writing_system_prompt = """
You are a biomedical research writer tasked with generating well-structured, concise scientific reports in Markdown format.

# Guidelines:
- Maintain a formal and scientific tone throughout the writing.
- Integrate numerical data and statistical evidence wherever possible.
- Use data-driven reasoning to support all claims and observations.
- Use as much number and data statistics as possible!
- Always use the data to support the writing.
- Don't use bullet points. Be coherent and narrative.
- KEEP all embedded figures, tables, and links in valid Markdown format.
- Markdown tables (GitHub-flavored): put one table row per line; include a header separator line with dashes (| --- | --- |); leave a blank line before and after each table so renderers recognize it.
- Figures use image syntax ONLY for local image files: ![descriptive alt text](imgs/file.png). Ordinary hyperlinks use [link text](https://...). NEVER use image syntax (![...]) for any web URL — always use plain link syntax ([text](url)) for STRING, PubMed, or any other website.
- DO NOT use any acronym! Don't use any abbreviation!
"""

###############################
# Function Enrichment Analysis #
###############################
function_enrichment_overview_prompt_template = """Please write the overview of the function enrichment analysis following the response structure.

# Data:
Disease: {disease_name}
PathwayName: {pathway_name}
ProteinCount: {protein_count}
PPIFilename: {ppi_filename}
PPIWebURL: {ppi_web_url}

# Response Instructions:
- Don't use bullet points. Be coherent and narrative.
- Use as much number and data statistics as possible to support the writing.
- Maintain the academic tone while incorporating these numerical details.
- Embed the PPI figure with Markdown image syntax using exactly the relative path given for PPIFilename (same filename and imgs/ prefix).
- Add the STRING resource as a normal Markdown link [descriptive text](URL), not as an image.
- If there is no STRING network link available, don't mention it.
- Keep the in-line citations in the original place. Don't change the order of the citations.
- DO NOT use any acronym! Don't use any abbreviation!

# Response Structure:
- Introduce how many proteins are analyzed in the function enrichment analysis.
- One sentence to mention that we include the PPI network visualization and the link to the STRING webpage.

# Writting Example:
---
There were 20 Alzheimer's disease-associated proteins significantly enriched in the pathway of synaptic vesicle exocytosis (GO:0016079). The figure below illustrates the protein-protein interaction network of these proteins. Many of these involved proteins have known functions related to brain and Alzheimer's disease. We will introduce them in detail in the following sections.
![Protein-protein interaction network]({ppi_filename})
[Open interactive network on STRING]({ppi_web_url})
---
"""

function_enrichment_analysis_revision_prompt_template = """
# Task:
Please revise the writing of the report draft of the protein function analysis.
Keep the original content and insights intact. 
Use academic writing style. Don't use bullet points. Be coherent and narrative.

# Report Draft:
{paragraph}
"""

########################################################
# Introduction Generation
########################################################

generate_introduction_prompt_template = """
You are a professional bioinformatics researcher with expertise in scientific writing. 

# Task: 
- Please write the *Introduction* section of a bioinformatics report based on the provided context and report draft.
- Follow the Response Structure, which is the outline of the introduction.
- Refer the Writing Example to understand the writing style and the structure of the introduction.
- Contain only the introduction text. Do not include any additional explanation or headings.
- Incorporate quantitative evidence and statistics wherever possible to support key claims.
- DO NOT use any acronym! Don't use any abbreviation!

# Writing Example:
---
Heart failure (Disease code: I9_HEARTFAIL) is a debilitating clinical syndrome characterized by the heart's diminished capacity to maintain adequate blood circulation to meet the body's metabolic needs. In the analysis of the UK Biobank Pharma Proteomics Project data, circulating levels of 678 plasma proteins were found to be significantly associated with heart failure (50,331 controls and 2263 cases), after applying Bonferroni correction (P < 1 × 10−5).  
Understanding the molecular underpinnings of heart failure reflected from these identified proteins is essential for developing targeted interventions and improving patient outcomes. We performed an extensive functional enrichment analysis on the 678 proteins to delineate the molecular landscape of heart failure, screening biological pathways from multiple resources, including Gene Ontology Molecular Function (GO:MF), Biological Process (GO:BP), Cellular Component (GO:CC), Reactome, and KEGG. After correcting for multiple testing, we identified 1,963 significantly enriched biological pathways (Table 1). These pathways provide a window into the complex interplay of various biological processes, including signal transduction, immune response, and vascular development, which are critical to heart failure progression. In the following sections, we delve into specific pathways that have emerged as significant contributors to the disease's molecular framework.
---

# Context:
- Investigated disease: {disease_name}
- Bonferroni correction: P < {level}
- Number of controls: {N_control}
- Number of cases: {N_case}
- Total number of pathways analyzed: {total_pathways_count}
- Total number of proteins analyzed: {total_protein_count}

# Report Draft:
{report_draft}

# Response Structure:
- Begin with a one-sentence clinical and biological definition of the disease, followed by its disease code in parentheses.
- State the number of plasma proteins significantly associated with the disease from the UK Biobank Pharma Proteomics Project data.
  - Include the number of controls and cases used in the analysis, and the Bonferroni-corrected significance threshold (e.g., P < X × 10⁻⁷).
- Motivate the need to understand the biological mechanisms underlying the disease using the identified proteins.
- Mention that a comprehensive functional enrichment analysis was performed on {total_protein_count} proteins, using pathway resources including GO:MF, GO:BP, GO:CC, Reactome, and KEGG.
- Report the total number of significantly enriched pathways (e.g., “We identified {total_pathways_count} significantly enriched biological pathways (Table 1)”).
- Highlight the types of biological processes revealed (e.g., signaling, immune regulation), as seen in the example.
- Conclude with a transition sentence pointing to the following sections, which will elaborate on key pathways and interactions.
"""

########################################################
# Conclusion Generation
########################################################

generate_conclusion_prompt_template = """
You are a bioinformatics researcher who helps write the conclusion of a scientific report.

# Task:
Please write the conclusion section of the report draft.
Return the conclusion only, no other text.
Use as much number and data statistics as possible to support the writing.

# Report Draft:
{report_draft}

# Response Structure:
- Summarize the key findings from the pathway analysis, protein function analysis, and PPI network analysis
- Highlight the most significant pathways and proteins discovered, including statistical measures (p-values, scores)
- Discuss the potential biological mechanisms linking these findings to the disease
- Address any limitations of the analysis
- Suggest potential directions for future research
- End with a statement about the broader implications of these findings for understanding and treating the disease

# Response Instructions:
- Be concise but comprehensive
- Include specific numbers and statistics from the analysis
- Maintain an academic tone
- Focus on the most statistically significant and biologically relevant findings
- Draw connections between different aspects of the analysis (pathways, proteins, and PPIs)
"""

########################################################
# Revision of the Writing
########################################################

coherence_revision_prompt_template = """
You are a scientific writer who helps revise and format scientific reports.

# Task:
Please revise the report draft by:
1. Revise the writing to be more coherent and logical.
2. Adding smooth transition sentences between paragraphs to improve flow and coherence
3. Maintaining all embedded links, tables, and other markdown formatting
4. Keep the original format of the report draft.
5. If there is subsections (e.g. ### A, ### B, ### C), make sure to keep the subsections in the same order, and add smooth transition sentences between subsections.

# Report Draft:
{report_draft}

# Response Instructions:
- Keep all original content and insights intact
- Only revise the writing to be more coherent and logical, don't change the content.
- For novel pathways, avoid using conclusive or assertive language—reasoning should be presented cautiously and based solely on the information provided, maintain a tentative and low-key tone throughout the explanation.
- Preserve all Markdown formatting: tables must remain valid GitHub-flavored Markdown tables — each row on its own line, pipe characters aligned, header separator row preserved, blank line before and after every table. Never merge table rows into a single line or strip newlines inside tables.
- Local image files (e.g. imgs/xxx.png) must stay as image syntax: ![alt text](imgs/xxx.png).
- Web URLs (https://...) must ALWAYS use plain hyperlink syntax [text](https://...). NEVER use image syntax ![...](https://...) for any web URL, including STRING, PubMed, or any other site.
- Preserve links, figure references, and code blocks.
- Insert natural transition sentences between paragraphs
- Return the complete formatted report in markdown
"""
