from abc import ABC, abstractmethod
from .utils import *

import warnings
warnings.filterwarnings("ignore")

class Agent(ABC):
  def __init__(self, name, model_name, **kwargs):
    self.supported_base_models = ["gpt-4o", "llama3_2", "o4-mini", "gpt-4.1"]
    self.agent_name = name
    self.model_name = model_name
    self.config = kwargs
    self.model = self._load_model(model_name)
    print(f"{self.agent_name} with {model_name} loaded.")
    
  def _load_model(self, model_name):
    import os
    os.environ["CUDA_VISIBLE_DEVICES"] = self.config.get("cuda_device", "0")
    
    # OpenAI family
    if "gpt" in model_name or "o4" in model_name or "o3" in model_name:
      from openai import OpenAI
      import dotenv
      import httpx

      dotenv.load_dotenv()
      OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
      # Defaults are conservative for slow TLS / HTTP proxies (see httpx.ConnectTimeout).
      connect_s = float(os.getenv("OPENAI_CONNECT_TIMEOUT", "120"))
      read_s = float(os.getenv("OPENAI_READ_TIMEOUT", "600"))
      max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "5"))
      timeout = httpx.Timeout(read_s, connect=connect_s, write=read_s, pool=connect_s)
      client = OpenAI(
          api_key=OPENAI_API_KEY,
          timeout=timeout,
          max_retries=max_retries,
      )
      return client

    # vLLM for opensource models
    elif model_name in self.supported_base_models:
      from vllm import LLM
      llm = LLM(
        model=model_name,
        tokenizer=model_name,
        device="cuda",
        gpu_memory_utilization=0.95,
        tensor_parallel_size=self.config.get("tensor_parallel_size", 1),
      )
      return llm
    
    else:
      raise ValueError(f"Model {model_name} not supported. Supported models: {self.supported_base_models}")

  @staticmethod
  def _chat_max_output_kw(model_name: str):
    """gpt-5+ chat completions require max_completion_tokens; older models use max_tokens.
    Caps are per-model — exceeding them returns HTTP 400 'max_tokens is too large'."""
    if "gpt-5" in model_name:
      # GPT-5 Chat family max output is 16,384; larger values can trigger 400s (sometimes reported as JSON parse errors).
      return {"max_completion_tokens": 16384}
    if "gpt-4o" in model_name:
      # gpt-4o and gpt-4o-mini both cap at 16,384 output tokens.
      return {"max_tokens": 16384}
    cap = 8000 if "gpt-4.1" in model_name else 30000
    return {"max_tokens": cap}

  @staticmethod
  def _safe_chat_text(text) -> str:
    """Ensure message strings are JSON-safe (no NUL; valid UTF-8)."""
    if text is None:
      return ""
    s = text if isinstance(text, str) else str(text)
    return s.replace("\x00", "").encode("utf-8", errors="replace").decode("utf-8")

  def t2t_generate(self, user_prompt, system_prompt="You are a helpful assistant."):
    
    model_name = self.model_name
    
    if "gpt" in model_name:
      model = self.model
      response = model.chat.completions.create(
          model=model_name,
          messages=[
              {"role": "system", "content": self._safe_chat_text(system_prompt)},
              {"role": "user", "content": self._safe_chat_text(user_prompt)},
          ],
          temperature=0.7,
          **self._chat_max_output_kw(model_name),
      )
      return response.choices[0].message.content.strip()
    
    if "o4" in model_name:
      model = self.model
      response = model.responses.create(
          model=model_name,
          reasoning={"effort": "medium", "summary": "auto"},
          input=[
              {"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt}
          ],
      )
      return response.output_text
    
    elif model_name in self.supported_base_models:
      model, processor = self.model
      messages = [
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": [
              {"type": "text", "text": user_prompt}
          ]}
      ]
      input_text = processor.apply_chat_template(messages, add_generation_prompt=True)
      inputs = processor(
          None,
          input_text,
          add_special_tokens=False,
          return_tensors="pt"
          ).to(model.device)

      output = model.generate(**inputs, max_new_tokens=8000)
      response = processor.decode(output[:, inputs["input_ids"].shape[-1]:][0], skip_special_tokens=True)
      return response.strip()
    else:
      raise ValueError(f"Model {model_name} not supported. Supported models: {self.supported_base_models}")
      
  def v2t_generate(self, user_prompt, image_path, system_prompt="You are a helpful assistant."):
      import base64
      
      with open(image_path, "rb") as image_file:
        image_url = base64.b64encode(image_file.read()).decode('utf-8')
      model_name = self.model_name
      
      if "gpt" in model_name:
        model = self.model
        response = model.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": self._safe_chat_text(system_prompt)},
                {"role": "user", "content": [
                      {"type": "text",
                       "text": self._safe_chat_text(user_prompt)},
                      {
                          "type": "image_url",
                          "image_url": {
                              "url": f"data:image/jpeg;base64,{image_url}", },
                      },
                  ]},
            ],
            temperature=0.7,
            **self._chat_max_output_kw(model_name),
        )
        return response.choices[0].message.content.strip()
      elif model_name in self.supported_base_models:
        model, processor = self.model
        messages = [
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": [
              {"type": "image"},
              {"type": "text", "text": user_prompt}
          ]}
       ]
      input_img = Image.open(image_path)
      input_text = processor.apply_chat_template(messages, add_generation_prompt=True)
      inputs = processor(
          input_img,
          input_text,
          add_special_tokens=False,
          return_tensors="pt"
      ).to(model.device)
      output = model.generate(**inputs, max_new_tokens=1000)
      response = processor.decode(output[:, inputs["input_ids"].shape[-1]:][0], skip_special_tokens=True)
      return response.strip()
  
  @abstractmethod
  def act(self, *args, **kwargs):
    pass