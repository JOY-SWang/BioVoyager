from .Agent import *
from .utils.reasoning_utils import *
from .prompts.reasoning_prompt_templates import *

import os
import json
import uuid

__init__ = """"""

class ReasoningAgent(Agent):
  def __init__(self, model, **kwargs):
    super().__init__("ReasoningAgent", model, **kwargs)
    
  def get_agent_info(self):
    info = """
    - Objective: Analyze the queried results, and write each part of document.
    - Task:
        - Reason and summarize for each enriched biological pathway
            - Overview: How many overlapping proteins with this pathway? Mention there is a figure for the PPI network.
            - Key proteins: Highlight the key proteins with functions that relevant with this disease.
              - If there is a cluster of proteins function together, introduce the cluster together.
            - Summary: Summarize the pathway with a few sentences.
    """
    for line in info.split("\n"):
      print("|", line)
    return info
  
  def generate_ppi_info(self, proteins_list, query_agent, img_dir="results/imgs"):
    extracted_ppi_data, single_protein = query_agent.act("PPI", {"target_proteins": proteins_list})
    if extracted_ppi_data is None:
        return "No PPI data available for the given protein(s).", None, None, None
    filename = f"{img_dir}/{uuid.uuid4()}.png"
    protein_list = extracted_ppi_data["protein1"].tolist() + extracted_ppi_data["protein2"].tolist() + single_protein
    protein_list = list(set(protein_list))
    image_path, web_url = generate_string_network_image_and_link_to_webpage(protein_list, filename)
    filename = filename.replace(img_dir, "imgs")
    if not web_url:
        web_url = "No link to the STRING webpage."
    return len(proteins_list), extracted_ppi_data, filename, web_url
  
########################################################
########### Pathway-Disease Analysis ###################
########################################################

  def generate_pathway_section_overview(self, pathway_infos, disease_name):
    formatted_pathways = format_pathways(pathway_infos)
    return self.t2t_generate(pathway_overview_prompt_template.format(formatted_pathways=formatted_pathways, disease_name=disease_name), pathway_overview_sys_tempalte)
  
  def generate_pathway_overview_tbl(self, pathway_infos):
    if pathway_infos is None:
      return None
    return pathway_overview_tbl(pathway_infos)
  
  def generate_pathway_analysis(self, disease_name, pathway_info, publication_info):
    prompt = pathway_reasoning_prompt_template.format(disease_name=disease_name, pathway_info=pathway_info, publication_info=publication_info)
    raw_response = self.t2t_generate(prompt, pathway_reasoning_sys_tempalte)
    if "```json" in raw_response:
      extracted_pathway = json.loads(raw_response.split("```json")[1].split("```")[0])
      return extracted_pathway
    else:
      return raw_response
  
########################################################
########### Function Enrichment Analysis ###############
########################################################

  def generate_cluster_function_analysis(self, extracted_ppi_data, disease_name, query_agent):
    clusters = query_agent.act("Cluster", {"extracted_ppi_data": extracted_ppi_data})
    cluster_functions = {}
    if clusters is None:
      return None, None
    if len(clusters) != 0:
      for cluster in clusters:
        cluster_name = "-".join(cluster)
        functions = query_agent.act("Functions", {"target_proteins": cluster})
        if functions is None:
          continue
        prompt = cluster_function_reasoning_prompt_template.format(formatted_proteins_functions=format_proteins_functions(functions), disease_name=disease_name)
        raw_response = self.t2t_generate(prompt, cluster_function_reasoning_sys_tempalte)
        if "```json" in raw_response:
          extracted_cluster_function = json.loads(raw_response.split("```json")[1].split("```")[0])
          cluster_functions[cluster_name] = extracted_cluster_function
        else:
          cluster_functions[cluster_name] = raw_response
    return clusters, cluster_functions
  
  def generate_protein_function_analysis(self, proteins_list, disease_name, query_agent):
    functions = query_agent.act("Functions", {"target_proteins": proteins_list})
    if functions is None:
      return None
    prompt = protein_function_reasoning_prompt_template.format(formatted_proteins_functions=format_proteins_functions(functions), disease_name=disease_name)
    raw_response = self.t2t_generate(prompt, protein_function_reasoning_sys_tempalte)
    if "```json" in raw_response:
      extracted_protein_function = json.loads(raw_response.split("```json")[1].split("```")[0])
      return extracted_protein_function
    else:
      return raw_response
    
  def summarize_function_enrichment(self, protein_count, ppi_filename, ppi_web_url, protein_functions, cluster_functions):
    response = {
      "protein_count": protein_count,
      "ppi_filename": ppi_filename,
      "ppi_web_url": ppi_web_url,
      "cluster_function": {
        "chunks": [],
        "citations": []
      },
      "protein_function": {
        "chunks": [],
        "citations": []
      }
    }
    if cluster_functions:
      for cluster_name, cluster_function in cluster_functions.items():
        response["cluster_function"]["chunks"].append(cluster_function["explanation"])
        response["cluster_function"]["citations"].append(cluster_function["citations"])
    if protein_functions and type(protein_functions) == dict:
      for protein_name, protein_function in protein_functions.items():
        response["protein_function"]["chunks"].append(protein_function["explanation"])
        response["protein_function"]["citations"].append(protein_function["citations"])
    return response
    
  def act(self, reasoning_type, configs):
    if reasoning_type == "PPI_Analysis":
      proteins_list = configs.get("proteins_list", [])
      disease_name = configs.get("disease_name", "")
      query_agent = configs.get("query_agent", None)
      img_dir = configs.get("img_dir", "results/imgs")
      if query_agent is None:
        return None
      protein_count, extracted_ppi_data, filename, web_url = self.generate_ppi_info(proteins_list, query_agent, img_dir)
      if extracted_ppi_data is None:
        return None, None, None, None
      return protein_count, extracted_ppi_data, filename, web_url
    elif reasoning_type == "Protein_Function_Analysis":
      proteins_list = configs.get("proteins_list", [])
      disease_name = configs.get("disease_name", "")
      query_agent = configs.get("query_agent", None)
      if query_agent is None:
        return None
      protein_functions = self.generate_protein_function_analysis(proteins_list, disease_name, query_agent)
      return protein_functions
    elif reasoning_type == "Cluster_Function_Analysis":
      extracted_ppi_data = configs.get("extracted_ppi_data", None)
      disease_name = configs.get("disease_name", "")
      query_agent = configs.get("query_agent", None)
      if query_agent is None:
        return None
      clusters, cluster_functions = self.generate_cluster_function_analysis(extracted_ppi_data, disease_name, query_agent)
      return clusters, cluster_functions
    elif reasoning_type == "Function_Enrichment_Analysis":
      protein_count = configs.get("protein_count", 0)
      ppi_filename = configs.get("ppi_filename", None)
      ppi_web_url = configs.get("ppi_web_url", None)
      protein_functions = configs.get("protein_functions", None)
      cluster_functions = configs.get("cluster_functions", None)
      return self.summarize_function_enrichment(protein_count, ppi_filename, ppi_web_url, protein_functions, cluster_functions)
    elif reasoning_type == "Pathway_Section_Overview":
      pathway_infos = configs.get("pathway_infos", None)
      disease_name = configs.get("disease_name", None)
      return self.generate_pathway_section_overview(pathway_infos, disease_name)
    elif reasoning_type == "Pathway_Overview_Tbl":
      pathway_infos = configs.get("pathway_infos", None)
      return self.generate_pathway_overview_tbl(pathway_infos)
    elif reasoning_type == "Pathway_Analysis":
      disease_name = configs.get("disease_name", None)
      pathway_info = configs.get("pathway_info", None)
      publication_info = configs.get("publication_info", None)
      return self.generate_pathway_analysis(disease_name, pathway_info, publication_info)
