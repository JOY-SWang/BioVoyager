def format_publications(citations):
  if citations is None:
    return ""
  if not isinstance(citations, list):
    return ""
  return "\n".join([f"[{i}] {citation['Title']} ({citation['Authors']}, {citation['Publication Date']}) [PMID: {citation['PMID']}]" for i, citation in enumerate(citations)])
  
def get_pubmed_link(pmid):
  if not pmid:
    return ""
  return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
