# Formatting Funcs
def format_pathways(pathway_infos):
  formatted_pathways = "\n".join(
        [f"{item['name']} [TermID: {item['native']}] (p = {item['p_value']}, score = {item['score']}, associated proteins counts = {item['intersection_size']}): {item['description']} (Source: {item['source']})\n"
         for i, item in enumerate(pathway_infos)]
    )
  return formatted_pathways

def format_proteins_functions(protein_functions):
  if protein_functions is None:
    return "No protein functions found."
  if not isinstance(protein_functions, dict):
    return "Invalid protein functions format."
      
  formatted_proteins_functions = "\n".join(
        [f'{protein}: {funcs}' for protein, funcs in protein_functions.items()]
  )
  return formatted_proteins_functions

def format_ppi_knowledge_entries(df):
    entries = []
    for idx, row in enumerate(df.itertuples(index=False), start=1):
        entry = f"[PPI {row.protein1} begin] {row.protein2} - {row.score} - {row.ppi} [PPI {idx} end]"
        entries.append(entry)
    return "\n".join(entries)


# Pathway Reasoning
pathway_overview_sys_tempalte = """
You are a biomedical research assistant who helps summarize biological findings. 
Briefly describe the top-ranked pathways, and the supporting evidence from the literature.  
"""

pathway_overview_prompt_template = """
Here are the top relevant biological pathways associated with this {disease_name}, including their statistical significance:

Table 1: Top Enriched Pathways from Each Source
{formatted_pathways}

# Task:
The input (Table 1) is the top-ranked pathways associated with {disease_name}, please write a concise and informative overview paragraph that summarizes how these pathways may be related to {disease_name}.
Please follow the writing style and the structure in the Writing Example.

# Writing Example:
----
In Table 1, we rank the enriched biological pathways based on a combination of multiple factors through our agent system, including their statistical significance, coherence with existing knowledge and literature, as well as disease specificity. 
Notably, the synaptic vesicle exocytosis pathway (GO:0016079, P < 1.63 × 10−2) and the chemical synaptic transmission pathway (GO:0007268, P < 1.44 × 10−2) highlight the essential roles of neurotransmitter release and synaptic communication, underscoring the impact of impaired synaptic function in the pathology of Alzheimer’s disease.
Furthermore, the enrichment of the neurotransmitter release cycle (REAC:R-HSA-112310, P < 2.4 × 10−2) and the acetylcholine neurotransmitter release cycle (REAC:R-HSA-264642, P < 6.7 × 10−4) suggests potential disruptions in neurotransmitter dynamics. These disruptions can impair cognitive function and are known to play an important role in the development of Alzheimer’s disease.
In addition, enrichment of structural integrity pathways, such as the structural constituent of the cytoskeleton (GO:0005200, P < 1.05 × 10−2), suggests that cytoskeletal anomalies may contribute to the neuronal degeneration observed in Alzheimer’s disease. Similarly, the involvement of neurodevelopmental pathways, including cerebellar cortex maturation (GO:0021699, P < 1.63 × 10−2), points to potential connections between developmental processes and the neurodegenerative changes characteristic of Alzheimer’s disease. 
----

# Response Instructions:
- The overview should be clear and suitable for a scientific audience, providing insights into the potential implications of these pathways in the context of {disease_name}.
- Mention the term ID when relevant.
- Highlight key biological processes, shared mechanisms, and the potential relevance of the p-values.
- Use as much number and data statistics as possible!
- Describe the top-ranked pathways, and the supporting evidence from the literature. 
- DO NOT use any acronym! Don't use any abbreviation!
"""


# Pathway-Disease Analysis
pathway_reasoning_sys_tempalte = """
You are a biomedical research assistant who helps summarize biological findings. Please response in the academic writing style. This will be used as part of academic report. 
"""

pathway_reasoning_prompt_template = """Here is the description and the relevant publications for a biological pathway, please analyze the pathway in the context of {disease_name} disease:

# Pathway Description:
{pathway_info}

# Relevant Publications:
{publication_info}

# Task:
Please analyze the provided publications, and find out how this pathway is related to {disease_name}. 
Please provide a detailed introduction of the pathway, and a narrative coherent and comprehensive paragraph that explains how this pathway is related to {disease_name}.
Use the citation information to support your analysis.
DO NOT use any acronym! Don't use any abbreviation!

# Response Format:
- A json code block with the following format:
```json
{{
  "description": (String)"Detailed introduction of the pathway",
  "explanation": (String)"A narrative coherent and comprehensive paragraph that explains how this pathway is related to {disease_name}",
  "citations": (List) "The citations (from the publications) to support the explanation (PubMed ID if available), in the format of ['PubMed:XXXXX', 'PubMed:XXXXX', ...]"
}}
```
"""

# Protein Reasoning
protein_function_reasoning_sys_tempalte = """
You are a biomedical research assistant who helps summarize biological findings. Please response in the academic writing style. This will be used as part of academic report.
"""

protein_function_reasoning_prompt_template = """ The input is a list of proteins and their functions:
{formatted_proteins_functions}

# Task:
Please identify and summarize the most interesting or relevant protein functions that may have a meaningful connection with {disease_name}. 
Highlight the proteins that stand out, explain why they are important, and relate them to disease mechanisms where possible. 
There are citation information for each protein function, please use them to support your analysis.

# Response Format:
- A json code block with the following format:
```json
{{
  "protein_name": {{
    "function": (String)"The function of the protein",
    "explanation": (String)"A narrative coherent and comprehensive paragraph that explains why this function is important, and how it is related to {disease_name}",
    "citations": (List)"The citations for the function (PubMed ID if available), in the format of ['PubMed:XXXXX', 'PubMed:XXXXX', ...]"
  }}
}}
```
"""

cluster_function_reasoning_sys_tempalte = """
You are a biomedical research assistant who helps summarize biological findings.  Please response in the academic writing style. This will be used as part of academic report.
"""

cluster_function_reasoning_prompt_template = """The input is a list of proteins and their functions:

{formatted_proteins_functions}

# Task:
The input list of protein is a cluster of proteins that shows high protein-protein interaction (PPI) with each other. 
Please summarize the function of the cluster, and how they contribute to {disease_name}. There are citation information for each protein function, please use them to support your analysis. 

# Response Format:
- A json code block with the following format:
```json
{{
  "cluster_function": (String) "The function of the whole cluster",
  "explanation": (String) "A narrative coherent and comprehensive paragraph that explains why this function is important, and how it is related to {disease_name}",
  "citations": (List) "The citations for the function (PubMed ID if available), in the format of ['PubMed:XXXXX', 'PubMed:XXXXX', ...]"  
}}
```
"""



