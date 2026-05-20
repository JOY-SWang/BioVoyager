def get_pubmed_link(pmid):
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"

def format_citations_inline(report_draft):
    import re

    # Step 1: Special case for (e.g., PMID:..., ...)
    eg_pattern = re.compile(r'\(e\.g\.,\s*(.*?)\)')

    pmid_to_number = {}
    ordered_pmids = []

    def replace_eg_block(match):
        original = match.group(0)
        content = match.group(1)

        pmid_matches = re.findall(r'(?:PMID:|PubMed:)?\s*(\d{5,})', content)
        replacement = "(e.g., "
        seen = set()
        for i, pmid in enumerate(pmid_matches):
            if pmid not in pmid_to_number:
                pmid_to_number[pmid] = len(ordered_pmids) + 1
                ordered_pmids.append(pmid)
            if pmid not in seen:
                if i > 0:
                    replacement += ", "
                replacement += f"[[{pmid_to_number[pmid]}]]({get_pubmed_link(pmid)})"
                seen.add(pmid)
        replacement += ")"
        return replacement

    report_draft = re.sub(eg_pattern, replace_eg_block, report_draft)

    # Step 2: General citations
    pattern = re.compile(r"""
        \[PubMed:(\d+)\]\(https?://pubmed\.ncbi\.nlm\.nih\.gov/\d+\)     # [PubMed:12345678](...)
        |
        \(
            (?:
                (?:PubMed|PMID):\s*\d+ | \d+                              # PubMed:12345678 or just digits
            )
            (?:
                [,;]\s*
                (?:
                    (?:PubMed|PMID):\s*\d+ | \d+
                )
            )*
        \)
    """, re.VERBOSE)

    citation_blocks = list(pattern.finditer(report_draft))

    for block in citation_blocks:
        raw_text = block.group(0)
        pmid_matches = re.findall(r'(?:PubMed|PMID):\s*(\d+)|\b(\d{5,})\b', raw_text)
        for match in pmid_matches:
            pmid = match[0] if match[0] else match[1]
            if pmid not in pmid_to_number:
                pmid_to_number[pmid] = len(ordered_pmids) + 1
                ordered_pmids.append(pmid)

    def replace_citation(match):
        raw_text = match.group(0)
        pmid_matches = re.findall(r'(?:PubMed|PMID):\s*(\d+)|\b(\d{5,})\b', raw_text)
        replacement = ""
        seen = set()
        for match in pmid_matches:
            pmid = match[0] if match[0] else match[1]
            if pmid in pmid_to_number and pmid not in seen:
                number = pmid_to_number[pmid]
                replacement += f"[[{number}]]({get_pubmed_link(pmid)}) "
                seen.add(pmid)
        return replacement.strip()

    formatted_text = re.sub(pattern, replace_citation, report_draft)

    return formatted_text, ordered_pmids
