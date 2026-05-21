import os
import re
import json
import copy
import requests
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from tqdm import tqdm

# BioBERT model. Default to the HuggingFace Hub identifier so the model is
# fetched + cached automatically (~440 MB on first run). Override with
# BIOVOYAGER_BIOBERT to point at a local checkpoint dir.
_BIOBERT_MODEL = os.environ.get("BIOVOYAGER_BIOBERT", "dmis-lab/biobert-base-cased-v1.1")

try:
    biobert_tokenizer = AutoTokenizer.from_pretrained(_BIOBERT_MODEL)
    biobert_model = AutoModel.from_pretrained(_BIOBERT_MODEL)
    _BIOBERT_AVAILABLE = True
except Exception as _e:  # pragma: no cover — falls back to keyword-only ranking
    print(f"[planning_utils] WARNING: BioBERT unavailable ({_e!r}); "
          f"semantic pathway ranking will be skipped.")
    biobert_tokenizer = None
    biobert_model = None
    _BIOBERT_AVAILABLE = False

def sanitize_protein_list(protein_list):
  if isinstance(protein_list, list):
      return protein_list
  elif isinstance(protein_list, str):
      temp = protein_list.split(",")
      return [x.strip() for x in temp]
  else:
      return []

def gprofiler_query(query, organism="hsapiens", sources=['REAC', 'KEGG', 'HP', 'GO:MF', 'GO:BP'], user_threshold=0.0001):
  url = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
  payload = {
      "organism": organism,
      "query": query,
      "sources": sources,
      "user_threshold": user_threshold,
      "no_iea": True,  
      "ordered": False, 
      "highlight": True,
      "significance_threshold_method": "fdr" 
  }
  headers = {"Content-Type": "application/json"}
  response = requests.post(url, data=json.dumps(payload), headers=headers)
  if response.status_code == 200:
      result = response.json()
      with open("result.json", "w") as f:
          json.dump(result, f)
      if result["result"] == []:
          return None, None
      result_df = pd.DataFrame(result["result"])
      
      genes_mapping = result["meta"]["genes_metadata"]["query"]["query_1"]["mapping"]
      genes_mapping = {v[0]: k for k, v in genes_mapping.items()}
      ordered_protein = result["meta"]["genes_metadata"]["query"]["query_1"]["ensgs"]
      ordered_protein = [genes_mapping.get(ensg, ensg) for ensg in ordered_protein]
      
      significant_df = result_df[result_df['significant'] == True]      
      intersections = significant_df["intersections"].values
      intersections_protiens = []
      for intersection in intersections:
          if intersection:
              temp = []
              for i, inter in enumerate(intersection):
                  if len(inter) > 0:
                        temp.append(ordered_protein[i])
              intersections_protiens.append(temp) 
      
      significant_df = significant_df.sort_values('p_value', ascending=True)
      significant_df = significant_df[["native","name", "description", "source", "effective_domain_size", "term_size", "p_value", "intersections", "intersection_size", "highlighted"]]
      significant_df["intersections"] = intersections_protiens
      return result, significant_df
  else:
      print("Error:", response.status_code, response.text)
      return None, None 
  
def run_gprofiler_query(query, organism="hsapiens", user_threshold=0.05, top=20):
    sources = ["REAC", "KEGG", "HP", "WP", "TF", "MIRNA", "CORUM", "HPA"]
    go_sources = ["GO:MF", "GO:BP", "GO:CC"]
    results = []
    result_df = pd.DataFrame()
    
    result, significant_df = gprofiler_query(query, organism, sources, user_threshold)
    results.append(result)
    result_df = pd.concat([result_df, significant_df])
        
    result, significant_df = gprofiler_query(query, organism, go_sources, user_threshold)
    significant_df = significant_df[significant_df["highlighted"] == True]
    results.append(result)
    result_df = pd.concat([result_df, significant_df])
    
    result_df = result_df.drop(columns=["highlighted"])
    result_df = result_df.sort_values("p_value", ascending=True)
    
    result_df = result_df.groupby("source").head(top)
        
    return results, result_df

def get_biobert_embedding(text):
  if not _BIOBERT_AVAILABLE:
      # Caller-side code is expected to wrap this and fall back to TF-IDF.
      raise RuntimeError("BioBERT unavailable; set BIOVOYAGER_BIOBERT or install transformers properly.")
  inputs = biobert_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
  with torch.no_grad():
      outputs = biobert_model(**inputs)
  cls_embedding = outputs.last_hidden_state[:, 0, :].numpy()
  return cls_embedding

def filter_duplicate_pathways(result_df):
    names = result_df["name"].tolist()
    safe_words = ["complex", "signaling", "process", "pathway", "interaction", "activity"]
    embeddings = []
    for name in names:
        for safe_word in safe_words:
            name.replace(safe_word, "")
        if ";" in name:
            name = name.split(";")[1].strip()
        embeddings.append(get_biobert_embedding(name))
    output_df = copy.deepcopy(result_df)
    to_drop = set()
    for i in range(len(embeddings)):
        if i in to_drop:
            continue
        for j in range(i + 1, len(embeddings)):
            if j in to_drop:
                continue
            sim = cosine_similarity(embeddings[i], embeddings[j])[0][0]
            if sim > 0.98:
                print(f"      ---| {result_df.iloc[i]['name']} | {result_df.iloc[j]['name']}")
                if result_df.iloc[i]["p_value"] > result_df.iloc[j]["p_value"]:
                    to_drop.add(i)
                else:
                    to_drop.add(j)
    output_df = output_df.drop(result_df.index[list(to_drop)])
    output_df = output_df.sort_values("p_value", ascending=True)
    return output_df

def filter_fundamental_pathways(result_df, term_size_thresholds = [10, 500]):
    output_df = copy.deepcopy(result_df)
    output_df = output_df[(output_df["term_size"] < term_size_thresholds[1]) & (output_df["term_size"] > term_size_thresholds[0])]
    filtered = result_df[(result_df["term_size"] < term_size_thresholds[0]) | (result_df["term_size"] > term_size_thresholds[1])]
    filtered_names = filtered["name"].tolist()
    for name in filtered_names:
        print(f"      ---| {name}")
    return output_df

# ============================================================
# Journal impact weighting (adapted from SearchMedPaper/search.py)
# ============================================================
_JOURNAL_WEIGHT_DEFAULT = 1.0
_JOURNAL_WEIGHT_RANGE = (0.5, 2.2)

def _normalize_journal(name):
    if not name:
        return None
    import re as _re
    s = name.lower().strip()
    s = _re.sub(r'\(.*?\)', '', s)
    s = _re.sub(r':.*$', '', s)
    s = _re.sub(r'[^a-z0-9\s&\-\.]', ' ', s)
    s = _re.sub(r'\bthe\b', ' ', s)
    s = _re.sub(r'\s+', ' ', s).strip()
    return s

_JOURNAL_WEIGHTS = {
    _normalize_journal('Nature'): 2.0,
    _normalize_journal('Science'): 2.0,
    _normalize_journal('Cell'): 2.0,
    _normalize_journal('The New England Journal of Medicine'): 2.0,
    _normalize_journal('Lancet (London, England)'): 2.0,
    _normalize_journal('JAMA'): 1.9,
    _normalize_journal('Nature Medicine'): 1.9,
    _normalize_journal('Nature Genetics'): 1.9,
    _normalize_journal('Nature Neuroscience'): 1.9,
    _normalize_journal('Nature Communications'): 1.6,
    _normalize_journal('Science Advances'): 1.5,
    _normalize_journal('Cell Reports'): 1.5,
    _normalize_journal('PNAS'): 1.7,
    _normalize_journal('Proceedings of the National Academy of Sciences of the United States of America'): 1.7,
    _normalize_journal('Neuron'): 1.8,
    _normalize_journal('Brain : a journal of neurology'): 1.6,
    _normalize_journal('Acta Neuropathologica'): 1.7,
    _normalize_journal('Molecular Psychiatry'): 1.7,
    _normalize_journal("Alzheimer's & Dementia"): 1.6,
    _normalize_journal('Human Molecular Genetics'): 1.6,
    _normalize_journal('The Journal of Neuroscience'): 1.6,
    _normalize_journal('The Journal of Clinical Investigation'): 1.8,
    _normalize_journal('eLife'): 1.4,
    _normalize_journal('Genome Medicine'): 1.5,
    _normalize_journal('EMBO Molecular Medicine'): 1.5,
    _normalize_journal('Scientific Reports'): 1.05,
    _normalize_journal('PloS one'): 0.95,
    _normalize_journal('Frontiers in Aging Neuroscience'): 1.1,
    _normalize_journal('Frontiers in Neuroscience'): 1.1,
    _normalize_journal('International Journal of Molecular Sciences'): 1.0,
}


def _journal_weight(journal_name):
    key = _normalize_journal(journal_name)
    if not key:
        return _JOURNAL_WEIGHT_DEFAULT
    if key in _JOURNAL_WEIGHTS:
        return _JOURNAL_WEIGHTS[key]
    if key == 'nature' or key == 'science' or key == 'cell':
        return 2.0
    if key.startswith('nature '):
        return 1.6
    if key.startswith('science '):
        return 1.4
    if key.startswith('cell '):
        return 1.4
    if 'lancet' in key:
        return 2.0
    if 'jama' in key:
        return 1.9
    if 'pnas' in key or 'national academy' in key:
        return 1.7
    if key.startswith('frontiers '):
        return 1.1
    if key == 'scientific reports':
        return 1.05
    if 'plos one' in key:
        return 0.95
    return _JOURNAL_WEIGHT_DEFAULT


# ============================================================
# Relevance scoring: keyword + semantic
# ============================================================

def _keyword_relevance(pub, disease_trait, pathway_name):
    """Keyword-overlap relevance score in [0, 1]."""
    title = (pub.get("Title") or "").lower()
    abstract = (pub.get("Abstract") or "").lower()
    disease_low = disease_trait.lower()
    pathway_low = pathway_name.lower()

    score = 0.0
    if disease_low in title:
        score += 3.0
    if pathway_low in title:
        score += 2.0
    if disease_low in abstract:
        score += 1.5
    if pathway_low in abstract:
        score += 1.5

    disease_tokens = disease_low.split()
    pathway_tokens = pathway_low.split()
    for tok in disease_tokens:
        if len(tok) > 3 and tok in abstract:
            score += 0.3
    for tok in pathway_tokens:
        if len(tok) > 3 and tok in abstract:
            score += 0.3

    max_score = 3.0 + 2.0 + 1.5 + 1.5 + 0.3 * max(len(disease_tokens), 1) + 0.3 * max(len(pathway_tokens), 1)
    return min(score / max_score, 1.0)


def _semantic_relevance(pub, disease_trait, pathway_name):
    """BioBERT cosine similarity between (disease+pathway) query and paper text."""
    query_text = f"{disease_trait} {pathway_name}"
    paper_text = f"{pub.get('Title', '')} {pub.get('Abstract', '')}"
    if not paper_text.strip():
        return 0.0
    try:
        q_emb = get_biobert_embedding(query_text)
        p_emb = get_biobert_embedding(paper_text[:512])
        sim = cosine_similarity(q_emb, p_emb)[0][0]
        return float(max(sim, 0.0))
    except Exception:
        return 0.0


def compute_publication_relevance(pub, disease_trait, pathway_name, use_semantic=True):
    """Combined relevance score for a single publication."""
    kw_score = _keyword_relevance(pub, disease_trait, pathway_name)
    j_weight = _journal_weight(pub.get("Journal"))
    citation_boost = 0.0
    cc = pub.get("CitationCount", 0)
    if cc and cc > 0:
        citation_boost = min(np.log1p(cc) / 10.0, 0.3)

    if use_semantic:
        sem_score = _semantic_relevance(pub, disease_trait, pathway_name)
        raw = 0.45 * kw_score + 0.35 * sem_score + 0.20 * citation_boost
    else:
        raw = 0.70 * kw_score + 0.30 * citation_boost

    return float(np.clip(raw * j_weight, 0.0, _JOURNAL_WEIGHT_RANGE[1]))


# ============================================================
# Merge & deduplicate publications from multiple sources
# ============================================================

def _merge_publications(pubmed_pubs, s2_pubs):
    """Merge PubMed and Semantic Scholar results, dedup by PMID/title."""
    merged = []
    seen_pmids = set()
    seen_titles = set()

    for pub in pubmed_pubs:
        pmid = pub.get("PMID", "N/A")
        title = (pub.get("Title") or "").lower().strip()
        if pmid != "N/A" and pmid in seen_pmids:
            continue
        if title and title in seen_titles:
            continue
        if pmid != "N/A":
            seen_pmids.add(pmid)
        if title:
            seen_titles.add(title)
        merged.append(pub)

    for pub in s2_pubs:
        pmid = pub.get("PMID", "N/A")
        title = (pub.get("Title") or "").lower().strip()
        if pmid != "N/A" and pmid in seen_pmids:
            continue
        if title and title in seen_titles:
            continue
        if pmid != "N/A":
            seen_pmids.add(pmid)
        if title:
            seen_titles.add(title)
        merged.append(pub)

    return merged


# ============================================================
# Main ranking entry point
# ============================================================

def rank_pathways_by_pubmed_relevance(ranked_significant_df, disease_trait, query_agent):
    """Rank pathways by combined PubMed + Semantic Scholar literature relevance."""
    if ranked_significant_df is None or ranked_significant_df.empty:
        return ranked_significant_df

    literature_scores = []
    validated_publications = []
    number_of_publications = []

    use_semantic = True
    try:
        get_biobert_embedding("test")
    except Exception:
        use_semantic = False
        print("  --| BioBERT unavailable, falling back to keyword-only scoring")

    for i in tqdm(range(len(ranked_significant_df))):
        row = ranked_significant_df.iloc[i]
        name = row["name"]
        keywords = f"{disease_trait} AND {name}"

        pubmed_pubs = query_agent.act("PubMed", {"keywords": keywords, "max_results": 50}) or []
        s2_pubs = query_agent.act("SemanticScholar", {"keywords": f"{disease_trait} {name}", "max_results": 30}) or []

        publications = _merge_publications(pubmed_pubs, s2_pubs)

        if not publications:
            literature_scores.append(0.0)
            validated_publications.append([])
            number_of_publications.append(0)
            continue

        scored_pubs = []
        for pub in publications:
            rel = compute_publication_relevance(pub, disease_trait, name, use_semantic=use_semantic)
            scored_pubs.append((pub, rel))

        scored_pubs.sort(key=lambda x: x[1], reverse=True)

        pathway_score = sum(s for _, s in scored_pubs) / len(scored_pubs) if scored_pubs else 0.0
        top_score = scored_pubs[0][1] if scored_pubs else 0.0
        pathway_score = 0.6 * pathway_score + 0.4 * top_score

        validated = []
        for pub, rel in scored_pubs:
            if rel >= 0.25:
                simplified = {
                    "Title": pub.get("Title", "N/A"),
                    "Abstract": pub.get("Abstract", "N/A"),
                    "PMID": pub.get("PMID", "N/A"),
                    "Journal": pub.get("Journal", "N/A"),
                    "relevance_score": round(rel, 4),
                }
                validated.append(simplified)

        validated_publications.append(validated[:20])
        number_of_publications.append(len(validated))
        literature_scores.append(pathway_score)

    ranked_significant_df["pubmed_relevance"] = literature_scores
    p_rank = ranked_significant_df["p_value"].rank(method="min", ascending=True)
    p_norm = p_rank / p_rank.max() if p_rank.max() > 0 else p_rank
    lit_norm = pd.Series(literature_scores)
    lit_max = lit_norm.max()
    if lit_max > 0:
        lit_norm = lit_norm / lit_max
    lit_norm.index = ranked_significant_df.index

    ranked_significant_df["score"] = (1.0 - lit_norm) * 0.6 + p_norm * 0.4

    ranked_significant_df["validated_publications"] = validated_publications
    ranked_significant_df["num_publications"] = number_of_publications
    ranked_significant_df = ranked_significant_df.sort_values(by=["score"], ascending=True)

    return ranked_significant_df
