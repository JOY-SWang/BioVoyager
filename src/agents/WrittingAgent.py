from .Agent import *
from .utils import *
from .prompts.writting_prompt_templates import *

import os
import re

__init__ = """"""

_NON_IMG_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico')


def _normalize_collapsed_markdown_tables(text):
  """Repair tables where row boundaries were collapsed into '| |' without newlines."""
  if not text:
    return text
  # Caption glued to table: "Table 1: Title | Term ID |" -> blank line before pipes
  text = re.sub(
      r"(Table\s+\d+:[^\n|]*?)(\s+)(\|)",
      r"\1\n\n\3",
      text,
  )
  # Repeatedly split merged rows: "... | GO:BP | | GO:0005882 | ..." -> newline between rows
  prev = None
  while prev != text:
    prev = text
    text = re.sub(r"\|\s+\|(?=\s*[-A-Za-z0-9:.])", "|\n|", text)
  # Ensure blank line before a table block that starts mid-paragraph (line begins with |)
  lines = text.split("\n")
  out = []
  for i, line in enumerate(lines):
    if (
        i > 0
        and line.strip().startswith("|")
        and out
        and out[-1].strip()
        and not out[-1].strip().startswith("|")
        and not out[-1].strip().startswith("#")
        and lines[i - 1].strip()
        and not lines[i - 1].strip().startswith("|")
    ):
      out.append("")
    out.append(line)
  return "\n".join(out)


def _normalize_ppi_markdown(text, ppi_filename, ppi_web_url):
  """Ensure PPI PNG uses imgs/-relative path and non-image URLs are links, not image syntax."""
  if not text:
    return text
  base = os.path.basename((ppi_filename or "").strip()) if ppi_filename else ""
  rel_img = f"imgs/{base}" if base else ""

  # Remove broken None placeholders generated when PPI analysis returns nothing
  text = re.sub(r'!\[[^\]]*\]\(None\)', '', text, flags=re.IGNORECASE)
  text = re.sub(r'\[[^\]]*\]\(None\)', '', text, flags=re.IGNORECASE)

  # Convert ANY image syntax pointing at a non-image URL into a plain hyperlink.
  # e.g. ![Link to STRING](https://string-db.org/...) -> [Link to STRING](https://string-db.org/...)
  def _url_img_to_link(m):
    alt, url = m.group(1), m.group(2)
    if url.lower().endswith(_NON_IMG_EXTENSIONS):
      return m.group(0)  # keep real image references unchanged
    return f'[{alt}]({url})'

  text = re.sub(
      r'!\[([^\]]*)\]\((https?://[^)]+)\)',
      _url_img_to_link,
      text,
  )

  if rel_img:
    # Normalize any image markdown that references this file to the canonical relative path
    esc_base = re.escape(base)
    text = re.sub(
        rf'!\[([^\]]*)\]\([^)]*{esc_base}[^)]*\)',
        rf'![\1]({rel_img})',
        text,
    )
    # Absolute or odd prefixes still pointing at the same basename
    text = re.sub(
        rf'!\[([^\]]*)\]\([^)]*/{esc_base}\)',
        rf'![\1]({rel_img})',
        text,
    )

  # Drop placeholder web URL text from ReasoningAgent when STRING failed
  if ppi_web_url and str(ppi_web_url).strip().lower().startswith("no link"):
    text = re.sub(r'\[[^\]]*\]\(\s*No link to the STRING webpage\.?\s*\)', '', text)

  return text


def _normalize_visualization_markdown(text, ppi_filename=None, ppi_web_url=None):
  text = _normalize_collapsed_markdown_tables(text)
  if ppi_filename or ppi_web_url:
    text = _normalize_ppi_markdown(text, ppi_filename, ppi_web_url)
  return text


class WrittingAgent(Agent):
  def __init__(self, model, **kwargs):
    super().__init__("WrittingAgent", model, **kwargs)
    
  def get_agent_info(self):
    info = """
    - Objectives:
      - Generate the introduction of the report.
      - Revise the overview of the report draft.
      - Generate the conclusion of the report.
      - Format the report in Markdown.
    - Tasks:
      - introduction: the introduction of the report
      - revised_overview: the revised overview of the report draft
      - conclusion: the conclusion of the report
      - formatted_report: the formatted report in Markdown
    """
    for line in info.split("\n"):
      print("|", line)
    return info
  
  ################################
  # Function Enrichment Analysis #
  ################################
  
  def generate_function_enrichment_overview(self, disease_name, pathway_name, protein_count, ppi_filename, ppi_web_url):
    prompt = function_enrichment_overview_prompt_template.format(disease_name=disease_name, pathway_name=pathway_name, protein_count=protein_count, ppi_filename=ppi_filename, ppi_web_url=ppi_web_url)
    raw_response = self.t2t_generate(prompt, writing_system_prompt)
    return _normalize_visualization_markdown(raw_response, ppi_filename, ppi_web_url)
  
  def revise_function_enrichment_analysis(self, paragraph):
    prompt = function_enrichment_analysis_revision_prompt_template.format(paragraph=paragraph)
    raw_response = self.t2t_generate(prompt, writing_system_prompt)
    return _normalize_visualization_markdown(raw_response)
  
  def generate_introduction(self, report_draft, disease_name, level, N_control, N_case, total_pathways_count, total_protein_count):
    prompt = generate_introduction_prompt_template.format(report_draft=report_draft, disease_name=disease_name, level=level, N_control=N_control, N_case=N_case, total_pathways_count=total_pathways_count, total_protein_count=total_protein_count)
    raw_response = self.t2t_generate(prompt, writing_system_prompt)
    return raw_response

  def revise_coherence(self, report_draft):
    prompt = coherence_revision_prompt_template.format(report_draft=report_draft)
    raw_response = self.t2t_generate(prompt, writing_system_prompt)
    return _normalize_visualization_markdown(raw_response)
  
  def act(self, writting_type, configs):
    if writting_type == "Function_Enrichment_Overview":
      disease_name = configs.get("disease_name", None)
      pathway_name = configs.get("pathway_name", None)
      protein_count = configs.get("protein_count", None)
      ppi_filename = configs.get("ppi_filename", None)
      ppi_web_url = configs.get("ppi_web_url", None)
      return self.generate_function_enrichment_overview(disease_name, pathway_name, protein_count, ppi_filename, ppi_web_url)
    elif writting_type == "Function_Enrichment_Analysis":
      paragraph = configs.get("paragraph", None)
      return self.revise_function_enrichment_analysis(paragraph)
    elif writting_type == "Introduction":
      report_draft = configs.get("report_draft", None)
      disease_name = configs.get("disease_name", None)
      level = configs.get("level", None)
      N_control = configs.get("N_control", None)
      N_case = configs.get("N_case", None)
      total_pathways_count = configs.get("total_pathways_count", None)
      total_protein_count = configs.get("total_protein_count", None)
      return self.generate_introduction(report_draft, disease_name, level, N_control, N_case, total_pathways_count, total_protein_count)
    elif writting_type == "RevisionCoherence":
      report_draft = configs.get("report_draft", None)
      return self.revise_coherence(report_draft)