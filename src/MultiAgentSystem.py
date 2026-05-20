import os
import json
import copy
import pandas as pd
import time
import logging
import argparse
import itertools

import markdown
from weasyprint import HTML

from agents.ReasoningAgent import ReasoningAgent
from agents.PlanningAgent import PlanningAgent
from agents.WrittingAgent import WrittingAgent
from agents.QueryAgent import QueryAgent

from agents.utils.general_utils import get_pubmed_link, format_citations_inline

def setup_logger(output_path, output_suffix):
    logger = logging.getLogger(output_suffix)
    logger.setLevel(logging.INFO)
    log_file = os.path.join(output_path, f"{output_suffix}.log")
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(fh)
    return logger

class MultiAgentSystemNew:
    def __init__(self, config: dict):
        self.planning_agent = PlanningAgent(model=config.get("planning_model", "gpt-4o"))
        self.reasoning_agent = ReasoningAgent(model=config.get("reasoning_model", "gpt-4o"))
        self.writting_agent = WrittingAgent(model=config.get("writting_model", "gpt-4o"))
        self.query_agent = QueryAgent(model=config.get("query_model", "gpt-4o"))
        self.config = config
        result_dir = self.config.get('result_dir', '.')
        os.makedirs(result_dir, exist_ok=True)
        self.main_logger = setup_logger(result_dir, 'main')

    def run(self, test_data_dir, test_data_range):
        test_data_name = []
        for file in os.listdir(test_data_dir):
            if file.endswith(".csv"):
                test_data_name.append(file)

        for idx, test_file in enumerate(test_data_name[test_data_range[0]:test_data_range[1]]):
            try:
                test_data = pd.read_csv(os.path.join(test_data_dir, test_file))
                disease_file_name = test_file.split(".")[0]
                disease_name = self.planning_agent.sanitize_disease_name(disease_file_name)
                result_dir = f"{self.config['result_dir']}/{disease_file_name}"
                img_dir = f"{result_dir}/imgs"
                os.makedirs(result_dir, exist_ok=True)
                os.makedirs(img_dir, exist_ok=True)
                protein_list = test_data["Protein"].tolist()
                
                # Per-disease logger
                logger = setup_logger(result_dir, disease_file_name)
                logger.info(f"Processing disease: {disease_name}({disease_file_name})")
                logger.info(f"Protein list (Count: {len(protein_list)}): {protein_list}")
                self.main_logger.info(f"Processing {disease_name} ({disease_file_name}) [{idx+1}/{test_data_range[1]-test_data_range[0]}]")

                # Initialize report_draft & citation map
                report_draft = ""
                
                # Planning Agent Act
                logger.info("-| PlanningAgent Acting..")
                ranked_significant_pubmed_df, wellknown_pathways, novel_pathways = self.planning_agent.act(protein_list, disease_name, query_agent=self.query_agent)

                total_protein_count = len(protein_list)
                total_pathways_count = len(ranked_significant_pubmed_df)
                logger.info(f"-| PlanningAgent: found {total_pathways_count} total pathways for {total_protein_count} proteins")

                #########################
                # Pathway Section Overview
                #########################
                logger.info("-| Generating Enriched Pathway Overview")
                pathway_overview = self.reasoning_agent.act("Pathway_Section_Overview", {"pathway_infos": wellknown_pathways.to_dict(orient="records"), "disease_name": disease_name})

                # Append Enriched Pathway Overview to report_draft
                report_draft += "## Overview of the Enriched Pathways\n\n"
                report_draft += pathway_overview
                report_draft += "\n\n## Enriched Pathways Analysis\n\n"

                #########################
                # Wellknown Pathway Analysis
                #########################
                logger.info("-| Generating Wellknown Pathway Analysis")
                for index, row in itertools.islice(wellknown_pathways.iterrows(), 0, 6):
                    logger.info("-| Wellknown Pathway Analysis for: %s", row['name'])

                    content = f"\n\n### {row['name']} ({row['native']}) \n\n"
  
                    pathway_info = row["name"] + ": " + row["description"]
                    pathway_publications = row["validated_publications"]

                    pathway_analysis = self.reasoning_agent.act("Wellknown_Pathway_Analysis", {"disease_name": disease_name, "pathway_info": pathway_info, "publication_info": pathway_publications})
                    pathway_analysis_content = pathway_analysis["description"] + "\n" + pathway_analysis["explanation"]
                    for citation in pathway_analysis["citations"]:
                        pmid = citation.split(":")[1].strip()
                        pmid_url = get_pubmed_link(pmid)
                        pathway_analysis_content += f"[{citation}]({pmid_url}) "
                        
                    pathway_analysis_content += "\n\n"
                    
                    content += pathway_analysis_content

                    protein_list = row["intersections"]
                    protein_list = [protein.strip() for protein in protein_list]
                    logger.info("   --| Protein Function Enrichment Analysis")
                    logger.info("     ---| PPI Analysis")
                    protein_count, extracted_ppi_data, filename, web_url = self.reasoning_agent.act("PPI_Analysis", {"proteins_list": protein_list, "disease_name": disease_name, "query_agent": self.query_agent, "img_dir": img_dir})
                    logger.info("     ---| Cluster Function Analysis")
                    cluster, cluster_functions = self.reasoning_agent.act("Cluster_Function_Analysis", {"extracted_ppi_data": extracted_ppi_data, "disease_name": disease_name, "query_agent": self.query_agent})
                    logger.info("     ---| Protein Function Analysis")
                    cluster_expanded = [protein for cluster in cluster for protein in cluster]
                    rest_proteins = [protein for protein in protein_list if protein not in cluster_expanded]
                    protein_functions = self.reasoning_agent.act("Protein_Function_Analysis", {"proteins_list": rest_proteins, "disease_name": disease_name, "query_agent": self.query_agent})
                    logger.info("     ---| Summarize Function Enrichment Analysis")
                    protein_function_enrichment = self.reasoning_agent.act("Function_Enrichment_Analysis", {"protein_count": protein_count, "ppi_filename": filename, "ppi_web_url": web_url, "protein_functions": protein_functions, "cluster_functions": cluster_functions})
                    logger.info("     ---| Function Enrichment Overview")
                    function_enrichment_overview = self.writting_agent.act("Function_Enrichment_Overview", {"disease_name": disease_name, "pathway_name": pathway_analysis["description"], "protein_count": protein_function_enrichment["protein_count"], "ppi_filename": protein_function_enrichment["ppi_filename"], "ppi_web_url": protein_function_enrichment["ppi_web_url"]})

                    logger.info("   --| Protein Function Enrichment Writting")
                    content += function_enrichment_overview

                    logger.info("     ---| Protein Function Writting")
                    protein_function_analysis = ""
                    protein_function = protein_function_enrichment["protein_function"]
                    citations = protein_function["citations"]
                    if len(protein_function["chunks"]) > 0:
                        content += "\n\nDuring the function enrichment analysis, we identified serveral significant proteins. We will introduce them in-details in the following.\n"
                        for index, chunk in enumerate(protein_function["chunks"]):
                            protein_function_analysis += chunk
                            if len(citations[index]) > 0:
                                for citation in citations[index]:
                                    pmid = citation.split(":")[1].strip()
                                    pmid_url = get_pubmed_link(pmid)
                                    protein_function_analysis += f"[{citation}]({pmid_url}) "
                            protein_function_analysis += "\n"
                    content += protein_function_analysis
                    content += "\n"

                    logger.info("     ---| Cluster Function Writting")
                    cluster_function_analysis = ""
                    cluster_function = protein_function_enrichment["cluster_function"]
                    citations = cluster_function["citations"]
                    if len(cluster_function["chunks"]) > 0:
                        for index, chunk in enumerate(cluster_function["chunks"]):
                            cluster_function_analysis += chunk
                            if len(citations[index]) > 0:
                                for citation in citations[index]:
                                    pmid = citation.split(":")[1].strip()
                                    pmid_url = get_pubmed_link(pmid)
                                    cluster_function_analysis += f"[{citation}]({pmid_url}) "
                            cluster_function_analysis += "\n"
                    content += "There are also small set of proteins function together to form a cluster."
                    content += cluster_function_analysis  

                    report_draft += content

                # Writing report draft
                with open(f"{result_dir}/report_draft_{disease_name}.md", "w") as f:
                    f.write(report_draft)    

                #########################
                # Novel Enriched Pathways
                #########################

                logger.info("-| Novel Enriched Pathways")
                report_draft += """\n\n## Novel Enriched Pathways

                In addition to the well-established pathways discussed above, our analysis also uncovered several novel or less commonly emphasized pathways that were significantly enriched. These pathways provide fresh perspectives on the molecular underpinnings of Parkinson's disease and may represent untapped opportunities for therapeutic innovation. The following sections explore these novel findings in detail.

                -----\n\n"""

                for index, row in itertools.islice(novel_pathways.iterrows(), 0, 6):
                    logger.info(f"-| Novel Enriched Pathway Analysis: {row['name']}")
                    
                    content = f"\n\n### {row['name']} ({row['native']}) \n\n"
                    
                    pathway_info = row["name"] + ": " + row["description"]
                    pathway_analysis = self.reasoning_agent.act("Novel_Pathway_Analysis", {"disease_name": disease_name, "pathway_info": pathway_info})
                    content += pathway_analysis["description"] + "\n" + pathway_analysis["explanation"]
                    
                    protein_list = row["intersections"]
                    protein_list = [protein.strip() for protein in protein_list]
                    logger.info("   --| Protein Function Enrichment Analysis")
                    logger.info("     ---| PPI Analysis")
                    protein_count, extracted_ppi_data, filename, web_url = self.reasoning_agent.act("PPI_Analysis", {"proteins_list": protein_list, "disease_name": disease_name, "query_agent": self.query_agent, "img_dir": img_dir})
                    logger.info("     ---| Cluster Function Analysis")
                    cluster, cluster_functions = self.reasoning_agent.act("Cluster_Function_Analysis", {"extracted_ppi_data": extracted_ppi_data, "disease_name": disease_name, "query_agent": self.query_agent})
                    logger.info("     ---| Protein Function Analysis")
                    cluster_expanded = [protein for cluster in cluster for protein in cluster]
                    rest_proteins = [protein for protein in protein_list if protein not in cluster_expanded]
                    protein_functions = self.reasoning_agent.act("Protein_Function_Analysis", {"proteins_list": rest_proteins, "disease_name": disease_name, "query_agent": self.query_agent})
                    logger.info("     ---| Summarize Function Enrichment Analysis")
                    protein_function_enrichment = self.reasoning_agent.act("Function_Enrichment_Analysis", {"protein_count": protein_count, "ppi_filename": filename, "ppi_web_url": web_url, "protein_functions": protein_functions, "cluster_functions": cluster_functions})
                    logger.info("     ---| Function Enrichment Overview")
                    function_enrichment_overview = self.writting_agent.act("Function_Enrichment_Overview", {"disease_name": disease_name, "pathway_name": pathway_analysis["description"], "protein_count": protein_function_enrichment["protein_count"], "ppi_filename": protein_function_enrichment["ppi_filename"], "ppi_web_url": protein_function_enrichment["ppi_web_url"]})
                    
                    content += function_enrichment_overview
                    content += "\n\nDuring the function enrichment analysis, we identified serveral significant proteins. We will introduce them in-details in the following.\n"

                    logger.info("     ---| Protein Function Writting")
                    protein_function_analysis = ""
                    protein_function = protein_function_enrichment["protein_function"]
                    citations = protein_function["citations"]
                    if len(protein_function["chunks"]) > 0:
                        for index, chunk in enumerate(protein_function["chunks"]):
                            protein_function_analysis += chunk
                            if len(citations[index]) > 0:
                                for citation in citations[index]:
                                    pmid = citation.split(":")[1].strip()
                                    pmid_url = get_pubmed_link(pmid)
                                    protein_function_analysis += f"[{citation}]({pmid_url}) "
                    content += protein_function_analysis
                    content += "\n"
                    
                    logger.info("     ---| Cluster Function Writting")
                    cluster_function_analysis = ""
                    cluster_function = protein_function_enrichment["cluster_function"]
                    citations = cluster_function["citations"] 
                    if len(cluster_function["chunks"]) > 0:
                        for index, chunk in enumerate(cluster_function["chunks"]):
                            cluster_function_analysis += chunk
                            if len(citations[index]) > 0:
                                for citation in citations[index]:
                                    pmid = citation.split(":")[1].strip() 
                                    pmid_url = get_pubmed_link(pmid)
                                    cluster_function_analysis += f"[{citation}]({pmid_url}) "
                            cluster_function_analysis += "\n"
                    content += "There are also small set of proteins function together to form a cluster."
                    content += cluster_function_analysis  
                    report_draft += content
                   
                with open(f"{result_dir}/report_draft_{disease_name}.md", "w") as f:
                    f.write(report_draft)

                total_pathways_count = len(ranked_significant_pubmed_df)
                introduction = self.writting_agent.act("Introduction", {"report_draft": report_draft, "disease_name": disease_name, "total_pathways_count": total_pathways_count, "total_protein_count": total_protein_count})

                draft_with_introduction = "## Introctction\n\n" + introduction + "\n\n" + report_draft

                with open(f"{result_dir}/{disease_name}_v1.md", "w") as f:
                    f.write(draft_with_introduction)
                    
                revised_report_draft = self.writting_agent.act("Finalize_Report", {"report_draft": report_draft})
                revised_report_draft = "## Introctction\n\n" + introduction + "\n\n" + revised_report_draft
                with open(f"{result_dir}/{disease_name}_v2.md", "w") as f:
                    f.write(revised_report_draft)


                ######################
                # Formatting Citations
                ######################
                logger.info("-| Formatting Citations")
                formatted_citation_draft, ordered_pmids = format_citations_inline(revised_report_draft)


                ############################
                # Adding Citation References
                ############################
                logger.info("-| Adding Citation References")
                references = []
                for i, pmid in enumerate(ordered_pmids):
                    try:
                        pub = self.query_agent.act("PubMed_by_ID", {"pmid": pmid})
                        if pub:
                            authors = ', '.join(pub.get("Authors", []))
                            title = pub.get("Title", "N/A")
                            journal = pub.get("Journal", "N/A")
                            pub_date = pub.get("Publication Date", "N/A")
                            ref_line = f"[{i+1}]({get_pubmed_link(pmid)}) {authors}. {title}. *{journal}*. {pub_date}."
                            references.append(ref_line)
                        else:
                            logger.warning(f"No publication found for PMID: {pmid}")
                    except Exception as e:
                        logger.error(f"Error fetching reference for PMID {pmid}: {e}")
                
                
                ############################
                # Appending Reference Section
                ############################
                logger.info("-| Appending References to Report")
                formatted_citation_draft += "\n\n## References\n\n" + "\n\n".join(references)

                ############################
                # Saving Final Report to File
                ############################
                logger.info("-| Writing Final Report to File")
                draft_with_citations_and_references_path = f"{result_dir}/report_draft_{disease_name}_with_citations_and_references.md"
                with open(draft_with_citations_and_references_path, "w") as f:
                    f.write(formatted_citation_draft)
                logger.info(f"-| Final report saved to: {draft_with_citations_and_references_path}")

            except Exception as e:
                    logger.error(f"[Error] Error processing {test_file}: {e}", exc_info=True)
                    self.main_logger.error(f"[Error] Error processing {test_file}: {e}", exc_info=True)

    def run_reference_append_test(self):
        import os

        logger = setup_logger(".", "citation_reference_test")

        # 1. Load the revised report draft
        input_path = "/home/ubuntu/BMAgent/src/report_draft_with_introduction_parkinsons.md"
        if not os.path.exists(input_path):
            logger.error(f"Input file not found: {input_path}")
            return
        
        with open(input_path, "r") as f:
            revised_report_draft = f.read()

        # 2. Format citations
        logger.info("Formatting citations...")
        formatted_citation_draft, ordered_pmids = format_citations_inline(revised_report_draft)

        # 4. Fetch references
        logger.info("Querying references for PMIDs...")
        references = []
        for i, pmid in enumerate(ordered_pmids):
            try:
                pub = self.query_agent.act("PubMed_by_ID", {"pmid": pmid})
                if pub:
                    authors = ', '.join(pub.get("Authors", []))
                    title = pub.get("Title", "N/A")
                    journal = pub.get("Journal", "N/A")
                    pub_date = pub.get("Publication Date", "N/A")
                    ref_line = f"[[{i+1}]]({get_pubmed_link(pmid)}) {authors}. {title}. *{journal}*. {pub_date}. (PMID: {pmid})"
                    references.append(ref_line)
                else:
                    logger.warning(f"No publication found for PMID: {pmid}")
            except Exception as e:
                logger.error(f"Error fetching reference for PMID {pmid}: {e}")

        # 5. Append references
        logger.info("Appending references to report...")
        formatted_citation_draft += "\n\n## References\n\n" + "\n\n".join(references)

        # 6. Save the final output
        output_path = input_path.replace(".md", "_with_citations_and_references.md")
        with open(output_path, "w") as f:
            f.write(formatted_citation_draft)

        logger.info(f"Test output written to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_data_dir", type=str, default="/Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/test_data", help="Directory containing test data CSV files.")
    parser.add_argument("--result_dir", type=str, default="/Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/src/results_0411", help="Directory to store results.")
    parser.add_argument("--start", type=int, default=0, help="Start index for test data range.")
    parser.add_argument("--end", type=int, default=1, help="End index for test data range (exclusive).")
    parser.add_argument("--planning_model", type=str, default="gpt-4o", help="Model for PlanningAgent.")
    parser.add_argument("--reasoning_model", type=str, default="gpt-4o", help="Model for ReasoningAgent.")
    parser.add_argument("--writting_model", type=str, default="gpt-4o", help="Model for WrittingAgent.")
    parser.add_argument("--query_model", type=str, default="gpt-4o", help="Model for QueryAgent.")
    args = parser.parse_args()

    config = {
        "planning_model": args.planning_model,
        "reasoning_model": args.reasoning_model,
        "writting_model": args.writting_model,
        "query_model": args.query_model,
        "result_dir": args.result_dir
    }
    test_data_dir = args.test_data_dir
    test_data_range = [args.start, args.end]
    
    multi_agent_system = MultiAgentSystemNew(config)
    # multi_agent_system.run(test_data_dir, test_data_range)
    multi_agent_system.run_reference_append_test()  # For testing reference appending functionality


