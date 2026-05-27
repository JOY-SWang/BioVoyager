import markdown
import re
from agents.utils.general_utils import get_pubmed_link, format_citations_inline
import traceback

_NON_IMG_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico')


def _fix_url_images_to_links(html: str) -> str:
    """Convert <img> tags with broken or non-image srcs into links or remove them."""
    def replace(match):
        tag = match.group(0)
        src_m = re.search(r'src=["\']([^"\']+)["\']', tag)
        alt_m = re.search(r'alt=["\']([^"\']*)["\']', tag)
        if src_m:
            src = src_m.group(1)
            alt = alt_m.group(1) if alt_m else src
            # Drop broken "None" placeholders entirely
            if src.lower() == 'none':
                return ''
            # Convert web URLs in image syntax to hyperlinks
            if src.startswith('http') and not src.lower().endswith(_NON_IMG_EXTENSIONS):
                return f'<a href="{src}">{alt}</a>'
        return tag
    return re.sub(r'<img[^>]+>', replace, html)


def markdown_to_html(final_report, img_dir, result_dir, disease_file_name, version):
    html = markdown.markdown(final_report, extensions=['tables'])
    css = '''
    @page { 
        size: letter;
        margin: 1in;
    }
    body {
        font-size: 12pt;
        font-family: Arial, sans-serif;
        line-height: 1.5;
    }
    table {
        font-size: 10pt;
        width: 95%;
        border-collapse: collapse;
        margin: 20px 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f5f5f5;
    }
    img {
        max-width: 400px;
        height: auto;
        display: block;
        margin: 12px 0;
    }
    '''
    css_file = f"{result_dir}/style.css"
    with open(css_file, 'w') as f:
        f.write(css)

    # Keep relative imgs/ paths so the HTML works from its own directory.
    # Non-image URLs wrapped in image syntax are converted to hyperlinks.
    html = _fix_url_images_to_links(html)
    html_full = f"""
        <html>
        <head>
        <style>
        {css}
        </style>
        </head>
        <body>
        {html}
        </body>
        </html>
        """
    html_path = f"{result_dir}/{disease_file_name}_v{version}.html"
    with open(html_path, "w") as f:
        f.write(html_full)

def run(input_protein_list, disease_name, N_control, N_case, level, result_dir, cache_dir, img_dir, planning_agent, reasoning_agent, query_agent, writting_agent):
  total_protein_count = len(input_protein_list)

  report_draft = ""

  ranked_significant_pubmed_df, top_pathways = planning_agent.act(input_protein_list, disease_name, query_agent=query_agent)
  
  top_pathways.to_csv(f"{cache_dir}/top_pathways.csv", index=False)
  ranked_significant_pubmed_df.to_csv(f"{cache_dir}/ranked_significant_pubmed_df.csv", index=False)

  #########################
  # Pathway Section Overview
  #########################

  print("-| Pathway Overview")
  pathway_overview = reasoning_agent.act("Pathway_Section_Overview", {"pathway_infos": top_pathways.to_dict(orient="records"), "disease_name": disease_name})
  report_draft += "## Overview of the Enriched Pathways\n\n"
  report_draft += pathway_overview
  with open(f"{cache_dir}/pathway_overview.md", "w") as f:
    f.write(report_draft)
  
  pathway_overview_tbl = reasoning_agent.act("Pathway_Overview_Tbl", {"pathway_infos": top_pathways})
  report_draft += "\n\nTable 1: Top Enriched Pathways from Each Source\n\n"
  report_draft += pathway_overview_tbl
  report_draft += "\n\n"
  with open(f"{cache_dir}/pathway_overview_tbl.md", "w") as f:
    f.write(report_draft)
  
  report_draft += "\n\n## Enriched Pathways Analysis\n\n"
  report_draft += "In the following sections, we provide a detailed discussion of the top enriched pathways."

  report_draft = writting_agent.act("RevisionCoherence", {"report_draft": report_draft})
  report_draft += "\n"
  
  #########################
  #  Pathway Analysis
  #########################

  import itertools
  for index, row in itertools.islice(top_pathways.iterrows(), 0, min(12, len(top_pathways))):
    print(f"-| Pathway Analysis: {row['name']}")
    
    content = f"\n\n### {row['name']} ({row['native']}) \n\n"
    
    pathway_info = row["name"] + ": " + row["description"]
    pathway_publications = row["validated_publications"]
    
    pathway_analysis = reasoning_agent.act("Pathway_Analysis", {"disease_name": disease_name, "pathway_info": pathway_info, "publication_info": pathway_publications})
    
    if pathway_analysis is None:
        print(f"Warning: Pathway_Analysis returned None for pathway {row['name']}, skipping")
        continue
        
    pathway_analysis_content = pathway_analysis.get("description", "") + "\n" + pathway_analysis.get("explanation", "")
    for citation in pathway_analysis.get("citations", []):
      try:
        pmid = citation.split(":")[1].strip()
        pmid_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
        pathway_analysis_content += f"[{citation}]({pmid_url}) "
      except Exception as e:
        print(f"Error processing citation: {citation}")
        continue
    pathway_analysis_content += "\n\n"
    
    content += pathway_analysis_content

    protein_list = row["intersections"]
    protein_list = [protein.strip() for protein in protein_list]
    print("   --| Protein Function Enrichment Analysis")
    print("     ---| PPI Analysis")
    protein_count, extracted_ppi_data, filename, web_url = reasoning_agent.act("PPI_Analysis", {"proteins_list": protein_list, "disease_name": disease_name, "query_agent": query_agent, "img_dir": img_dir})
    print("     ---| Cluster Function Analysis")
    cluster, cluster_functions = reasoning_agent.act("Cluster_Function_Analysis", {"extracted_ppi_data": extracted_ppi_data, "disease_name": disease_name, "query_agent": query_agent})
    print("     ---| Protein Function Analysis")
    if cluster is None or len(cluster) == 0:
        print("Warning: Cluster_Function_Analysis returned None, skipping")
        rest_proteins = protein_list
    else:
      cluster_functions = []
      cluster_expanded = [protein for cluster in cluster for protein in cluster]
      rest_proteins = [protein for protein in protein_list if protein not in cluster_expanded]
    protein_functions = reasoning_agent.act("Protein_Function_Analysis", {"proteins_list": rest_proteins, "disease_name": disease_name, "query_agent": query_agent})
    print("     ---| Summarize Function Enrichment Analysis")
    protein_function_enrichment = reasoning_agent.act("Function_Enrichment_Analysis", {"protein_count": protein_count, "ppi_filename": filename, "ppi_web_url": web_url, "protein_functions": protein_functions, "cluster_functions": cluster_functions})
    
    if protein_function_enrichment is None:
        print("Warning: Function_Enrichment_Analysis returned None, skipping this pathway")
        continue
        
    print("     ---| Function Enrichment Overview")
    function_enrichment_overview = writting_agent.act("Function_Enrichment_Overview", {"disease_name": disease_name, "pathway_name": pathway_analysis.get("description", ""), "protein_count": protein_function_enrichment.get("protein_count", 0), "ppi_filename": protein_function_enrichment.get("ppi_filename", ""), "ppi_web_url": protein_function_enrichment.get("ppi_web_url", "")})
    
    # Add safety check for function_enrichment_overview
    if function_enrichment_overview is None:
        print("Warning: Function_Enrichment_Overview returned None")
        function_enrichment_overview = ""

    print("   --| Protein Function Enrichment Writting")
    content += function_enrichment_overview

    print("     ---| Protein Function Writting")
    protein_function_analysis = ""
    protein_function = protein_function_enrichment.get("protein_function", {})
    if not protein_function:
        print("Warning: No protein_function data available")
        protein_function = {"chunks": [], "citations": []}
    protein_citations = protein_function.get("citations", [])
    if len(protein_function.get("chunks", [])) > 0:
      content += "\n\nDuring the function enrichment analysis, we identified serveral significant proteins. We will introduce them in-details in the following.\n"
      for index, chunk in enumerate(protein_function.get("chunks", [])):
        protein_function_analysis += chunk
        if protein_citations and index < len(protein_citations) and protein_citations[index] and len(protein_citations[index]) > 0:
          for citation in protein_citations[index]:
            try:
              pmid = citation.split(":")[1].strip()
              pmid_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
              protein_function_analysis += f"[{citation}]({pmid_url}) "
            except Exception as e:
              print(f"Error processing citation: {citation}")
              continue
        protein_function_analysis += "\n"
      content += protein_function_analysis
      content += "\n"

    print("     ---| Cluster Function Writting")
    cluster_function_analysis = ""
    cluster_function = protein_function_enrichment.get("cluster_function", {})
    if not cluster_function:
        print("Warning: No cluster_function data available")
        cluster_function = {"chunks": [], "citations": []}
    cluster_citations = cluster_function.get("citations", [])
    if len(cluster_function.get("chunks", [])) > 0:
      for index, chunk in enumerate(cluster_function.get("chunks", [])):
        cluster_function_analysis += chunk
        if cluster_citations and index < len(cluster_citations) and cluster_citations[index] and len(cluster_citations[index]) > 0:
          for citation in cluster_citations[index]:
            try:
              pmid = citation.split(":")[1].strip()
              pmid_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
              cluster_function_analysis += f"[{citation}]({pmid_url}) "
            except Exception as e:
              print(f"Error processing citation: {citation}")
              continue
        cluster_function_analysis += "\n"
      content += "There are also small set of proteins function together to form a cluster."
      content += cluster_function_analysis  
    
    revised_content = writting_agent.act("RevisionCoherence", {"report_draft": content})
    if revised_content is None:
        print("Warning: RevisionCoherence returned None")
        revised_content = content
    if not revised_content.startswith("\n"):
      revised_content = "\n\n" + revised_content
    report_draft += revised_content

    with open(f"{cache_dir}/report_draft_{index}.md", "w") as f:
      f.write(report_draft)

  total_pathways_count = len(ranked_significant_pubmed_df)
  introduction = writting_agent.act("Introduction", {"report_draft": report_draft, "disease_name": disease_name, "level": level, "N_control": N_control, "N_case": N_case, "total_pathways_count": total_pathways_count, "total_protein_count": total_protein_count})
  
  if introduction is None:
      print("Warning: Introduction returned None")
      introduction = ""

  draft_with_introduction = "## Introduction\n\n" + introduction + "\n\n" + report_draft
  with open(f"{cache_dir}/draft_with_introduction.md", "w") as f:
    f.write(draft_with_introduction)

  formatted_citation_draft, ordered_pmids = format_citations_inline(draft_with_introduction)
  references = []
  if len(ordered_pmids) > 0:
    for i, pmid in enumerate(ordered_pmids):
      try:
        pub = query_agent.act("PubMed_by_ID", {"pmid": pmid})
        if pub:
            authors = ', '.join(pub.get("Authors", []))
            title = pub.get("Title", "N/A")
            journal = pub.get("Journal", "N/A")
            pub_date = pub.get("Publication Date", "N/A")
            ref_line = f"[{i+1}]({get_pubmed_link(pmid)}) {authors}. {title}. *{journal}*. {pub_date}."
            references.append(ref_line)
        else:
          print(f"No publication found for PMID: {pmid}")
      except Exception as e:
        print(f"Error fetching reference for PMID {pmid}: {e}")
    
  formatted_citation_draft += "\n\n## References\n\n" + "\n\n".join(references)
  with open(f"{cache_dir}/formatted_citation_draft.md", "w") as f:
    f.write(formatted_citation_draft)
  markdown_to_html(formatted_citation_draft, img_dir, result_dir, disease_file_name, 1)


if __name__ == "__main__":
  import argparse
  import os

  import pandas as pd
  from agents.PlanningAgent import PlanningAgent
  from agents.ReasoningAgent import ReasoningAgent
  from agents.QueryAgent import QueryAgent
  from agents.WrittingAgent import WrittingAgent

  # Repo-relative defaults; override with flags or env vars.
  _SRC_DIR = os.path.dirname(os.path.abspath(__file__))
  _REPO_ROOT = os.path.dirname(_SRC_DIR)
  DEFAULT_TEST_DATA_DIR = os.environ.get(
      "BIOINSIGHT_TEST_DATA_DIR", os.path.join(_REPO_ROOT, "test_data")
  )
  DEFAULT_RESULTS_DIR = os.environ.get(
      "BIOINSIGHT_RESULTS_DIR", os.path.join(_SRC_DIR, "results_0411")
  )
  DEFAULT_META_PATH = os.path.join(DEFAULT_TEST_DATA_DIR, "DiseaseDefinition&Summary_incident.csv")
  DEFAULT_MODEL = os.environ.get("BIOINSIGHT_MODEL", "gpt-5.4")

  parser = argparse.ArgumentParser(description="Generate v1 narrative HTML reports")
  parser.add_argument("--csv", type=str, help="Run a single CSV instead of batch", default=None)
  parser.add_argument("--test-data-dir", type=str, default=DEFAULT_TEST_DATA_DIR)
  parser.add_argument("--results-dir", type=str, default=DEFAULT_RESULTS_DIR)
  parser.add_argument("--meta-path", type=str, default=DEFAULT_META_PATH)
  parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
  parser.add_argument("--range", type=str, default="0:11", help="Slice of CSVs to process in batch mode (e.g. 0:11)")
  args = parser.parse_args()

  planning_agent = PlanningAgent(model=args.model)
  reasoning_agent = ReasoningAgent(model=args.model)
  query_agent = QueryAgent(model=args.model)
  writting_agent = WrittingAgent(model=args.model)

  level = "0.000000001"
  meta_data = pd.read_csv(args.meta_path)

  test_data_dir = args.test_data_dir
  result_dir_path = args.results_dir

  if args.csv:
      subset = [os.path.basename(args.csv)]
  else:
      rs, re_ = args.range.split(":")
      files = [f for f in os.listdir(test_data_dir) if f.endswith(".csv") and f != "DiseaseDefinition&Summary_incident.csv"]
      subset = files[int(rs):int(re_)]

  for idx, test_file in enumerate(subset):
    try:
      print("================================================")
      print(f"Processing [{idx+1}/{len(subset)}] {test_file}")
      print("================================================")
      df = pd.read_csv(os.path.join(test_data_dir, test_file))
      disease_file_name = os.path.splitext(test_file)[0]
      
      temp_meta_data = meta_data[meta_data["Disease"] == disease_file_name.replace("_", " ")]
      N_control = temp_meta_data["N_control"].values[0]
      N_case = temp_meta_data["N_case_After baseline"].values[0]
      
      disease_name = planning_agent.sanitize_disease_name(disease_file_name)
      result_dir = os.path.join(result_dir_path, disease_name)
      cache_dir = os.path.join(result_dir, 'cache')
      img_dir = os.path.join(result_dir, 'imgs')
      os.makedirs(result_dir, exist_ok=True)
      os.makedirs(cache_dir, exist_ok=True)
      os.makedirs(img_dir, exist_ok=True)
      
      input_protein_list = df["Protein"].tolist()
      run(input_protein_list, disease_name, N_control, N_case, level, result_dir, cache_dir, img_dir, planning_agent, reasoning_agent, query_agent, writting_agent)      
    except Exception as e:
      print(f"### Error processing {test_file}: {str(e)}")
      print(traceback.format_exc())
      continue