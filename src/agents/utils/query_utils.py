import json
import time
from .db_utils import execute_query

# PPI query
def query_ppi(target_proteins, ppi_data):
    if len(target_proteins) < 2:
        return None, None
    filtered_data = ppi_data[ppi_data["protein1"].isin(target_proteins)]
    extracted_ppi_data = filtered_data[filtered_data["protein2"].isin(
        target_proteins)]
    extracted_ppi_data = extracted_ppi_data.sort_values(
        by="score", ascending=False)
    protein_with_no_connections = set(target_proteins) - set(
        extracted_ppi_data["protein1"].unique()) - set(extracted_ppi_data["protein2"].unique())
    
    return extracted_ppi_data, list(protein_with_no_connections)

def find_cluster_from_ppi(extracted_ppi_data, k=5):
    if extracted_ppi_data is None or extracted_ppi_data.empty:
        return []
    
    import networkx as nx
    G = nx.Graph()
    for _, row in extracted_ppi_data.iterrows():
        G.add_edge(row['protein1'], row['protein2'], weight=row['score'])
    clusters = list(nx.connected_components(G))
    
    def cluster_score(cluster):
        total_weight = 0
        for node1 in cluster:
            for node2 in cluster:
                if node1 != node2 and G.has_edge(node1, node2):
                    total_weight += G[node1][node2]['weight']
        return total_weight

    sorted_clusters = sorted(clusters, key=lambda x: (cluster_score(x), len(x)), reverse=True)
    
    return [list(cluster) for cluster in sorted_clusters[:k]]
    
  
# Protein functions query
def query_protein_functions(proteins, protein_functions):
    functions = {}
    for protein in proteins:
        if protein in protein_functions:
            functions[protein] = protein_functions[protein][0]["functions"]
        else:
            functions[protein] = "Function not found"
    return functions
  
# Pubmed query
from Bio import Entrez, Medline
from io import StringIO

def query_pubmed(keywords, max_results=10):
    """PubMed search without restrictive journal filter; returns richer metadata."""
    if not keywords or not isinstance(keywords, str) or keywords.strip() == "":
        print(f"Invalid keywords: {keywords}")
        return []
    Entrez.email = "test@gmail.com"
    Entrez.tool = "PubMedQueryTool"

    with Entrez.esearch(db="pubmed", term=keywords, retmax=max_results * 3, sort="relevance") as search_handle:
        search_results = Entrez.read(search_handle)
        id_list = search_results["IdList"]
    time.sleep(1)
    if not id_list:
        return []
    with Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="medline", retmode="text") as fetch_handle:
        records_text = fetch_handle.read()
    time.sleep(1)
    records = list(Medline.parse(StringIO(records_text)))
    publications = []
    for record in records:
        pub_info = {
            "Title": record.get("TI", "N/A"),
            "Authors": record.get("AU", []),
            "Abstract": record.get("AB", "N/A"),
            "Journal": record.get("JT", "N/A"),
            "Publication Date": record.get("DP", "N/A"),
            "PMID": record.get("PMID", "N/A"),
            "Source": record.get("SO", "N/A"),
        }
        publications.append(pub_info)

    publications = [pub for pub in publications if pub["Abstract"] != "N/A"]
    unique_publications = []
    seen_titles = set()
    for pub in publications:
        title = pub["Title"]
        if title not in seen_titles:
            seen_titles.add(title)
            unique_publications.append(pub)
    unique_publications.sort(key=lambda x: x["Publication Date"], reverse=True)
    publications = unique_publications[:max_results]
    return publications


# ============================================================
# Semantic Scholar search (keyword + snippet)
# ============================================================
import os
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_S2_GRAPH_API = "https://api.semanticscholar.org/graph/v1"
_S2_PAPER_FIELDS = (
    "paperId,corpusId,url,title,abstract,authors,authors.name,"
    "year,venue,citationCount,externalIds,isOpenAccess"
)


def _s2_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.3,
                  status_forcelist=(429, 500, 502, 504),
                  allowed_methods=("GET", "POST"))
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _s2_headers():
    key = os.environ.get("S2_API_KEY")
    return {"x-api-key": key} if key else {}


def query_semantic_scholar(keywords, max_results=20):
    """Keyword search on Semantic Scholar. Returns list[dict] aligned with PubMed format."""
    if not keywords or not isinstance(keywords, str) or keywords.strip() == "":
        return []
    session = _s2_session()
    try:
        resp = session.get(
            f"{_S2_GRAPH_API}/paper/search",
            params={"query": keywords, "limit": min(max_results, 100),
                    "fields": _S2_PAPER_FIELDS},
            headers=_s2_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception as e:
        logging.warning(f"Semantic Scholar keyword search failed: {e}")
        return []

    publications = []
    for paper in data:
        pmid = (paper.get("externalIds") or {}).get("PubMed")
        authors = [a.get("name", "") for a in (paper.get("authors") or [])]
        pub = {
            "Title": paper.get("title") or "N/A",
            "Authors": authors,
            "Abstract": paper.get("abstract") or "N/A",
            "Journal": paper.get("venue") or "N/A",
            "Publication Date": str(paper.get("year") or "N/A"),
            "PMID": pmid or "N/A",
            "Source": "SemanticScholar",
            "CitationCount": paper.get("citationCount") or 0,
            "S2_PaperId": paper.get("paperId"),
        }
        publications.append(pub)

    publications = [p for p in publications if p["Abstract"] != "N/A"]
    return publications


def query_semantic_scholar_snippets(query, max_results=10):
    """Snippet search on Semantic Scholar (requires S2_API_KEY).
    Returns list of snippet dicts with paper metadata."""
    if not query or not isinstance(query, str) or query.strip() == "":
        return []
    session = _s2_session()
    headers = _s2_headers()
    if not headers.get("x-api-key"):
        logging.warning("S2_API_KEY not set; snippet search unavailable.")
        return []
    try:
        resp = session.get(
            f"{_S2_GRAPH_API}/snippet/search",
            params={"query": query, "limit": min(max_results, 100)},
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        items = resp.json().get("data", [])
    except Exception as e:
        logging.warning(f"Semantic Scholar snippet search failed: {e}")
        return []

    results = []
    for item in items:
        snippet_text = ""
        if item.get("snippet"):
            snippet_text = item["snippet"].get("text", "")
        paper = item.get("paper", {})
        pmid = (paper.get("externalIds") or {}).get("PubMed")
        results.append({
            "snippet": snippet_text,
            "Title": paper.get("title") or "N/A",
            "Abstract": paper.get("abstract") or "N/A",
            "PMID": pmid or "N/A",
            "S2_PaperId": paper.get("paperId"),
            "Year": paper.get("year"),
            "CitationCount": paper.get("citationCount") or 0,
        })
    return results

def query_pubmed_by_id(pubmed_id):
    from Bio import Entrez, Medline
    from io import StringIO

    if not pubmed_id or not isinstance(pubmed_id, str):
        print(f"Invalid PubMed ID: {pubmed_id}")
        return None

    Entrez.email = "test@gmail.com"
    Entrez.tool = "PubMedQueryTool"

    try:
        with Entrez.efetch(db="pubmed", id=pubmed_id, rettype="medline", retmode="text") as fetch_handle:
            records_text = fetch_handle.read()

        records = list(Medline.parse(StringIO(records_text)))
        if not records:
            return None

        record = records[0]
        pub_info = {
            "Title": record.get("TI", "N/A"),
            "Authors": record.get("AU", []),
            "Abstract": record.get("AB", "N/A"),
            "Journal": record.get("JT", "N/A"),
            "Publication Date": record.get("DP", "N/A"),
            "PMID": record.get("PMID", pubmed_id),
            "Source": record.get("SO", "N/A"),
        }

        return pub_info

    except Exception as e:
        print(f"Error querying PubMed ID {pubmed_id}: {e}")
        return None

# opentargets graphql 
# Schema reference: https://api.platform.opentargets.org/api/v4/graphql/schema
# API refernce: https://platform-docs.opentargets.org/data-access/graphql-api
import requests
import json

OT_GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"


def search_target_protein(protein):
    query = """
    query Search($queryString: String!) {
      search(queryString: $queryString) {
        hits {
          id
          entity
          name
        }
      }
    }
    """
    response = requests.post(
        OT_GRAPHQL_URL,
        json={"query": query, "variables": {"queryString": protein}}
    ).json()

    hits = response.get("data", {}).get("search", {}).get("hits", [])

    for hit in hits:
        if hit["entity"] == "target" and hit["name"].lower() == protein.lower():
            return hit["id"]

    for hit in hits:
        if hit["entity"] == "target":
            return hit["id"]

    return None


def query_target_description(ensembl_id):
    query = """
    query TargetProfileQuery($ensgId: String!) {
      target(ensemblId: $ensgId) {
        functionDescriptions
      }
    }
    """
    response = requests.post(
        OT_GRAPHQL_URL,
        json={"query": query, "variables": {"ensgId": ensembl_id}}
    ).json()

    if "errors" in response:
        raise ValueError(f"GraphQL error: {response['errors']}")

    descriptions = response.get("data", {}).get("target", {}).get("functionDescriptions", [])
    return descriptions[0] if descriptions else None

def query_target_known_drugs(ensembl_id, page_size=20):
    query = """
    query KnownDrugsQuery($ensgId: String!, $cursor: String, $freeTextQuery: String, $size: Int!) {
      target(ensemblId: $ensgId) {
        knownDrugs(cursor: $cursor, freeTextQuery: $freeTextQuery, size: $size) {
          count
          cursor
          rows {
            phase
            status
            urls {
              name
              url
            }
            disease {
              id
              name
            }
            drug {
              id
              name
              mechanismsOfAction {
                rows {
                  actionType
                  targets {
                    id
                  }
                }
              }
            }
            drugType
            mechanismOfAction
          }
        }
      }
    }
    """

    all_rows = []
    cursor = None

    while True:
        variables = {
            "ensgId": ensembl_id,
            "cursor": cursor,
            "freeTextQuery": "",
            "size": page_size
        }

        response = requests.post(OT_GRAPHQL_URL, json={"query": query, "variables": variables}).json()

        if "errors" in response:
            raise ValueError(f"GraphQL error: {response['errors']}")

        known_drugs = response.get("data", {}).get("target", {}).get("knownDrugs", {})
        rows = known_drugs.get("rows", [])
        all_rows.extend(rows)

        cursor = known_drugs.get("cursor")
        if not cursor:
            break  # No more pages

    return all_rows

def query_target_bibliography(ensembl_id):
    query = """
    query SimilarEntitiesQuery(
      $id: String!,
      $ids: [String!] = [],
      $startYear: Int = null,
      $startMonth: Int = null,
      $endYear: Int = null,
      $endMonth: Int = null,
      $cursor: String = null
    ) {
      target(ensemblId: $id) {
        literatureOcurrences(
          additionalIds: $ids,
          cursor: $cursor,
          startYear: $startYear,
          startMonth: $startMonth,
          endYear: $endYear,
          endMonth: $endMonth
        ) {
          count
          filteredCount
          earliestPubYear
          cursor
          rows {
            pmid
            pmcid
            publicationDate
          }
        }
      }
    }
    """

    variables = {
        "id": ensembl_id,
        "ids": [],
        "startYear": None,
        "startMonth": None,
        "endYear": None,
        "endMonth": None,
        "cursor": None
    }

    response = requests.post(
        OT_GRAPHQL_URL,
        json={"query": query, "variables": variables}
    ).json()

    if "errors" in response:
        raise ValueError(f"GraphQL error: {response['errors']}")

    rows = response.get("data", {}).get("target", {}).get("literatureOcurrences", {}).get("rows", [])
    return rows


def query_target_associated_diseases(ensembl_id, page_size=100):
    query = """
    query TargetAssociationsQuery(
        $id: String!,
        $index: Int!,
        $size: Int!,
        $sortBy: String!,
        $enableIndirect: Boolean!,
        $datasources: [DatasourceSettingsInput!],
        $rowsFilter: [String!],
        $facetFilters: [String!],
        $entitySearch: String!
    ) {
      target(ensemblId: $id) {
        id
        approvedSymbol
        associatedDiseases(
          page: {index: $index, size: $size},
          orderByScore: $sortBy,
          enableIndirect: $enableIndirect,
          datasources: $datasources,
          Bs: $rowsFilter,
          facetFilters: $facetFilters,
          BFilter: $entitySearch
        ) {
          count
          rows {
            disease {
              id
              name
            }
            score
            datasourceScores {
              id
              score
            }
          }
        }
      }
    }
    """

    datasources = [
        {"id": ds_id, "weight": 1, "propagate": True, "required": False}
        for ds_id in [
            "gwas_credible_sets", "gene_burden", "eva", "genomics_england",
            "gene2phenotype", "uniprot_literature", "uniprot_variants", "orphanet",
            "clingen", "cancer_gene_census", "intogen", "eva_somatic", "cancer_biomarkers",
            "chembl", "crispr_screen", "crispr", "slapenrich", "progeny", "reactome",
            "sysbio", "europepmc", "expression_atlas", "impc", "ot_crispr_validation",
            "ot_crispr", "encore"
        ]
    ]
    # Special weights
    for d in datasources:
        if d["id"] in {"slapenrich", "progeny", "sysbio", "europepmc", "expression_atlas", "impc", "ot_crispr", "ot_crispr_validation", "encore"}:
            d["weight"] = 0.5 if d["id"] not in {"europepmc", "expression_atlas", "impc"} else 0.2

    all_rows = []
    page_index = 0
    total_count = None

    while True:
        variables = {
            "id": ensembl_id,
            "index": page_index,
            "size": page_size,
            "sortBy": "score",
            "enableIndirect": False,
            "datasources": datasources,
            "rowsFilter": [],
            "facetFilters": [],
            "entitySearch": ""
        }

        response = requests.post(OT_GRAPHQL_URL, json={"query": query, "variables": variables}).json()

     
        if "errors" in response:
            raise ValueError(f"GraphQL error: {response['errors']}")

        data = response.get("data", {}).get("target", {}).get("associatedDiseases", {})
        rows = data.get("rows", [])
        all_rows.extend(rows)

        total_count = data.get("count", 0)
        if len(all_rows) >= total_count:
            break

        page_index += 1

    return all_rows
