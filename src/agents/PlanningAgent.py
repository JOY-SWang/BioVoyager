from .Agent import *
from .utils.planning_utils import *
from .prompts.planning_prompt_templates import *

__init__ = """"""

class PlanningAgent(Agent):
  def __init__(self, model, **kwargs):
    super().__init__("PlanningAgent", model, **kwargs)
    
  def get_agent_info(self):
    info = """
    - Objective: Profile the protein by pathway, and select the top 10 pathway for following steps.
    - Tool: gProfiler, PubMed, Semantic Scholar
    - Task:
      - profile protein list with given tool (gProfiler), and group by pathway
      - collaborate with query agent to rank pathways (PubMed + Semantic Scholar combined search)
      - rank by journal-weighted relevance, semantic similarity, and citation impact
      - select the top pathways and associate proteins, each group run the query and reasoning.
    """
    for line in info.split("\n"):
      print("|", line)
    return info
  
  def sanitize_disease_name(self, disease_name):
    return self.t2t_generate(sanitize_disease_name_prompt_template.format(disease_name=disease_name), "You are a helpful assistant.")
  
  def enrich_disease_description(self, disease_trait):
    enriched_description = self.t2t_generate(prompt_template.format(disease_trait=disease_trait), "You are a helpful assistant.")
    return enriched_description
  
  def rank_pathways(self, pathway_descriptions, disease_trait):
    enriched_description = self.enrich_disease_description(disease_trait)
    tfidf_scores = rank_pathways_tfidf(pathway_descriptions, enriched_description)
    biobert_scores = rank_pathways_biobert(pathway_descriptions, enriched_description)
    combined_scores = {}
    for desc in pathway_descriptions:
        combined = (tfidf_scores.get(desc, 0) + biobert_scores.get(desc, 0)) / 2
        combined_scores[desc] = combined
    return enriched_description, combined_scores.items()
  
  def select_top_pathways(self, df, top_count=3):
    df = df.groupby("source").head(top_count)
    df.sort_values(by="score", ascending=False, inplace=True)
    return df

  
  def act(self, protein_list, disease_trait, query_agent=None):
    print("-| Planning")
    proteins = sanitize_protein_list(protein_list)
    print("  --| Run g:Profiler")
    result, significant_df = run_gprofiler_query(proteins)
    print("  --| Filter Fundamental Pathways")
    significant_df = filter_fundamental_pathways(significant_df)
    print("  --| Filter Duplicate Pathways")
    significant_df = filter_duplicate_pathways(significant_df)
    print("  --| Rank Pathways by Literature Relevance (PubMed + Semantic Scholar)")
    ranked_significant_pubmed_df = rank_pathways_by_pubmed_relevance(significant_df, disease_trait, query_agent)

    top_count = 2
    top_pathways = self.select_top_pathways(ranked_significant_pubmed_df, top_count)
    print(f"  --| Select Top {top_count} Pathways")
    print(f"      ---| Total: {len(top_pathways)} pathways selected.")
    for source in top_pathways["source"].unique():
      print(f"      ---| {source}: {len(top_pathways[top_pathways['source'] == source])} pathways")

    return ranked_significant_pubmed_df, top_pathways