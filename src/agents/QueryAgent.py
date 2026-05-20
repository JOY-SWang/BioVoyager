from .Agent import *
from .utils.query_utils import *

import json
import pandas as pd
import time

__init__ = """"""

class QueryAgent(Agent):
  def __init__(self, model, **kwargs):
    super().__init__("QueryAgent", model, **kwargs)
    print("Loading knowledge base...")
    self.ppi_data = pd.read_csv("/Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/knowledge_base/ppi_significant.csv")
    with open("/Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/knowledge_base/protein_functions.json", "r") as f:
      self.protein_functions = json.load(f)
    print("Knowledge base loaded.")
    
  def get_agent_info(self):
    info = """
    - Objective: Query relevant data from the knowledge base, help with planing agent and reasoning agent.
    - Tool: querier for offline and online base
        - offline knowledge base
            - PPI
            - Protein functions (Uniprot)
        - online knowledge base
            - PubMed keyword search
            - PubMed fact-checking
            - Semantic Scholar keyword search
            - Semantic Scholar snippet search (requires S2_API_KEY)
    - Task:
      - Query relevant data from the knowledge base
      - Query relevant data from the online knowledge base
      - Query relevant data from the offline knowledge base
    """
    for line in info.split("\n"):
      print("|", line)
    return info
  
  def act(self, query_type, configs):
    if query_type == "PPI":
      try:
        target_proteins = configs.get("target_proteins", [])
        extracted_ppi_data, protein_with_no_connections = query_ppi(target_proteins, self.ppi_data)
        return extracted_ppi_data, protein_with_no_connections
      except Exception as e:
        print(f"Error in QueryAgent: {e}")
        return None, None
    elif query_type == "Cluster":
      try:
        extracted_ppi_data = configs.get("extracted_ppi_data", None)
        if extracted_ppi_data is None:
          return None
        clusters = find_cluster_from_ppi(extracted_ppi_data, k=2)
        return clusters
      except Exception as e:
        print(f"Error in QueryAgent: {e}")
        return None
    elif query_type == "Functions":
      try:
        target_proteins = configs.get("target_proteins", [])
        functions = query_protein_functions(target_proteins, self.protein_functions)
        return functions
      except Exception as e:
        print(f"Error in QueryAgent: {e}")
        return None
    elif query_type == "PubMed":
      try:
        keywords = configs.get("keywords", "")
        max_results = configs.get("max_results", 10)
        publications = query_pubmed(keywords, max_results)
        return publications
      except Exception as e:
        print(f"Error in QueryAgent: {e}")
        time.sleep(10)
        try:
          keywords = configs.get("keywords", "")
          max_results = configs.get("max_results", 10)
          publications = query_pubmed(keywords, max_results)
          return publications
        except Exception as e:
          print(f"Error in QueryAgent: {e}")
          return None
    elif query_type == "PubMed_by_ID":
      try:
        pmid = str(configs.get("pmid", "")).strip()
        if not pmid:
          raise ValueError("PMID is required for PubMed query.")
        publication = query_pubmed_by_id(pmid)
        print(f"Found publication for PMID: {pmid}")
        time.sleep(1)
        return publication
      except Exception as e:
        print(f"Error in QueryAgent: {e}")
        return None
    elif query_type == "SemanticScholar":
      try:
        keywords = configs.get("keywords", "")
        max_results = configs.get("max_results", 20)
        publications = query_semantic_scholar(keywords, max_results)
        return publications
      except Exception as e:
        print(f"Error in QueryAgent SemanticScholar: {e}")
        return []

    elif query_type == "SemanticScholar_Snippets":
      try:
        query = configs.get("query", "")
        max_results = configs.get("max_results", 10)
        snippets = query_semantic_scholar_snippets(query, max_results)
        return snippets
      except Exception as e:
        print(f"Error in QueryAgent SemanticScholar_Snippets: {e}")
        return []

    elif query_type == "Open_Target_Description_by_Protein":
      try:
        protein = configs.get("protein", "")
        ensembl_id = search_target_protein(protein)
        if not ensembl_id:
          raise ValueError(f"No Ensembl ID found for protein: {protein}")
        return query_target_description(ensembl_id)
      except Exception as e:
        print(f"Error in QueryAgent TargetDescription: {e}")
        return None

    elif query_type == "Open_Target_KnownDrugs_by_Protein":
      try:
        protein = configs.get("protein", "")
        ensembl_id = search_target_protein(protein)
        if not ensembl_id:
          raise ValueError(f"No Ensembl ID found for protein: {protein}")
        return query_target_known_drugs(ensembl_id)
      except Exception as e:
        print(f"Error in QueryAgent TargetKnownDrugs: {e}")
        return None

    elif query_type == "Open_Target_Bibliography_by_Protein":
      try:
        protein = configs.get("protein", "")
        ensembl_id = search_target_protein(protein)
        if not ensembl_id:
          raise ValueError(f"No Ensembl ID found for protein: {protein}")
        return query_target_bibliography(ensembl_id)
      except Exception as e:
        print(f"Error in QueryAgent TargetBibliography: {e}")
        return None

    elif query_type == "Open_Target_AssociatedDiseases_by_Protein":
      try:
        protein = configs.get("protein", "")
        ensembl_id = search_target_protein(protein)
        if not ensembl_id:
          raise ValueError(f"No Ensembl ID found for protein: {protein}")
        return query_target_associated_diseases(ensembl_id)
      except Exception as e:
        print(f"Error in QueryAgent TargetAssociatedDiseases: {e}")
        return None
    else:
       return None