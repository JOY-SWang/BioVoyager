#!/usr/bin/env python3
"""
generate_v3.py — BioInsight v3 Interactive HTML Generator
Converts XXX.csv + XXX_v1.html → XXX_v3.html

Usage:
    python generate_v3.py --csv /Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/test_data/Alzheimer_disease.csv --v1 /Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/src/results_0411/alzheimer/Alzheimer_disease_v1.html
    python generate_v3.py --csv test_data/Disease.csv --v1 src/results_0411/subdir/Disease_v1.html --out output.html
    python generate_v3.py --batch   (auto-discover all diseases)

Directories (can be overridden via --csv-dir / --html-dir):
    CSV:  <BASE>/test_data/
    HTML: <BASE>/src/results_0411/<subfolder>/
"""

import re, csv, sys, json, os, argparse, html as html_mod
import urllib.request, urllib.parse
from pathlib import Path
from collections import defaultdict

# Load .env from same directory as this script
_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # drug-target-agent/
CSV_DIR  = BASE_DIR / "test_data"
HTML_DIR = BASE_DIR / "src" / "results_0411"
PROTEIN_COLOR = "#6b7280"
PATHWAY_COLOR = "#016994"

# Drug keyword → drug node label mapping
DRUG_KEYWORDS = {
    "Synaptic Mod.":    ["synap", "neuro", "axon", "vesicle", "transmitter", "acetylcholin",
                         "glutamat", "dopamin", "seroton"],
    "Anti-inflammatory":["interleukin", "cytokine", "immun", "inflam", "complement",
                         "tumor necrosis", "interferon", "lymphocyte", "macrophage"],
    "Metabolic/Lipid":  ["lipid", "cholesterol", "lipoprotein", "metabolic", "triglyceride",
                         "apolipoprotein", "glucose", "insulin", "adipose"],
    "Anti-fibrotic":    ["collagen", "fibros", "matrix", "elastin", "fibroblast",
                         "extracellular matrix", "laminin", "connective"],
    "Targeted Therapy": [],  # catch-all
}

# Color schemes per broad disease category keyword
DISEASE_COLORS = {
    "cardiac": {"pathway": PATHWAY_COLOR, "protein": PROTEIN_COLOR, "drug": "#1b5e20"},
    "neuro":   {"pathway": PATHWAY_COLOR, "protein": PROTEIN_COLOR, "drug": "#1b5e20"},
    "immun":   {"pathway": PATHWAY_COLOR, "protein": PROTEIN_COLOR, "drug": "#e65100"},
    "kidney":  {"pathway": PATHWAY_COLOR, "protein": PROTEIN_COLOR, "drug": "#1a237e"},
    "liver":   {"pathway": PATHWAY_COLOR, "protein": PROTEIN_COLOR, "drug": "#004d40"},
    "default": {"pathway": PATHWAY_COLOR, "protein": PROTEIN_COLOR, "drug": "#27ae60"},
}


# ──────────────────────────────────────────────────────────────────────────────
# 1. CSV Parsing
# ──────────────────────────────────────────────────────────────────────────────
def load_proteins(csv_path: Path) -> dict:
    """Return {gene_symbol: {name, desc, hr_str, hr_float, pval_str}} from CSV."""
    proteins = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gene = row["Protein"].strip()
            hr_raw = row["HR[95%CI]"].strip()
            hr_str = hr_raw.split("[")[0].strip()
            try:
                hr_float = float(hr_str)
            except ValueError:
                hr_float = 1.0
            try:
                pval_float = float(row["P_value"].strip())
                pval_str = f"{pval_float:.2e}"
            except ValueError:
                pval_str = row["P_value"].strip()
            proteins[gene] = {
                "name": gene,
                "desc": row.get("Protein_definition", "").strip(),
                "hr_str": hr_raw,
                "hr_val": hr_str,
                "hr_float": hr_float,
                "pval_str": pval_str,
            }
    return proteins


# ──────────────────────────────────────────────────────────────────────────────
# 2. HTML Utilities
# ──────────────────────────────────────────────────────────────────────────────
_TAG_RE   = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

def strip_tags(text: str) -> str:
    return _SPACE_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()

def decode_entities(text: str) -> str:
    return (text.replace("&lt;", "<").replace("&gt;", ">")
                .replace("&amp;", "&").replace("&nbsp;", " ")
                .replace("&#39;", "'").replace("&quot;", '"'))

def clean_text(text: str) -> str:
    return decode_entities(strip_tags(text))

def first_sentence(text: str, max_chars: int = 280) -> str:
    """Return first ~2 sentences of plain text, capped at max_chars."""
    text = clean_text(text)
    # Split on period followed by space/end
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for p in parts:
        candidate = (out + " " + p).strip()
        if len(candidate) > max_chars:
            break
        out = candidate
    return out.strip() or text[:max_chars].strip()


# ──────────────────────────────────────────────────────────────────────────────
# 3. V1 HTML Parsing
# ──────────────────────────────────────────────────────────────────────────────
def read_v1(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()

def extract_intro_stats(html: str) -> tuple[str, int, int, int]:
    """Return (disease_name, n_proteins, n_pathways, n_participants) from intro."""
    intro_match = re.search(
        r"<h2>Introduction</h2>(.*?)(?=<h2>)", html, re.DOTALL | re.IGNORECASE)
    intro = clean_text(intro_match.group(1)) if intro_match else ""

    # Disease name: first sentence often starts with "DiseaseX is..."
    disease_name = "Unknown Disease"
    m = re.match(r"^([^(,]+?)(?:\s*\(Disease code[^)]*\))?\s+(?:is|are)\s+", intro)
    if m:
        disease_name = m.group(1).strip()

    # Extract numeric stats
    def find_int(pattern: str) -> int:
        m = re.search(pattern, intro, re.IGNORECASE)
        return int(m.group(1).replace(",", "")) if m else 0

    n_proteins   = find_int(r"(?:levels of|circulating levels of)\s+(\d+)\s+plasma protein")
    n_pathways   = find_int(r"(\d+)\s+significantly enriched biological pathways")
    n_participants = find_int(r"total\s+([\d,]+)\s+participants")

    return disease_name, n_proteins, n_pathways, n_participants

def extract_intro_paragraphs(html: str) -> list[str]:
    """Return cleaned paragraph text from the v1 Introduction section."""
    intro_match = re.search(
        r"<h2>Introduction</h2>(.*?)(?=<h2>)", html, re.DOTALL | re.IGNORECASE)
    if not intro_match:
        return []

    intro_html = intro_match.group(1)
    paragraphs = []
    for m in re.finditer(r"<p>(.*?)</p>", intro_html, re.DOTALL | re.IGNORECASE):
        text = clean_text(m.group(1))
        if text:
            paragraphs.append(text)

    if paragraphs:
        return paragraphs
    text = clean_text(intro_html)
    return [text] if text else []

def parse_table1(html: str) -> list[dict]:
    """Parse the markdown Table 1 inside a <p> tag."""
    # Find block containing Table 1
    tbl_match = re.search(
        r"Table\s*1[^\n]*\n\|[^\n]+\|[^\n]+\|(.*?)(?=</p>)", html, re.DOTALL | re.IGNORECASE)
    if not tbl_match:
        return []

    rows = []
    for line in tbl_match.group(0).split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        # Skip header and separator rows
        if re.match(r"^-+$", cells[0]) or re.match(r"(?i)term.?id", cells[0]):
            continue
        # cells: TermID | Pathway Name | Count | Score | p-value | Source
        try:
            rows.append({
                "termId":  cells[0].strip(),
                "name":    cells[1].strip(),
                "count":   int(cells[2].strip()),
                "score":   cells[3].strip(),
                "pval":    cells[4].strip(),
                "source":  cells[5].strip() if len(cells) > 5 else "–",
            })
        except (ValueError, IndexError):
            continue
    return rows

def split_pathway_sections(html: str) -> list[dict]:
    """
    Split the HTML by <h3> headings that appear after
    '<h2>Enriched Pathways Analysis</h2>'.
    Returns list of {heading_text, raw_html}.
    """
    analysis_start = re.search(
        r"<h2>Enriched Pathways Analysis</h2>", html, re.IGNORECASE)
    if analysis_start:
        html = html[analysis_start.end():]

    parts = re.split(r"(?=<h3>)", html, flags=re.IGNORECASE)
    sections = []
    for part in parts:
        m = re.match(r"<h3>(.*?)</h3>(.*)", part, re.DOTALL | re.IGNORECASE)
        if m:
            sections.append({"heading": m.group(1).strip(), "body": m.group(2)})
    return sections

def parse_pathway_heading(heading: str) -> tuple[str, str]:
    """Split 'Pathway Name (TermID)' → (name, termId)."""
    m = re.search(r"\(([^)]+)\)\s*$", heading)
    if m:
        return heading[:m.start()].strip(), m.group(1).strip()
    return heading.strip(), ""

def extract_section_image(body: str) -> str:
    """Return first local (non-http) img src from section."""
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', body, re.IGNORECASE):
        src = m.group(1)
        if not src.startswith("http"):
            return src
    return ""

def extract_pubmed_links(body: str) -> list[str]:
    """Return list of unique PubMed PMIDs found in the section body."""
    return list(dict.fromkeys(
        re.findall(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", body)))

def build_reference_lookup(html: str) -> dict[str, dict]:
    """
    Parse reference paragraphs at the bottom of the v1 HTML.
    Pattern: <p><a href="...PMID">N</a> Authors. Title. <em>Journal</em>. Year.</p>
    Returns: {pmid: {num, authors, title, journal, year}}
    """
    ref_dict = {}
    pattern = re.compile(
        r'<p>\s*<a href="[^"]*?(\d+)">\s*(\d+)\s*</a>\s*(.*?)</p>', re.DOTALL)
    for m in pattern.finditer(html):
        pmid, num, body_html = m.group(1), m.group(2), m.group(3)
        # Extract journal (in <em> tag)
        journal_m = re.search(r"<em>(.*?)</em>", body_html)
        journal = clean_text(journal_m.group(1)) if journal_m else ""
        # Strip journal tag from body
        raw = re.sub(r"<em>.*?</em>", "", body_html)
        raw = clean_text(raw).strip(" .")
        # Separate authors (before last ". ") and title
        parts = raw.rsplit(". ", 1)
        title = parts[0].strip() if parts else raw
        # Extract year
        year_m = re.search(r"\b(19|20)\d{2}\b", body_html)
        year = year_m.group(0) if year_m else ""
        ref_dict[pmid] = {"num": num, "title": title,
                          "journal": journal, "year": year}
    return ref_dict

def extract_proteins_from_section(body: str, proteins: dict) -> list[str]:
    """
    Return list of gene names mentioned in section text.
    Searches by:
      1. Gene symbol (word boundary, case-insensitive)
      2. Full protein definition (case-insensitive substring)
      3. First 3 significant words of protein definition (partial match fallback)
    """
    plain = clean_text(body)
    plain_lc = plain.lower()
    found = []
    for gene, info in proteins.items():
        # 1. Gene symbol
        if re.search(r"\b" + re.escape(gene) + r"\b", plain, re.IGNORECASE):
            found.append(gene)
            continue
        # 2. Full definition (case-insensitive)
        desc = info["desc"].strip().lower()
        if len(desc) > 8 and desc in plain_lc:
            found.append(gene)
            continue
        # 3. Partial: first 3+ significant words (skip very short tokens)
        words = [w for w in re.split(r"[\s/,;-]+", desc) if len(w) > 3]
        if len(words) >= 3:
            phrase = " ".join(words[:3])
            if phrase in plain_lc:
                found.append(gene)
    return found

def extract_full_section_text(body: str) -> str:
    """
    Collect all meaningful paragraphs from a pathway section body.
    Skips short paragraphs, 'Building on...' / 'With this...' summaries,
    and paragraphs that are purely PubMed reference lists.
    Returns the concatenated plain text (no character limit).
    """
    parts = []
    for m in re.finditer(r"<p>(.*?)</p>", body, re.DOTALL | re.IGNORECASE):
        text = clean_text(m.group(1))
        lc = text.lower()
        if (len(text) > 150
                and not lc.startswith("building on")
                and not lc.startswith("with this")
                and not re.match(r"^\[?\d+\]", text)          # starts with ref number
                and text.count("pubmed.ncbi") < 3):            # mostly plain text
            parts.append(text)
    return "\n\n".join(parts)


def summarize_context_gpt(pathway_name: str, disease_name: str,
                           full_text: str, max_tokens: int = 220) -> str:
    """
    Use GPT-4o to produce a concise, complete 3-5 sentence summary of
    the pathway's role in the disease context.
    Falls back to the first complete sentence(s) of full_text if the API fails.
    """
    if not full_text.strip():
        return ""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return first_sentence(full_text, 500)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = (
            f"Summarize the following text about the '{pathway_name}' pathway "
            f"in the context of {disease_name} in 3-5 complete, fluent sentences. "
            f"Focus on the biological mechanism and disease relevance. "
            f"Do NOT cut off mid-sentence. Output plain text only.\n\n"
            f"{full_text[:4000]}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"    [GPT summary skipped: {e}]")
        return first_sentence(full_text, 500)


INTRO_REWRITE_PROMPT = """Please rewrite the following long description into a concise, information-rich introduction/overview paragraph for a disease-protein functional enrichment analysis.

Requirements:

1. Organize the paragraph in this order:
   disease background -> protein association results -> rationale -> enrichment analysis method -> main enrichment results -> key biological themes -> overall interpretation -> transition to the following sections.

2. Briefly introduce the disease, including the disease name, disease code, major clinical features, and broad biological alterations if relevant.

3. Summarize the protein association results, including the dataset, number of controls and cases, number of significant proteins, correction method, and significance threshold.

4. Explain why studying these proteins is important for understanding disease mechanisms, heterogeneity, progression, and potential diagnosis or treatment.

5. Describe the functional enrichment analysis and list the pathway databases actually used in the input text.

6. Report the total number of significantly enriched pathways. You may mention 3-5 representative pathways, but avoid listing too many P values or protein counts.

7. Summarize the main biological themes, such as immune signaling, receptor-mediated communication, transcriptional regulation, lipid metabolism, intracellular transport, ER biology, extracellular biology, barrier biology, or gut-brain axis pathways. Only use themes supported by the input text.

8. End with one sentence that naturally introduces the following detailed pathway sections.

Style:
- Formal academic English.
- One paragraph only.
- About 180-260 words.
- Remove redundancy and avoid excessive pathway-by-pathway explanation.
- Keep key numbers, disease code, dataset name, sample size, protein count, database names, and significance threshold.
- If the disease code appears non-standard or ambiguous, add an "Items to verify" note stating that the disease code should use a standard coding system such as ICD-10.
- If pathway counts differ across the input, add an "Items to verify" note about pathway count consistency and use the total pathway count stated in the v1 Introduction text as the primary value (for example, 29 pathways when v1 reports 29), rather than assuming a fixed count.

Text to rewrite:

{text}
"""

def rewrite_intro_gpt(long_text: str, fallback_text: str, max_tokens: int = 360) -> str:
    """
    Rewrite the v1 Introduction into one concise overview paragraph.
    Falls back to a deterministic compact overview when the API is unavailable.
    """
    long_text = clean_text(long_text)
    if not long_text:
        return fallback_text

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return fallback_text
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = INTRO_REWRITE_PROMPT.format(text=long_text[:7000])
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        rewritten = clean_text(resp.choices[0].message.content.strip())
        return rewritten or fallback_text
    except Exception as e:
        print(f"    [GPT intro rewrite skipped: {e}]")
        return fallback_text


def extract_context_paragraph(body: str, max_chars: int = 800) -> str:
    """Legacy single-paragraph extractor (used for the Agent Summary line)."""
    for m in re.finditer(r"<p>(.*?)</p>", body, re.DOTALL | re.IGNORECASE):
        text = clean_text(m.group(1))
        if (len(text) > 200
                and not text.lower().startswith("building on")
                and not text.lower().startswith("with this")
                and "pubmed" not in text.lower()):
            return text[:max_chars].rstrip()
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# 4. Main Parsing Orchestrator
# ──────────────────────────────────────────────────────────────────────────────
def parse_v1(html: str, proteins: dict, top_n: int = 10) -> dict:
    """
    Full parse of v1 HTML.
    Returns a rich dict with all data needed to build v3.
    top_n: maximum number of pathways to include (default 10).
    """
    disease_name, n_prot, n_path, n_part = extract_intro_stats(html)
    intro_paragraphs = extract_intro_paragraphs(html)

    table_rows = parse_table1(html)[:top_n]
    sections   = split_pathway_sections(html)
    ref_lookup = build_reference_lookup(html)
    gene_set   = set(proteins.keys())

    # Match Table1 rows with pathway sections (by termId)
    # Build a map: termId → section data
    section_by_name: dict[str, dict] = {}
    for sec in sections:
        name, tid = parse_pathway_heading(sec["heading"])
        section_by_name[tid] = sec
        section_by_name[name.lower()] = sec  # fallback by name

    pathways = []
    for idx, row in enumerate(table_rows, start=1):
        tid  = row["termId"]
        name = row["name"]

        # Locate matching section
        sec = section_by_name.get(tid) or section_by_name.get(name.lower())
        body = sec["body"] if sec else ""

        # Full section text (no char limit) → GPT-4o summary
        full_text = extract_full_section_text(body)
        context   = summarize_context_gpt(name, disease_name, full_text)

        # Agent summary: first 1-2 sentences of the GPT context
        # (falls back to legacy extractor if GPT returned nothing)
        if not context:
            context = extract_context_paragraph(body)
        summary = first_sentence(context, 260)

        # Image
        img_src = extract_section_image(body)

        # Proteins mentioned in this section
        mentioned_proteins = extract_proteins_from_section(body, proteins)

        # PubMed refs
        pmids = extract_pubmed_links(body)
        refs  = []
        for pmid in pmids:
            info = ref_lookup.get(pmid)
            if info:
                refs.append(
                    f'[{info["num"]}] {info["title"]}. '
                    f'<em>{info["journal"]}</em>. {info["year"]}. '
                    f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}" '
                    f'target="_blank">PubMed</a>'
                )
            else:
                refs.append(
                    f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}" '
                    f'target="_blank">PubMed:{pmid}</a>'
                )

        pathways.append({
            "id":       f"P{idx}",
            "termId":   tid,
            "name":     name,
            "count":    row["count"],
            "score":    row["score"],
            "pval":     row["pval"],
            "source":   row["source"],
            "context":  context,
            "summary":  summary,
            "img_src":  img_src,
            "proteins": mentioned_proteins,
            "pmids":    pmids,
            "refs":     refs,
        })

    # ── Literature-based ranking for proteins ────────────────────────────────
    # For each gene, count unique PMIDs across all pathway sections that
    # mention that gene. This serves as a literature-evidence score.
    gene_pmids: dict[str, set[str]] = defaultdict(set)
    gene_pathways: dict[str, set[str]] = defaultdict(set)
    for pw in pathways:
        for gene in pw["proteins"]:
            gene_pmids[gene].update(pw["pmids"])
            gene_pathways[gene].add(pw["id"])

    for gene, info in proteins.items():
        info["lit_pmids"]    = sorted(gene_pmids.get(gene, set()))
        info["lit_count"]    = len(info["lit_pmids"])
        info["pathway_ids"]  = sorted(gene_pathways.get(gene, set()))
        info["pathway_hits"] = len(info["pathway_ids"])

    # Build gene→reference snippets lookup (for protein detail panel)
    for gene, info in proteins.items():
        info["lit_refs"] = []
        for pmid in info["lit_pmids"]:
            r = ref_lookup.get(pmid)
            if r:
                info["lit_refs"].append({
                    "pmid":    pmid,
                    "num":     r.get("num", ""),
                    "title":   r.get("title", ""),
                    "journal": r.get("journal", ""),
                    "year":    r.get("year", ""),
                })
            else:
                info["lit_refs"].append({"pmid": pmid, "num": "", "title": "",
                                          "journal": "", "year": ""})

    return {
        "disease_name":    disease_name,
        "n_proteins":      n_prot or len(proteins),
        "n_pathways":      n_path,
        "n_participants":  n_part,
        "intro_paragraphs": intro_paragraphs,
        "pathways":        pathways,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4.5 External Knowledge Fetchers (STRING-DB PPI · DGIdb Pharmacogenetics)
# ──────────────────────────────────────────────────────────────────────────────
CACHE_DIR = BASE_DIR / "src" / ".cache_v3"


def _ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _cached_json(key: str, fetcher):
    """Run `fetcher()` and persist the result under CACHE_DIR/<key>.json.
    Returns the parsed result, or [] on failure."""
    _ensure_cache_dir()
    safe_key = re.sub(r"[^A-Za-z0-9_\-]", "_", key)[:160]
    cache_path = CACHE_DIR / f"{safe_key}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            pass
    try:
        result = fetcher()
    except Exception as e:
        print(f"    [fetch failed for {key}: {e}]")
        return []
    if result is not None:
        try:
            cache_path.write_text(json.dumps(result))
        except Exception:
            pass
    return result if result is not None else []


def fetch_string_ppi(genes: list[str], score_threshold: float = 0.4,
                     max_edges: int = 60) -> list[tuple[str, str, float]]:
    """Fetch STRING-DB protein-protein interactions among `genes`.
    Returns list of (geneA, geneB, score) where both endpoints are in `genes`."""
    genes = sorted({g for g in genes if g})
    if len(genes) < 2:
        return []
    gene_set_uc = {g.upper() for g in genes}
    cache_key = "string_ppi_" + "_".join(genes)

    def _fetch():
        ids = "%0d".join(urllib.parse.quote(g) for g in genes)
        url = (f"https://string-db.org/api/json/network?identifiers={ids}"
               f"&species=9606&required_score={int(score_threshold*1000)}")
        req = urllib.request.Request(url, headers={"User-Agent": "BioInsight/3"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))

    rows = _cached_json(cache_key, _fetch) or []
    edges, seen = [], set()
    for row in rows:
        a = (row.get("preferredName_A") or "").upper()
        b = (row.get("preferredName_B") or "").upper()
        try:
            score = float(row.get("score", 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        if not (a and b) or a == b:
            continue
        if a not in gene_set_uc or b not in gene_set_uc:
            continue
        if score < score_threshold:
            continue
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        edges.append((a, b, score))
    edges.sort(key=lambda x: -x[2])
    return edges[:max_edges]


def fetch_pharmaco_drugs(gene: str, max_drugs: int = 2) -> list[dict]:
    """Fetch pharmacogenetic drug interactions for `gene` from DGIdb (GraphQL).
    Returns [{name, score, approved}] sorted by approval+score (top-N)."""
    if not gene:
        return []
    cache_key = f"dgidb_{gene}"

    def _fetch():
        query = (
            "query($name: String!) {"
            "  genes(names: [$name]) {"
            "    nodes { interactions {"
            "      drug { name approved }"
            "      interactionScore"
            "    } }"
            "  }"
            "}"
        )
        payload = json.dumps({"query": query, "variables": {"name": gene}}).encode("utf-8")
        req = urllib.request.Request(
            "https://dgidb.org/api/graphql",
            data=payload,
            headers={"Content-Type": "application/json",
                     "User-Agent": "BioInsight/3"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    result = _cached_json(cache_key, _fetch) or {}
    nodes = ((result.get("data") or {}).get("genes") or {}).get("nodes") or []
    if not nodes:
        return []
    interactions = nodes[0].get("interactions") or []
    drugs = []
    for it in interactions:
        drug = it.get("drug") or {}
        name = (drug.get("name") or "").strip()
        if not name:
            continue
        try:
            score = float(it.get("interactionScore") or 0)
        except (TypeError, ValueError):
            score = 0.0
        drugs.append({"name": name.title(),
                      "score": score,
                      "approved": bool(drug.get("approved"))})
    # Prefer FDA-approved drugs, then by interaction score
    drugs.sort(key=lambda d: (-(1 if d["approved"] else 0), -d["score"]))
    seen, out = set(), []
    for d in drugs:
        key = d["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
        if len(out) >= max_drugs:
            break
    return out


# ──────────────────────────────────────────────────────────────────────────────
# 5. Network Element Builder
# ──────────────────────────────────────────────────────────────────────────────
def classify_drug(protein_info: dict) -> str:
    desc_lower = protein_info["desc"].lower()
    for drug_label, keywords in DRUG_KEYWORDS.items():
        if drug_label == "Targeted Therapy":
            continue
        if any(kw in desc_lower for kw in keywords):
            return drug_label
    return "Targeted Therapy"

def _js_str(s: str) -> str:
    """Escape a Python string for embedding in a JS single-quoted literal."""
    return (s.replace("\\", "\\\\")
             .replace("'", "\\'")
             .replace("\n", " ")
             .replace("\r", " "))


def build_elements(pathways: list[dict], proteins: dict, *,
                   enable_ppi: bool = True,
                   enable_pharmaco: bool = True,
                   max_pharmaco_genes: int = 8) -> tuple[list, list, list, list]:
    """
    Build Cytoscape elements: (pathway_nodes, protein_nodes, drug_nodes, edges).

    Edge `relation` labels are added on every edge:
      * gene → pathway        : "belongs to"
      * gene ↔ gene (STRING)  : "PPI"
      * gene → category drug  : "category"
      * gene → pharmaco drug  : "pharmacogenetic"
    """
    pathway_nodes: list[str] = []
    protein_nodes: list[str] = []
    drug_nodes:    list[str] = []
    edges:         list[str] = []

    # Collect all proteins that appear in at least one pathway
    used_proteins: set = set()
    for pw in pathways:
        used_proteins.update(p for p in pw["proteins"] if p in proteins)

    # If no proteins matched via text, fall back to ALL csv proteins
    if not used_proteins:
        used_proteins = set(proteins.keys())

    # ── Pathway nodes ──
    for pw in pathways:
        ctx_escaped = _js_str(pw["context"])
        name_escaped = _js_str(pw["name"])
        pathway_nodes.append(
            f"{{ data: {{ id: '{pw['id']}', type: 'pathway', "
            f"termId: '{pw['termId']}', name: '{name_escaped}', "
            f"count: {pw['count']}, score: '{pw['score']}', pval: '{pw['pval']}', "
            f"source: '{pw['source']}', "
            f"context: '{ctx_escaped}' }} }}"
        )

    # ── Protein nodes (rank by literature evidence) ──
    # Tie-break order: lit_count → pathway_hits → |HR − 1|
    def _rank_key(g: str):
        info = proteins.get(g, {})
        return (-(info.get("lit_count") or 0),
                -(info.get("pathway_hits") or 0),
                -abs((info.get("hr_float") or 1.0) - 1.0))

    sorted_genes = sorted(used_proteins, key=_rank_key)
    for rank, gene in enumerate(sorted_genes, start=1):
        p = proteins[gene]
        desc_esc = _js_str(p["desc"])
        lit_count   = int(p.get("lit_count") or 0)
        path_hits   = int(p.get("pathway_hits") or 0)
        protein_nodes.append(
            f"{{ data: {{ id: '{gene}', name: '{gene}', type: 'protein', "
            f"hr: '{p['hr_val']}', pval: '{p['pval_str']}', "
            f"desc: '{desc_esc}', litCount: {lit_count}, pathwayHits: {path_hits}, "
            f"litRank: {rank} }} }}"
        )

    # ── Gene → Pathway edges (relation: "belongs to") ──
    pathway_edge_seen: set = set()
    for pw in pathways:
        for gene in pw["proteins"]:
            if gene in used_proteins:
                key = (gene, pw["id"])
                if key in pathway_edge_seen:
                    continue
                pathway_edge_seen.add(key)
                edges.append(
                    f"{{ data: {{ source: '{gene}', target: '{pw['id']}', "
                    f"relation: 'belongs to', edge_type: 'pathway' }} }}"
                )

    # ── Drug-category nodes (existing keyword-based classification) ──
    drug_map: dict[str, list[str]] = defaultdict(list)
    top_for_category = sorted(
        [g for g in used_proteins if g in proteins],
        key=lambda g: abs(proteins[g]["hr_float"] - 1.0), reverse=True
    )[:8]
    for gene in top_for_category:
        drug_map[classify_drug(proteins[gene])].append(gene)

    used_drug_labels = list(dict.fromkeys(
        classify_drug(proteins[g]) for g in top_for_category if g in proteins))
    drug_idx = 1
    for label in used_drug_labels[:4]:  # cap at 4 category nodes
        did = f"D{drug_idx}"
        drug_nodes.append(
            f"{{ data: {{ id: '{did}', name: '{_js_str(label)}', "
            f"type: 'drug', subtype: 'category' }} }}"
        )
        for gene in drug_map[label]:
            edges.append(
                f"{{ data: {{ source: '{gene}', target: '{did}', "
                f"relation: 'category', edge_type: 'drug_cat' }} }}"
            )
        drug_idx += 1

    # ── Pharmacogenetic specific drugs (DGIdb) ──
    if enable_pharmaco:
        # Prefer the genes with strongest literature evidence (then HR)
        pharmaco_candidates = sorted(
            [g for g in used_proteins if g in proteins],
            key=_rank_key
        )[:max_pharmaco_genes]

        pharmaco_id_by_name: dict[str, str] = {}
        pharmaco_idx = 1
        for gene in pharmaco_candidates:
            try:
                drugs = fetch_pharmaco_drugs(gene, max_drugs=2)
            except Exception as e:
                print(f"    [pharmaco fetch failed for {gene}: {e}]")
                drugs = []
            for d in drugs:
                dname = d["name"]
                key = dname.lower()
                if key not in pharmaco_id_by_name:
                    pdid = f"PD{pharmaco_idx}"
                    pharmaco_id_by_name[key] = pdid
                    pharmaco_idx += 1
                    approved = "true" if d.get("approved") else "false"
                    drug_nodes.append(
                        f"{{ data: {{ id: '{pdid}', name: '{_js_str(dname)}', "
                        f"type: 'drug', subtype: 'pharmaco', "
                        f"approved: {approved}, "
                        f"score: {float(d.get('score') or 0):.2f} }} }}"
                    )
                pdid = pharmaco_id_by_name[key]
                edges.append(
                    f"{{ data: {{ source: '{gene}', target: '{pdid}', "
                    f"relation: 'pharmacogenetic', edge_type: 'pharmaco' }} }}"
                )

    # ── STRING-DB gene-gene functional interactions (PPI) ──
    if enable_ppi:
        # When there are many proteins, limit to the top genes by literature
        # evidence to keep the STRING query URL reasonable.
        ppi_pool = sorted(used_proteins, key=_rank_key)[:80]
        try:
            ppi = fetch_string_ppi(sorted(ppi_pool))
        except Exception as e:
            print(f"    [STRING PPI fetch failed: {e}]")
            ppi = []
        # Map STRING's uppercase names back to the original symbols used as node IDs
        gene_uc_map = {g.upper(): g for g in used_proteins}
        ppi_seen = set()
        for a, b, score in ppi:
            ga = gene_uc_map.get(a)
            gb = gene_uc_map.get(b)
            if not ga or not gb or ga == gb:
                continue
            key = tuple(sorted((ga, gb)))
            if key in ppi_seen:
                continue
            ppi_seen.add(key)
            edges.append(
                f"{{ data: {{ source: '{ga}', target: '{gb}', "
                f"relation: 'STRING PPI', edge_type: 'ppi', "
                f"score: {score:.2f} }} }}"
            )

    return pathway_nodes, protein_nodes, drug_nodes, edges


# ──────────────────────────────────────────────────────────────────────────────
# 6. Color Scheme Selector
# ──────────────────────────────────────────────────────────────────────────────
def pick_colors(disease_name: str) -> dict:
    name_lc = disease_name.lower()
    if any(k in name_lc for k in ["atrial", "heart", "cardiac", "arrhythmia",
                                   "fibrillation", "flutter", "coronary"]):
        return DISEASE_COLORS["cardiac"]
    if any(k in name_lc for k in ["alzheimer", "parkinson", "depression",
                                   "neuro", "stroke", "dementia"]):
        return DISEASE_COLORS["neuro"]
    if any(k in name_lc for k in ["arthritis", "rheumat", "lupus", "immun"]):
        return DISEASE_COLORS["immun"]
    if any(k in name_lc for k in ["kidney", "renal", "nephro"]):
        return DISEASE_COLORS["kidney"]
    if any(k in name_lc for k in ["liver", "hepat", "cirrhosis", "fibrosis"]):
        return DISEASE_COLORS["liver"]
    return DISEASE_COLORS["default"]


# ──────────────────────────────────────────────────────────────────────────────
# 7. Narrative Report HTML Builder
# ──────────────────────────────────────────────────────────────────────────────
def _esc(s: str) -> str:
    """Escape for HTML attribute / JS string contexts."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_pathway_sections_html(pathways: list, proteins: dict) -> str:
    blocks = []
    for i, pw in enumerate(pathways, 1):
        name_esc = html_mod.escape(pw["name"])
        term_id  = pw["termId"]

        # Build entity-link spans for proteins found in this pathway
        top_prots = pw["proteins"][:3]  # highlight first 3 in summary
        protein_links = "".join(
            f'<span class="entity-link" onclick="highlightNode(\'{g}\')">{g}</span>'
            + (", " if j < len(top_prots) - 1 else "")
            for j, g in enumerate(top_prots)
        ) if top_prots else ""

        summary = pw["summary"] or f"This pathway is involved in {name_esc} and is enriched in this disease context."
        summary_html = html_mod.escape(summary)
        if protein_links:
            summary_html += f" Key proteins: {protein_links}."

        img_html = ""
        if pw["img_src"]:
            img_html = f'\n                            <img src="{pw["img_src"]}" alt="PPI Network" class="local-img">'

        context_plain = pw["context"] or summary
        context_html = html_mod.escape(context_plain)

        blocks.append(f"""
                    <h3>{i}. {name_esc} ({term_id})</h3>
                    <div class="summary-box">
                        <strong>Agent Summary:</strong> {summary_html}
                    </div>
                    <details>
                        <summary>Read Context ▽</summary>
                        <div class="details-content">
                            <p>{context_html}</p>{img_html}
                        </div>
                    </details>""")
    return "\n".join(blocks)

def build_pathway_refs_js(pathways: list) -> str:
    lines = []
    for pw in pathways:
        items = ",\n                ".join(f"`{r}`" for r in pw["refs"])
        if not items:
            items = "`No references extracted.`"
        lines.append(f"            {pw['id']}: [\n                {items}\n            ]")
    return ",\n".join(lines)

def summarize_functional_landscape(pathways: list) -> str:
    """Create a compact functional synthesis from enriched pathway names."""
    text = " ".join(
        f"{pw.get('name', '')} {pw.get('source', '')} {pw.get('summary', '')}"
        for pw in pathways
    ).lower()
    categories = [
        ("synaptic and neuronal communication",
         ["synap", "neuron", "axon", "neurotrans", "vesicle"]),
        ("immune and inflammatory regulation",
         ["immune", "inflam", "cytokine", "complement", "interleukin"]),
        ("receptor-mediated communication",
         ["receptor", "ligand", "signaling", "signal"]),
        ("lipid metabolism and lipoprotein receptor biology",
         ["lipid", "lipoprotein", "cholesterol", "apolipoprotein"]),
        ("secretory, vesicle trafficking, and intracellular transport processes",
         ["vesicle", "secret", "traffick", "transport", "endocyt"]),
        ("cytoskeletal, extracellular, and compartment-level organization",
         ["filament", "cytoskeleton", "extracellular", "cellular component", "axon"]),
        ("stress-responsive transcriptional and cellular regulation",
         ["stress", "transcription", "differentiation", "lineage", "regulation"]),
        ("gut-associated epithelial and host interaction pathways",
         ["gut", "epithelial", "host", "microbial", "infection"]),
    ]
    matched = [
        label for label, keywords in categories
        if any(keyword in text for keyword in keywords)
    ]
    if not matched:
        matched = [
            "receptor-mediated signaling",
            "immune and inflammatory regulation",
            "intracellular transport",
            "cellular compartment biology",
        ]
    return (
        "These results reveal a strongly interconnected molecular landscape "
        f"dominated by {', '.join(matched[:-1])}, and {matched[-1]}."
        if len(matched) > 1
        else f"These results reveal a focused molecular landscape dominated by {matched[0]}."
    )

def build_overview_html(
    disease_name: str,
    n_proteins: int,
    n_pathways: int,
    pathways: list,
    intro_paragraphs: list[str] | None,
) -> str:
    """Render a concise Introduction rewritten from the v1 report."""
    source_intro = " ".join(p for p in (intro_paragraphs or []) if p)
    pathway_count = n_pathways or len(pathways)
    representative = ", ".join(pw["name"] for pw in pathways[:5])
    source_lc = source_intro.lower()
    database_candidates = [
        ("Gene Ontology Molecular Function", ["gene ontology molecular function", "go:mf"]),
        ("Gene Ontology Biological Process", ["gene ontology biological process", "go:bp"]),
        ("Gene Ontology Cellular Component", ["gene ontology cellular component", "go:cc"]),
        ("Reactome", ["reactome", "reac"]),
        ("KEGG", ["kyoto encyclopedia of genes and genomes", "kegg"]),
        ("WikiPathways", ["wikipathways", "wp"]),
    ]
    databases = [
        label for label, keys in database_candidates
        if any(key in source_lc for key in keys)
    ]
    if not databases:
        source_codes = " ".join(pw.get("source", "") for pw in pathways).lower()
        databases = [
            label for label, keys in database_candidates
            if any(key in source_codes for key in keys)
        ]
    database_names = ", ".join(databases)

    fallback_parts = []
    if source_intro:
        fallback_parts.append(first_sentence(source_intro, 520))
    else:
        fallback_parts.append(
            f"{disease_name} is a complex disease analyzed through UK Biobank "
            f"proteomics, with {n_proteins} significant plasma proteins identified."
        )
    fallback_parts.append(
        "Studying these proteins can clarify disease mechanisms, biological "
        "heterogeneity, progression, and potential diagnostic or therapeutic targets."
    )
    fallback_parts.append(
        "Functional enrichment analysis was performed across "
        f"{database_names or 'GO, Reactome, KEGG, and related pathway resources'}, "
        f"identifying {pathway_count} significantly enriched pathways (Table 1)"
        f"{', including ' + representative if representative else ''}."
    )
    fallback_parts.append(summarize_functional_landscape(pathways))
    fallback_parts.append(
        "Together, these enrichments provide a systems-level view of how circulating "
        "protein associations may converge on coherent molecular programs rather "
        "than isolated biomarkers."
    )
    fallback_parts.append(
        "The following sections examine the most prominent enriched pathways and "
        "their molecular interactions in greater detail."
    )
    fallback_text = " ".join(p for p in fallback_parts if p)

    overview = rewrite_intro_gpt(source_intro, fallback_text)
    verify_match = re.search(r"\bItems to verify\s*:\s*", overview, re.IGNORECASE)
    if verify_match:
        paragraph = overview[:verify_match.start()].strip()
        note = overview[verify_match.start():].strip()
        # 将正则表达式及其处理提取到外部
        pattern = r'(?i)^Items to verify\s*:\s*'
        cleaned_note = re.sub(pattern, '', note)
        escaped_note = html_mod.escape(cleaned_note)

        return (
            f"<p>{html_mod.escape(paragraph)}</p>\n"
            # f'<p style="font-size:12px;color:#666;"><strong>Items to verify:</strong> '
            # f"{escaped_note}</p>"
        )
    return f"<p>{html_mod.escape(overview)}</p>"


# ──────────────────────────────────────────────────────────────────────────────
# 8. Full V3 HTML Generator
# ──────────────────────────────────────────────────────────────────────────────
def generate_v3_html(
    disease_name: str,
    n_proteins: int,
    n_pathways: int,
    intro_paragraphs: list[str] | None,
    pathways: list,
    proteins: dict,
    pathway_nodes: list,
    protein_nodes: list,
    drug_nodes: list,
    edges: list,
    colors: dict,
) -> str:
    pathway_html   = build_pathway_sections_html(pathways, proteins)
    refs_js        = build_pathway_refs_js(pathways)

    n_displayed    = len(proteins)
    spacing        = "1.0" if n_displayed > 15 else "1.2"

    # ── Per-gene literature references (shown in protein detail panel) ──
    gene_lit_js: dict[str, list[dict]] = {}
    for gene, info in proteins.items():
        gene_lit_js[gene] = info.get("lit_refs", [])
    gene_lit_json = json.dumps(gene_lit_js, ensure_ascii=False)

    # ── Literature-evidence ranking (full list, rendered client-side) ──
    # The full ordered list is exposed to JS so the user can drag a slider
    # to expand the display from the default top-N up to ALL CSV proteins.
    lit_ranked = sorted(
        proteins.items(),
        key=lambda kv: (-(kv[1].get("lit_count") or 0),
                        -(kv[1].get("pathway_hits") or 0),
                        -abs((kv[1].get("hr_float") or 1.0) - 1.0))
    )
    lit_rank_data = []
    for rank, (gene, info) in enumerate(lit_ranked, start=1):
        lit_rank_data.append({
            "rank":         rank,
            "gene":         gene,
            "lit_count":    int(info.get("lit_count") or 0),
            "pathway_hits": int(info.get("pathway_hits") or 0),
            "hr_val":       info["hr_val"],
        })
    # Default display count: keep the original behavior (top 5 plus any
    # additional genes that still have >=1 paper of literature evidence).
    lit_default_n = 0
    for item in lit_rank_data:
        if item["lit_count"] <= 0 and item["rank"] > 5:
            break
        lit_default_n = item["rank"]
    if lit_default_n == 0:
        lit_default_n = min(5, len(lit_rank_data))
    lit_total_n   = len(lit_rank_data)
    lit_rank_json = json.dumps(lit_rank_data, ensure_ascii=False)

    if lit_total_n == 0:
        lit_top_html = ('<em style="color:#999">'
                        'No literature evidence extracted from v1.</em>')
    else:
        slider_disabled = "" if lit_total_n > 1 else "disabled"
        lit_top_html = (
            '<div class="lit-rank-controls">'
            '<label class="lit-rank-label">Show top '
            f'<strong id="lit-rank-num">{lit_default_n}</strong> '
            f'of <span id="lit-rank-total">{lit_total_n}</span> proteins'
            '</label>'
            f'<input type="range" id="lit-rank-slider" class="lit-rank-slider" '
            f'min="1" max="{lit_total_n}" value="{lit_default_n}" '
            f'step="1" {slider_disabled}>'
            '<span class="lit-rank-quick">'
            f'<button class="toolbar-btn" type="button" '
            f'onclick="setLitRank({lit_default_n})">Default</button>'
            f'<button class="toolbar-btn" type="button" '
            f'onclick="setLitRank({lit_total_n})">All</button>'
            '</span></div>'
            '<ol class="lit-rank-list" id="lit-rank-list"></ol>'
        )

    # JS elements array
    all_elements = (
        ["            // Pathways"] + pathway_nodes +
        ["            // Proteins"] + protein_nodes +
        ["            // Drugs"]    + drug_nodes +
        ["            // Edges"]    + edges
    )
    elements_js = ",\n            ".join(
        e for e in all_elements if not e.startswith("//")
    )

    # Protein detail renderer JS
    protein_detail_cases = []
    for gene, p in sorted(proteins.items(),
                           key=lambda x: abs(x[1]["hr_float"] - 1.0), reverse=True):
        tier = ("High" if abs(p["hr_float"] - 1.0) > 1.5
                else "Medium" if abs(p["hr_float"] - 1.0) > 0.5
                else "Exploratory")
        note = (f"HR={p['hr_val']} and P={p['pval_str']} support an association "
                f"with {disease_name}. {p['desc']} - potential translational relevance.")
        drug_label = classify_drug(p)
        protein_detail_cases.append(
            f"        if(data.name === '{gene}') {{ "
            f"tier='Targetability: {tier}'; "
            f"note=\"Repurposing Agent Note: {note.replace(chr(34), chr(39))}\"; "
            f"drugsHTML='<li>Category: {drug_label}</li>'; }}"
        )
    protein_detail_js = "\n".join(protein_detail_cases)

    overview_html = build_overview_html(
        disease_name, n_proteins, n_pathways, pathways, intro_paragraphs)

    first_gene_link = next(iter(proteins), "")
    first_gene_html = (f'(<span class="entity-link" onclick="highlightNode(\'{first_gene_link}\')">'
                       f'{first_gene_link}</span>)') if first_gene_link else ""

    # Disease name short
    disease_short = disease_name.split(",")[0].strip()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioInsight Multi-Agent System - {html_mod.escape(disease_short)}</title>
    <link rel="preconnect" href="https://rsms.me/">
    <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
    <!-- fcose: modern force-directed layout, much better separation than cola for biology graphs. -->
    <script src="https://unpkg.com/layout-base@2.0.1/layout-base.js"></script>
    <script src="https://unpkg.com/cose-base@2.2.0/cose-base.js"></script>
    <script src="https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js"></script>
    <style>
        :root {{
            --primary-bg: #f8f9fa;
            --panel-bg: #ffffff;
            --header-bg: #1a2530;
            --text-main: #2c3e50;
            --text-muted: #6c757d;
            --border-color: #dee2e6;
            --color-pathway: {colors['pathway']};
            --color-protein: {colors['protein']};
            --color-drug: {colors['drug']};
        }}
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            background-color: var(--primary-bg);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        header {{
            background-color: var(--header-bg);
            color: white;
            padding: 0 20px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            z-index: 10;
        }}
        .logo {{ font-weight: 600; font-size: 16px; letter-spacing: 0.5px; }}
        .demo-selector {{ background: #2c3e50; color: white; border: 1px solid #4a5c6e;
                          padding: 4px 12px; border-radius: 4px; }}
        main {{ display: flex; flex: 1; height: calc(100vh - 50px); }}
        .left-pane {{ flex: 4; display: flex; flex-direction: column;
                     border-right: 1px solid var(--border-color); background: var(--panel-bg); }}
        .stats-bar {{ padding: 12px 20px; border-bottom: 1px solid var(--border-color);
                     background: #fdfdfd; font-size: 14px; display: flex; gap: 20px; }}
        .stats-item {{ font-weight: 500; }}
        .stats-item span {{ color: var(--color-protein); font-weight: bold; }}
        .stats-item.pathway span {{ color: var(--color-pathway); }}
        #cy-container {{ flex: 1; position: relative; display: flex; flex-direction: column; overflow: hidden; }}
        #cy {{
            flex: 1; min-height: 0; width: 100%;
            background-color: #fafbfd;
            background-image:
                radial-gradient(circle at 1px 1px, rgba(15,23,42,0.05) 1px, transparent 0);
            background-size: 24px 24px;
        }}
        .graph-toolbar {{ display: flex; flex-direction: column; gap: 0;
                         background: rgba(255,255,255,0.97); border-bottom: 1px solid var(--border-color);
                         z-index: 5; flex-shrink: 0; }}
        .toolbar-row {{ display: flex; align-items: center; gap: 8px; padding: 7px 14px; flex-wrap: wrap; }}
        .toolbar-row-legend {{ display: flex; align-items: center; gap: 14px; padding: 5px 14px 8px;
                              flex-wrap: wrap; border-top: 1px solid #f0f0f0; background: #fafbfc; }}
        .cy-hint {{ padding: 5px 14px; font-size: 11px; color: #999; text-align: center;
                   background: #fafbfc; border-top: 1px solid var(--border-color);
                   letter-spacing: 0.2px; flex-shrink: 0; }}
        .toolbar-btn {{ padding: 4px 10px; border: 1px solid #bbb; border-radius: 4px;
                       background: white; cursor: pointer; font-size: 12px; color: #444;
                       transition: all 0.15s; user-select: none; }}
        .toolbar-btn:hover {{ background: #f0f4ff; border-color: var(--color-pathway); color: var(--color-pathway); }}
        .toolbar-sep {{ width: 1px; height: 18px; background: #ddd; margin: 0 4px; flex-shrink: 0; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 12px; color: #555; white-space: nowrap; }}
        .legend-dot {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; flex-shrink: 0; }}
        .legend-hex {{ width: 13px; height: 13px; display: inline-block; flex-shrink: 0;
                      clip-path: polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%); }}
        .legend-rect {{ width: 16px; height: 9px; border-radius: 2px; display: inline-block; flex-shrink: 0; }}
        .legend-line {{ width: 18px; height: 2px; display: inline-block; flex-shrink: 0; }}
        .legend-line-solid {{ background: #5a6a7a; }}
        .legend-line-dashed {{ background: transparent;
                              background-image: linear-gradient(to right, #90a4ae 50%, transparent 50%);
                              background-size: 6px 2px; background-repeat: repeat-x; }}
        .toggle-btn {{ background: #eef2f6; }}
        .toggle-btn.active {{ background: #1a2530; color: white; border-color: #1a2530; }}
        .toggle-btn:not(.active) {{ opacity: 0.6; }}
        #cy-tooltip {{ position: absolute; background: rgba(25,35,45,0.92); color: #f0f0f0;
                      padding: 8px 12px; border-radius: 6px; font-size: 12px; pointer-events: none;
                      max-width: 220px; z-index: 999; display: none; line-height: 1.5;
                      box-shadow: 0 3px 10px rgba(0,0,0,0.35); }}
        .right-pane {{ flex: 6; display: flex; flex-direction: column; background: var(--panel-bg); }}
        .tabs {{ display: flex; border-bottom: 1px solid var(--border-color); background: #f4f6f8; }}
        .tab-btn {{ flex: 1; padding: 12px; border: none; background: transparent;
                   font-size: 14px; font-weight: 600; color: var(--text-muted); cursor: pointer; outline: none; }}
        .tab-btn.active {{ color: var(--color-pathway); border-bottom: 2px solid var(--color-pathway);
                          background: white; }}
        .content-area {{ flex: 1; overflow-y: auto; padding: 24px; line-height: 1.6; }}
        .panel {{ display: none; }}
        .panel.active {{ display: block; }}
        h2 {{ font-size: 18px; margin-top: 0; color: #1a2530; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
        h3 {{ font-size: 15px; color: var(--color-pathway); margin-top: 24px; }}
        .summary-box {{ background: #f8fcfc; border-left: 3px solid var(--color-pathway);
                       padding: 12px; border-radius: 0 4px 4px 0; margin-bottom: 16px; font-size: 13.5px; }}
        details {{ margin-bottom: 20px; background: white; border: 1px solid #eee; border-radius: 4px; }}
        summary {{ padding: 10px; font-weight: 600; cursor: pointer; background: #fafafa;
                  font-size: 13px; color: var(--text-muted); }}
        .details-content {{ padding: 15px; font-size: 13px; color: #444; }}
        .local-img {{ max-width: 100%; height: auto; border: 1px solid #eee; margin: 10px 0; }}
        .entity-link {{ color: var(--color-protein); font-weight: 500; cursor: pointer;
                       text-decoration: underline; text-decoration-color: rgba(200,60,40,0.3); }}
        .tier-badge {{ display: inline-block; padding: 4px 8px; border-radius: 12px;
                      font-size: 12px; font-weight: bold; margin-left: 10px; }}
        .badge-protein {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-pathway {{ background: #e3f2fd; color: var(--color-pathway); }}
        .detail-section {{ margin-top: 15px; font-size: 14px; }}
        .detail-section label {{ font-weight: 600; color: #555; display: block;
                                margin-bottom: 5px; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
        .repurposing-note {{ background: #fff3e0; padding: 12px; border-radius: 4px;
                            border-left: 3px solid var(--color-protein); color: #9a3412; font-size: 13px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
                      background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 5px; }}
        .stat-box {{ font-size: 12px; color: #666; }}
        .stat-box strong {{ display: block; color: #333; font-size: 14px; margin-top: 2px; }}
        .academic-text {{ font-size: 13.5px; color: #444; line-height: 1.6; text-align: justify; }}
        .ref-list {{ font-size: 12px; color: #666; padding-left: 20px; }}
        .protein-chip-list {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
        .protein-chip {{ display: inline-block; padding: 3px 9px; border-radius: 12px;
                        font-size: 12px; font-weight: 600; cursor: pointer;
                        background: #f3f4f6; color: #374151; border: 1px solid #9ca3af; }}
        .drug-chip {{ display: inline-block; padding: 3px 9px; border-radius: 4px;
                     font-size: 12px; font-weight: 600; cursor: pointer; margin: 2px;
                     background: #fff3e0; color: #bf360c; border: 1px solid #ff7043; }}
        .drug-chip.fda-approved::after {{ content: '✓'; margin-left: 4px; color: #2e7d32; }}
        .lit-rank-list {{ padding-left: 42px; margin: 4px 0; line-height: 1.9;
                         max-height: 320px; overflow-y: auto; overflow-x: hidden;
                         counter-reset: lit-rank; list-style: none; }}
        .lit-rank-list li {{ margin-bottom: 2px; position: relative;
                            counter-increment: lit-rank; }}
        .lit-rank-list li::before {{ content: counter(lit-rank) "."; position: absolute;
                                    left: -36px; width: 30px; text-align: right;
                                    color: #999; font-size: 11px; font-weight: 600;
                                    font-variant-numeric: tabular-nums;
                                    line-height: 1.9; }}
        .lit-rank-controls {{ display: flex; align-items: center; gap: 12px;
                             flex-wrap: wrap; padding: 4px 0 10px;
                             border-bottom: 1px dashed #ffe082; margin-bottom: 8px; }}
        .lit-rank-label {{ font-size: 13px; color: #555; white-space: nowrap; }}
        .lit-rank-label strong {{ color: #bf360c; font-size: 14px; padding: 0 3px; }}
        .lit-rank-slider {{ flex: 1; min-width: 140px; max-width: 260px;
                           accent-color: #fb8c00; cursor: pointer; }}
        .lit-rank-slider:disabled {{ opacity: 0.4; cursor: not-allowed; }}
        .lit-rank-quick {{ display: inline-flex; gap: 6px; }}
        .lit-link {{ color: #1565c0; text-decoration: none; }}
        .lit-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>

    <header>
        <div class="logo">BioInsight Multi-Agent System</div>
        <select class="demo-selector">
            <option>{html_mod.escape(disease_short)}</option>
        </select>
    </header>

    <main>
        <div class="left-pane">
            <div class="stats-bar">
                <div class="stats-item">Disease: <strong>{html_mod.escape(disease_short)}</strong></div>
                <div class="stats-item pathway">Pathways: <span>{n_pathways}</span> Enriched (Top {len(pathways)} Displayed)</div>
                <div class="stats-item">Proteins: <span>{n_proteins}</span> Significant ({n_displayed} Displayed)</div>
            </div>
            <div id="cy-container">
                <div class="graph-toolbar">
                    <div class="toolbar-row">
                        <button class="toolbar-btn" title="Zoom In" onclick="cy.animate({{zoom:cy.zoom()*1.35,center:{{eles:cy.elements()}}}},{{duration:200}})">＋</button>
                        <button class="toolbar-btn" title="Zoom Out" onclick="cy.animate({{zoom:cy.zoom()/1.35,center:{{eles:cy.elements()}}}},{{duration:200}})">－</button>
                        <button class="toolbar-btn" title="Fit all nodes" onclick="cy.animate({{fit:{{eles:cy.elements(),padding:20}}}},{{duration:300}})">⊡ Fit</button>
                        <button class="toolbar-btn" title="Re-run physics layout" onclick="resetLayout()">⟳ Reset</button>
                        <span class="toolbar-sep"></span>
                        <button class="toolbar-btn toggle-btn active" id="tg-ppi"      onclick="toggleEdgeType('ppi', this)">PPI</button>
                        <button class="toolbar-btn toggle-btn active" id="tg-pathway"  onclick="toggleEdgeType('pathway', this)">Pathway</button>
                        <button class="toolbar-btn toggle-btn active" id="tg-pharmaco" onclick="toggleEdgeType('pharmaco', this)">Pharmaco</button>
                        <button class="toolbar-btn toggle-btn active" id="tg-drug-cat" onclick="toggleEdgeType('drug_cat', this)">Drug Cat.</button>
                        <button class="toolbar-btn toggle-btn" id="tg-edge-labels" onclick="toggleEdgeLabels(this)">Labels</button>
                    </div>
                    <div class="toolbar-row-legend">
                        <div class="legend-item">
                            <span class="legend-hex" style="background:var(--color-pathway)"></span>Pathway
                        </div>
                        <div class="legend-item">
                            <span class="legend-dot" style="background:var(--color-protein)"></span>Protein / Gene
                        </div>
                        <div class="legend-item">
                            <span class="legend-rect" style="border:2px solid var(--color-drug);background:#fff"></span>Drug · Category
                        </div>
                        <div class="legend-item">
                            <span class="legend-rect" style="border:1.5px solid #ff7043;background:#fff3e0"></span>Drug · Pharmaco
                        </div>
                        <div class="legend-item">
                            <span class="legend-line legend-line-solid" style="background:var(--color-pathway)"></span>belongs to
                        </div>
                        <div class="legend-item">
                            <span class="legend-line legend-line-dashed"></span>STRING PPI
                        </div>
                        <div class="legend-item">
                            <span class="legend-line legend-line-solid" style="background:#ff7043"></span>pharmacogenetic
                        </div>
                    </div>
                </div>
                <div id="cy"></div>
                <div id="cy-tooltip"></div>
            </div>
            <div class="cy-hint">Drag nodes &nbsp;·&nbsp; Scroll to zoom &nbsp;·&nbsp; Click to inspect</div>
        </div>

        <div class="right-pane">
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('report')">Narrative Report</button>
                <button class="tab-btn" id="btn-detail" onclick="switchTab('detail')">Node Detail</button>
            </div>

            <div class="content-area">
                <div id="panel-report" class="panel active">
                    <h2>Introduction</h2>
                    <div class="summary-box">
                        {overview_html}
                    </div>

                    <h2>Literature-Ranked Disease-Associated Proteins</h2>
                    <div class="summary-box" style="border-left-color:#fb8c00; background:#fff8e1;">
                        Proteins are ranked by the number of distinct PubMed
                        references that mention them across the top
                        {len(pathways)} enriched pathway sections of the
                        v1 literature search. Click any protein to inspect
                        its supporting papers and drug interactions.
                        {lit_top_html}
                    </div>

                    <h2>Overview of the Enriched Pathways</h2>
                    <div class="summary-box" style="border-left-color: #607d8b; background: #eceff1;">
                        <strong>System Synthesis:</strong>
                        The enriched biological pathways highlight the core molecular mechanisms
                        of {html_mod.escape(disease_short)}.
                        Top proteins by significance include {first_gene_html}.
                        Click any node in the network to explore details.
                    </div>
                    <h2>Key Enriched Pathways (Top {len(pathways)})</h2>
{pathway_html}
                </div>

                <div id="panel-detail" class="panel">
                    <div id="empty-detail" style="color: #888; text-align: center; margin-top: 50px;">
                        <em>👈 Click on a Protein or Pathway node in the network to view full details.</em>
                    </div>
                    <div id="dynamic-detail" style="display:none;"></div>
                </div>
            </div>
        </div>
    </main>

    <script>
        function switchTab(tabName) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
            if(tabName === 'report') {{
                document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
                document.getElementById('panel-report').classList.add('active');
            }} else {{
                document.getElementById('btn-detail').classList.add('active');
                document.getElementById('panel-detail').classList.add('active');
            }}
        }}

        const pathwayRefs = {{
{refs_js}
        }};

        // Pathway → proteins map (for detail panel)
        const pathwayProteins = {{
{chr(10).join(f"            '{pw['id']}': {json.dumps(pw['proteins'])}," for pw in pathways)}
        }};

        // Per-gene literature references (PubMed evidence behind each protein)
        const geneLitRefs = {gene_lit_json};

        // Full literature-ranked protein list (for the interactive slider)
        const litRankData    = {lit_rank_json};
        const litRankDefault = {lit_default_n};

        function _clampLitRank(n) {{
            const total = litRankData.length;
            if(total === 0) return 0;
            return Math.max(1, Math.min(parseInt(n, 10) || 1, total));
        }}

        function renderLitRank(n) {{
            n = _clampLitRank(n);
            if(n === 0) return;
            const numEl = document.getElementById('lit-rank-num');
            if(numEl) numEl.textContent = n;
            const list = document.getElementById('lit-rank-list');
            if(!list) return;
            const escHtml = s => String(s)
                .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            list.innerHTML = litRankData.slice(0, n).map(item => {{
                const paper = item.lit_count === 1 ? 'paper' : 'papers';
                const path  = item.pathway_hits === 1 ? 'pathway' : 'pathways';
                const safeGene = escHtml(item.gene);
                return `<li><span class="protein-chip" `
                     + `onclick="highlightNode('${{item.gene}}')">${{safeGene}}</span>`
                     + ` <span style="color:#888;font-size:12px">`
                     + `· ${{item.lit_count}} ${{paper}}`
                     + ` · ${{item.pathway_hits}} ${{path}}`
                     + ` · HR=${{escHtml(item.hr_val)}}</span></li>`;
            }}).join('');
        }}

        // Filter the cytoscape canvas so it only shows the top-N proteins
        // (by literature rank) plus their connected pathways/drugs/edges.
        // Protein nodes outside the top-N are hidden, along with any drug
        // nodes that lose all of their visible protein neighbors.
        function applyCanvasFilter(n) {{
            if(typeof cy === 'undefined' || !cy) return;
            n = _clampLitRank(n);
            if(n === 0) return;
            cy.batch(function() {{
                cy.nodes('[type="protein"]').forEach(function(node) {{
                    const rank = node.data('litRank');
                    const visible = (typeof rank === 'number'
                                     && rank >= 1 && rank <= n);
                    node.style('display', visible ? 'element' : 'none');
                }});
                cy.nodes('[type="drug"]').forEach(function(d) {{
                    let keep = false;
                    d.connectedEdges().forEach(function(e) {{
                        const other = e.source().id() === d.id()
                                      ? e.target() : e.source();
                        if(other.data('type') === 'protein'
                           && other.style('display') !== 'none') {{
                            keep = true;
                        }}
                    }});
                    d.style('display', keep ? 'element' : 'none');
                }});
            }});
        }}

        function syncLitRank(n) {{
            renderLitRank(n);
            applyCanvasFilter(n);
        }}

        function setLitRank(n) {{
            const slider = document.getElementById('lit-rank-slider');
            if(slider) slider.value = n;
            syncLitRank(n);
        }}

        // Render the list immediately (cy may not exist yet — canvas filter
        // is applied in a separate IIFE after cytoscape is initialized).
        renderLitRank(litRankDefault);

        const elements = [
            {elements_js}
        ];

        // Modern force-directed layout via cytoscape-fcose. Falls back to
        // the built-in cose if fcose didn't register for some reason.
        function getFcoseOpts(randomize) {{
            return {{
                name: 'fcose',
                animate: true,
                animationDuration: 700,
                animationEasing: 'ease-out',
                quality: 'default',
                nodeSeparation: 80,
                idealEdgeLength: 110,
                nodeRepulsion: 5500,
                edgeElasticity: 0.45,
                gravity: 0.25,
                gravityRange: 3.8,
                gravityCompound: 1.0,
                numIter: 2500,
                tile: true,
                tilingPaddingVertical: 12,
                tilingPaddingHorizontal: 12,
                randomize: !!randomize,
                packComponents: true,
                padding: 36,
                fit: true
            }};
        }}
        function getCoseOpts() {{
            return {{
                name: 'cose',
                animate: true,
                animationDuration: 1000,
                nodeRepulsion: 6000,
                idealEdgeLength: 100,
                spacingFactor: {spacing},
                padding: 30,
                randomize: true,
                fit: true
            }};
        }}
        function resetLayout() {{
            var opts;
            try {{
                cy.makeLayout({{ name: 'fcose' }});
                opts = getFcoseOpts(true);
            }} catch(e) {{
                opts = getCoseOpts();
            }}
            cy.layout(opts).run();
        }}

        const cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: elements,
            userZoomingEnabled: true,
            userPanningEnabled: true,
            boxSelectionEnabled: false,
            autoungrabify: false,
            style: [
                {{
                    selector: 'node[type="pathway"]',
                    style: {{
                        'background-color': '{colors['pathway']}',
                        'background-fill': 'radial-gradient',
                        'background-gradient-stop-colors': '#3b82f6 {colors['pathway']} #1e3a8a',
                        'background-gradient-stop-positions': '0 60 100',
                        'border-width': 1.5,
                        'border-color': '#1e3a8a',
                        'border-opacity': 0.8,
                        'label': 'data(name)',
                        'shape': 'hexagon',
                        'width': 44, 'height': 44,
                        'color': '#0f172a',
                        'font-family': 'Inter, system-ui, sans-serif',
                        'font-weight': 600,
                        'text-valign': 'bottom',
                        'text-margin-y': 6,
                        'font-size': 10,
                        'text-outline-width': 2,
                        'text-outline-color': '#ffffff',
                        'text-outline-opacity': 0.9
                    }}
                }},
                {{
                    selector: 'node[type="protein"]',
                    style: {{
                        'background-color': '#475569',
                        'background-fill': 'radial-gradient',
                        'background-gradient-stop-colors': '#94a3b8 #475569 #1e293b',
                        'background-gradient-stop-positions': '0 55 100',
                        'border-width': 2,
                        'border-color': '#ffffff',
                        'label': 'data(name)',
                        'shape': 'ellipse',
                        'width': 32, 'height': 32,
                        'color': '#0f172a',
                        'font-family': 'Inter, ui-monospace, Menlo, monospace',
                        'font-weight': 700,
                        'text-valign': 'bottom',
                        'text-margin-y': 6,
                        'font-size': 11,
                        'text-outline-width': 2,
                        'text-outline-color': '#ffffff',
                        'text-outline-opacity': 0.95
                    }}
                }},
                {{
                    selector: 'node[type="drug"]',
                    style: {{
                        'background-color': '#ffffff',
                        'border-width': 1.8,
                        'border-color': '{colors['drug']}',
                        'label': 'data(name)',
                        'shape': 'round-rectangle',
                        'width': 78, 'height': 26,
                        'color': '{colors['drug']}',
                        'font-family': 'Inter, system-ui, sans-serif',
                        'font-weight': 600,
                        'text-valign': 'center',
                        'font-size': 10
                    }}
                }},
                {{
                    selector: 'node[type="drug"][subtype="pharmaco"]',
                    style: {{
                        'background-color': '#fff7ed',
                        'border-width': 1.5,
                        'border-color': '#fb923c',
                        'border-style': 'solid',
                        'shape': 'round-rectangle',
                        'width': 88, 'height': 24,
                        'color': '#9a3412',
                        'font-family': 'Inter, system-ui, sans-serif',
                        'font-size': 10,
                        'font-style': 'italic'
                    }}
                }},
                // Subtle global hover glow via overlay (cheap, GPU-friendly).
                {{
                    selector: 'node:active',
                    style: {{
                        'overlay-color': '#1d4ed8',
                        'overlay-opacity': 0.18,
                        'overlay-padding': 8
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 1.6,
                        'line-color': '#cbd5e1',
                        'target-arrow-color': '#cbd5e1',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 0.85,
                        'curve-style': 'bezier',
                        'control-point-step-size': 28,
                        'opacity': 0.7,
                        'label': 'data(relation)',
                        'font-family': 'Inter, system-ui, sans-serif',
                        'font-size': 8,
                        'color': '#475569',
                        'text-rotation': 'autorotate',
                        'text-background-color': '#ffffff',
                        'text-background-opacity': 0.92,
                        'text-background-padding': 2,
                        'text-background-shape': 'round-rectangle',
                        'text-margin-y': -3
                    }}
                }},
                {{
                    selector: 'edge[edge_type="pathway"]',
                    style: {{
                        'line-color': '#93c5fd',
                        'target-arrow-color': '#60a5fa',
                        'opacity': 0.55,
                        'width': 1.8
                    }}
                }},
                {{
                    selector: 'edge[edge_type="ppi"]',
                    style: {{
                        'line-color': '#94a3b8',
                        'line-style': 'dashed',
                        'line-dash-pattern': [4, 3],
                        'target-arrow-shape': 'none',
                        'opacity': 0.55,
                        'width': 1.3
                    }}
                }},
                {{
                    selector: 'edge[edge_type="drug_cat"]',
                    style: {{
                        'line-color': '{colors['drug']}',
                        'target-arrow-color': '{colors['drug']}',
                        'opacity': 0.6,
                        'width': 1.6
                    }}
                }},
                {{
                    selector: 'edge[edge_type="pharmaco"]',
                    style: {{
                        'line-color': '#fb923c',
                        'target-arrow-color': '#fb923c',
                        'width': 2,
                        'opacity': 0.85
                    }}
                }},
                {{
                    selector: 'node.highlighted',
                    style: {{
                        'border-width': 3,
                        'border-color': '#f59e0b',
                        'overlay-color': '#f59e0b',
                        'overlay-opacity': 0.18,
                        'overlay-padding': 10,
                        'z-index': 99
                    }}
                }},
                {{
                    selector: 'edge.highlighted',
                    style: {{
                        'line-color': '#f59e0b',
                        'target-arrow-color': '#f59e0b',
                        'width': 2.6,
                        'opacity': 1,
                        'z-index': 99
                    }}
                }},
                {{
                    selector: 'node.dimmed, edge.dimmed',
                    style: {{ 'opacity': 0.1 }}
                }}
            ],
            layout: {{ name: 'preset' }}   // placeholder; real layout runs below
        }});

        // Run the best available force-directed layout
        (function() {{
            var opts;
            try {{
                cy.makeLayout({{ name: 'fcose' }});  // throws if fcose not registered
                opts = getFcoseOpts(true);
            }} catch(e) {{
                opts = getCoseOpts();
            }}
            cy.layout(opts).run();
        }})();

        // ── Wire up the literature-rank slider now that cy exists ──────────
        (function initLitRankSync() {{
            const slider = document.getElementById('lit-rank-slider');
            const fitVisible = (duration) => {{
                const vis = cy.elements(':visible');
                if(vis.length > 0) {{
                    cy.animate({{ fit: {{ eles: vis, padding: 30 }} }},
                               {{ duration: duration }});
                }}
            }};
            if(slider) {{
                slider.addEventListener('input', e =>
                    syncLitRank(e.target.value));
                // On release, gently re-fit the camera to the visible nodes
                slider.addEventListener('change', () => fitVisible(350));
            }}
            applyCanvasFilter(litRankDefault);
            // After the initial force-directed layout settles, re-fit on
            // the visible subset so hidden ranks don't waste viewport space.
            cy.one('layoutstop', () => fitVisible(450));
        }})();

        // ── Edge type toggles & label toggles ──────────────────────────────
        const _hiddenEdgeTypes = new Set();
        let _showEdgeLabels = false;

        function toggleEdgeType(edgeType, btn) {{
            const sel = `edge[edge_type="${{edgeType}}"]`;
            if(_hiddenEdgeTypes.has(edgeType)) {{
                _hiddenEdgeTypes.delete(edgeType);
                cy.$(sel).style('display', 'element');
                if(btn) btn.classList.add('active');
            }} else {{
                _hiddenEdgeTypes.add(edgeType);
                cy.$(sel).style('display', 'none');
                if(btn) btn.classList.remove('active');
            }}
        }}
        function toggleEdgeLabels(btn) {{
            _showEdgeLabels = !_showEdgeLabels;
            cy.style().selector('edge')
                .style('text-opacity', _showEdgeLabels ? 1 : 0)
                .update();
            if(btn) btn.classList.toggle('active', _showEdgeLabels);
        }}
        // Hide edge labels by default to keep the graph readable
        cy.style().selector('edge').style('text-opacity', 0).update();

        cy.on('tap', 'node', function(evt) {{
            var node = evt.target;
            cy.elements().removeClass('highlighted dimmed');
            var connected = node.neighborhood().add(node);
            cy.elements().not(connected).addClass('dimmed');
            connected.addClass('highlighted');
            if(node.data('type') === 'protein') {{
                renderProteinDetail(node.data());
            }} else if(node.data('type') === 'pathway') {{
                renderPathwayDetail(node.data());
            }} else if(node.data('type') === 'drug') {{
                renderDrugDetail(node.data());
            }}
            switchTab('detail');
        }});

        cy.on('tap', function(evt) {{
            if(evt.target === cy) {{
                cy.elements().removeClass('highlighted dimmed');
            }}
        }});

        // ── Hover tooltip ──────────────────────────────────────────────────────
        const tooltip = document.getElementById('cy-tooltip');
        cy.on('mouseover', 'node', function(evt) {{
            var d = evt.target.data();
            var label = '';
            if(d.type === 'pathway') {{
                label = `<strong style="font-size:13px">${{d.name}}</strong><br>
                         <span style="color:#aaa">Pathway · ${{d.source}}</span><br>
                         Proteins: <b>${{d.count}}</b> &nbsp; p = ${{d.pval}}`;
            }} else if(d.type === 'protein') {{
                const litLine = (typeof d.litCount === 'number' && d.litCount > 0)
                    ? `<br><span style="color:#ffd54f">📚 Literature: ${{d.litCount}} paper${{d.litCount === 1 ? '' : 's'}}</span>`
                    : '';
                label = `<strong style="font-size:13px">${{d.name}}</strong><br>
                         <span style="color:#aaa">Protein / Gene · Rank #${{d.litRank ?? '?'}}</span><br>
                         HR: <b>${{d.hr}}</b> &nbsp; p = ${{d.pval}}${{litLine}}<br>
                         <span style="color:#ccc;font-size:11px">${{(d.desc||'').slice(0,60)}}${{d.desc && d.desc.length>60?'…':''}}</span>`;
            }} else if(d.type === 'drug') {{
                if(d.subtype === 'pharmaco') {{
                    const ap = d.approved ? ' · FDA-approved' : '';
                    label = `<strong style="font-size:13px">${{d.name}}</strong><br>
                             <span style="color:#ffab91">Pharmacogenetic drug${{ap}}</span>`;
                }} else {{
                    label = `<strong style="font-size:13px">${{d.name}}</strong><br>
                             <span style="color:#aaa">Drug Category</span>`;
                }}
            }}
            tooltip.innerHTML = label;
            tooltip.style.display = 'block';
        }});
        cy.on('mouseout', 'node', function() {{
            tooltip.style.display = 'none';
        }});
        cy.on('mousemove', function(evt) {{
            if(tooltip.style.display !== 'none') {{
                var rect = document.getElementById('cy-container').getBoundingClientRect();
                var x = evt.originalEvent.clientX - rect.left + 14;
                var y = evt.originalEvent.clientY - rect.top + 14;
                // Keep tooltip within container
                if(x + 230 > rect.width)  x = evt.originalEvent.clientX - rect.left - 230;
                if(y + 100 > rect.height) y = evt.originalEvent.clientY - rect.top  - 100;
                tooltip.style.left = x + 'px';
                tooltip.style.top  = y + 'px';
            }}
        }});
        // Hide tooltip while dragging a node
        cy.on('grab', 'node', function() {{ tooltip.style.display = 'none'; }});

        function highlightNode(name) {{
            var node = cy.getElementById(name);
            if(node.length > 0) {{
                cy.elements().removeClass('highlighted dimmed');
                var connected = node.neighborhood().add(node);
                cy.elements().not(connected).addClass('dimmed');
                connected.addClass('highlighted');
                cy.animate({{ fit: {{ eles: connected, padding: 50 }}, duration: 500 }});
                renderProteinDetail(node.data());
                switchTab('detail');
            }}
        }}

        function renderProteinDetail(data) {{
            let tier = 'Targetability: Exploratory';
            let note = 'Repurposing Agent Note: Further evaluation needed.';
            let drugsHTML = '<li>Pending deeper translational reasoning.</li>';
            let badgeClass = 'badge-protein';
            let badgeLabel = 'Protein / Gene';
{protein_detail_js}
            const pathwayList = Object.entries(pathwayProteins)
                .filter(([pid, genes]) => genes.includes(data.name))
                .map(([pid]) => {{
                    const pNode = cy.getElementById(pid);
                    const pName = pNode.length ? pNode.data('name') : pid;
                    return `<li style="cursor:pointer; color:var(--color-pathway);"
                        onclick="cy.getElementById('${{pid}}').trigger('tap')">${{pName}}</li>`;
                }}).join('');

            // Pharmacogenetic drugs: collect drug nodes connected via 'pharmacogenetic' edges
            const node = cy.getElementById(data.name);
            const pharmaDrugs = [];
            const ppiPartners = [];
            if(node && node.length) {{
                node.connectedEdges().forEach(e => {{
                    const et = e.data('edge_type');
                    if(et === 'pharmaco') {{
                        const other = e.source().id() === data.name ? e.target() : e.source();
                        pharmaDrugs.push(other);
                    }} else if(et === 'ppi') {{
                        const other = e.source().id() === data.name ? e.target() : e.source();
                        ppiPartners.push({{node: other, score: e.data('score')}});
                    }}
                }});
            }}
            const pharmaHTML = pharmaDrugs.length
                ? pharmaDrugs.map(n => {{
                    const ap = n.data('approved') ? 'fda-approved' : '';
                    return `<span class="drug-chip ${{ap}}" onclick="cy.getElementById('${{n.id()}}').trigger('tap')">${{n.data('name')}}</span>`;
                  }}).join('')
                : '<em style="color:#999">No pharmacogenetic interaction in DGIdb.</em>';
            const ppiHTML = ppiPartners.length
                ? ppiPartners.sort((a,b)=>b.score-a.score).slice(0,8).map(p =>
                    `<span class="protein-chip"
                       onclick="highlightNode('${{p.node.id()}}')">${{p.node.id()}}<span style="font-weight:400;font-size:10px;color:#888;margin-left:4px;">${{p.score.toFixed(2)}}</span></span>`
                  ).join('')
                : '<em style="color:#999">No STRING PPI partners among displayed proteins.</em>';

            // Literature references for this gene
            const refs = (geneLitRefs[data.name] || []);
            const litCount = (typeof data.litCount === 'number') ? data.litCount : refs.length;
            const litHTML = refs.length
                ? '<ul class="ref-list">' + refs.map(r => {{
                    const cite = r.title
                        ? `${{r.num ? '['+r.num+'] ' : ''}}${{r.title}}${{r.journal ? '. <em>'+r.journal+'</em>' : ''}}${{r.year ? '. '+r.year : ''}}`
                        : 'PubMed:' + r.pmid;
                    return `<li>${{cite}} <a class="lit-link" target="_blank" href="https://pubmed.ncbi.nlm.nih.gov/${{r.pmid}}">[PubMed:${{r.pmid}}]</a></li>`;
                  }}).join('') + '</ul>'
                : '<em style="color:#999">No PubMed evidence extracted from v1 sections.</em>';
            const rankBadge = (typeof data.litRank === 'number')
                ? `<span class="tier-badge" style="background:#fff3e0;color:#bf360c;">📚 Lit Rank #${{data.litRank}}</span>` : '';

            const html = `
                <h2 style="color: var(--color-protein);">
                    ${{data.name}}
                    <span class="tier-badge ${{badgeClass}}">${{badgeLabel}}</span>
                    <span class="tier-badge" style="background:#eee;color:#555;">${{tier}}</span>
                    ${{rankBadge}}
                </h2>
                <div class="repurposing-note">${{note}}</div>
                <div class="detail-section">
                    <label>Protein Definition</label>
                    <div>${{data.desc || 'Significant protein in ' + '{html_mod.escape(disease_short)}'}}</div>
                </div>
                <div class="detail-section">
                    <label>Statistical Evidence</label>
                    <div class="stats-grid">
                        <div class="stat-box">HR [95% CI]<strong>${{data.hr}}</strong></div>
                        <div class="stat-box">P-value<strong>${{data.pval}}</strong></div>
                        <div class="stat-box">Literature<strong>${{litCount}} paper${{litCount === 1 ? '' : 's'}}</strong></div>
                    </div>
                </div>
                <div class="detail-section">
                    <label>Associated Pathways</label>
                    <ul style="margin-top:5px; padding-left:20px; color:#444;">
                        ${{pathwayList || '<li>Not mapped to displayed pathways.</li>'}}
                    </ul>
                </div>
                <div class="detail-section">
                    <label>STRING Functional Interaction Partners (PPI)</label>
                    <div class="protein-chip-list">${{ppiHTML}}</div>
                </div>
                <div class="detail-section">
                    <label>Pharmacogenetic Drugs</label>
                    <div>${{pharmaHTML}}</div>
                </div>
                <div class="detail-section">
                    <label>Drug Category</label>
                    <ul style="margin-top:5px; padding-left:20px; color:#444;">${{drugsHTML}}</ul>
                </div>
                <div class="detail-section">
                    <label>Supporting Literature (${{litCount}} PubMed reference${{litCount === 1 ? '' : 's'}})</label>
                    ${{litHTML}}
                </div>`;

            document.getElementById('empty-detail').style.display = 'none';
            const container = document.getElementById('dynamic-detail');
            container.innerHTML = html;
            container.style.display = 'block';
        }}

        function renderDrugDetail(data) {{
            const node = cy.getElementById(data.id);
            const linkedGenes = [];
            if(node && node.length) {{
                node.connectedEdges().forEach(e => {{
                    const other = e.source().id() === data.id ? e.target() : e.source();
                    if(other.data('type') === 'protein') linkedGenes.push(other);
                }});
            }}
            const isPharmaco = data.subtype === 'pharmaco';
            const apTag = isPharmaco
                ? (data.approved
                    ? '<span class="tier-badge" style="background:#e8f5e9;color:#2e7d32;">FDA-approved</span>'
                    : '<span class="tier-badge" style="background:#fff3e0;color:#bf360c;">Investigational</span>')
                : '';
            const subtypeTag = isPharmaco
                ? '<span class="tier-badge" style="background:#fff3e0;color:#bf360c;">Pharmacogenetic</span>'
                : '<span class="tier-badge" style="background:#eef2f6;color:#455a64;">Drug Category</span>';
            const geneChips = linkedGenes.length
                ? linkedGenes.map(n =>
                    `<span class="protein-chip"
                       onclick="highlightNode('${{n.id()}}')">${{n.id()}}</span>`).join('')
                : '<em style="color:#999">No linked proteins in this graph.</em>';
            const html = `
                <h2 style="color: #bf360c;">${{data.name}} ${{subtypeTag}} ${{apTag}}</h2>
                <div class="detail-section">
                    <label>Linked Proteins (relation: ${{isPharmaco ? 'pharmacogenetic' : 'category'}})</label>
                    <div class="protein-chip-list">${{geneChips}}</div>
                </div>
                ${{isPharmaco ? `<div class="detail-section">
                    <label>Source</label>
                    <div>Drug-Gene Interaction Database (<a class="lit-link" target="_blank" href="https://dgidb.org/results?searchType=gene&searchTerms=${{linkedGenes.map(n=>n.id()).join('%2C')}}">DGIdb</a>),
                    DGIdb interaction score: ${{(data.score ?? 0).toFixed ? data.score.toFixed(2) : data.score}}.</div>
                </div>` : ''}}`;
            document.getElementById('empty-detail').style.display = 'none';
            const container = document.getElementById('dynamic-detail');
            container.innerHTML = html;
            container.style.display = 'block';
        }}

        function renderPathwayDetail(data) {{
            const refs = pathwayRefs[data.id] || [];
            const refItems = refs.length > 0
                ? refs.map(r => `<li>${{r}}</li>`).join('')
                : '<li><em>No references extracted.</em></li>';

            const proteinList = (pathwayProteins[data.id] || []).map(gene => {{
                return `<span class="protein-chip"
                    onclick="highlightNode('${{gene}}')">${{gene}}</span>`;
            }}).join('');

            const html = `
                <h2 style="color: var(--color-pathway); font-size: 17px;">
                    ${{data.name}}
                    <span style="font-size:13px; color:#666; font-weight:normal; margin-left:5px;">
                        (${{data.termId}})
                    </span>
                </h2>
                <div class="detail-section">
                    <label>Pathway Enrichment Statistics (Table 1)</label>
                    <div class="stats-grid">
                        <div class="stat-box">Source<br>
                            <span class="tier-badge badge-pathway" style="margin:4px 0 0 0;">
                                ${{data.source}}
                            </span>
                        </div>
                        <div class="stat-box">Proteins<strong>${{data.count}}</strong></div>
                        <div class="stat-box">Weighted Score<strong>${{data.score}}</strong></div>
                        <div class="stat-box">p-value<strong>${{data.pval}}</strong></div>
                    </div>
                </div>
                <div class="detail-section">
                    <label>Associated Proteins</label>
                    <div class="protein-chip-list">
                        ${{proteinList || '<em style="color:#999">No proteins mapped.</em>'}}
                    </div>
                </div>
                <div class="detail-section">
                    <label>Full Academic Context</label>
                    <div class="academic-text">${{data.context}}</div>
                </div>
                <div class="detail-section">
                    <label>Linked References</label>
                    <ul class="ref-list">${{refItems}}</ul>
                </div>`;

            document.getElementById('empty-detail').style.display = 'none';
            const container = document.getElementById('dynamic-detail');
            container.innerHTML = html;
            container.style.display = 'block';
        }}
    </script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# 9. File Discovery for Batch Mode
# ──────────────────────────────────────────────────────────────────────────────
def normalize_stem(name: str) -> str:
    """Lower, replace underscores/spaces/hyphens with empty string for fuzzy match."""
    return re.sub(r"[\s_\-',]", "", name.lower())

def find_v1_for_csv(csv_path: Path, html_dir: Path) -> Path | None:
    """Find the matching v1 HTML for a given CSV file."""
    stem = csv_path.stem  # e.g. "Alzheimer_disease"
    norm_stem = normalize_stem(stem)
    for v1 in html_dir.rglob("*_v1.html"):
        if normalize_stem(v1.stem.replace("_v1", "")) in (norm_stem, normalize_stem(stem)):
            return v1
        # Fuzzy: longest common substring
        common = sum(1 for a, b in zip(normalize_stem(v1.stem), norm_stem) if a == b)
        if common > min(len(normalize_stem(v1.stem)), len(norm_stem)) * 0.75:
            return v1
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 10. Main Entry Point
# ──────────────────────────────────────────────────────────────────────────────
def convert(csv_path: Path, v1_path: Path, out_path: Path, top_n: int = 10,
            enable_ppi: bool = True, enable_pharmaco: bool = True):
    print(f"  CSV : {csv_path.name}")
    print(f"  V1  : {v1_path.name}")

    proteins  = load_proteins(csv_path)
    html_src  = read_v1(v1_path)
    info      = parse_v1(html_src, proteins, top_n=top_n)
    colors    = pick_colors(info["disease_name"])

    pw_nodes, pr_nodes, dr_nodes, edges = build_elements(
        info["pathways"], proteins,
        enable_ppi=enable_ppi, enable_pharmaco=enable_pharmaco)

    output = generate_v3_html(
        disease_name   = info["disease_name"],
        n_proteins     = info["n_proteins"],
        n_pathways     = info["n_pathways"],
        intro_paragraphs = info["intro_paragraphs"],
        pathways       = info["pathways"],
        proteins       = proteins,
        pathway_nodes  = pw_nodes,
        protein_nodes  = pr_nodes,
        drug_nodes     = dr_nodes,
        edges          = edges,
        colors         = colors,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"  OUT : {out_path}")
    print(f"  Proteins={len(proteins)}  Pathways={len(info['pathways'])}  "
          f"Edges≈{len(edges)}")


def main():
    parser = argparse.ArgumentParser(description="Generate BioInsight v3 HTML")
    parser.add_argument("--csv",      type=Path, help="Path to disease CSV file")
    parser.add_argument("--v1",       type=Path, help="Path to v1 HTML file")
    parser.add_argument("--out",      type=Path, help="Output v3 HTML path (optional)")
    parser.add_argument("--batch",    action="store_true",
                        help="Auto-discover and convert all diseases")
    parser.add_argument("--top-n",   type=int, default=10,
                        help="Max number of pathways to display (default: 10)")
    parser.add_argument("--csv-dir",  type=Path, default=CSV_DIR,
                        help=f"CSV directory (default: {CSV_DIR})")
    parser.add_argument("--html-dir", type=Path, default=HTML_DIR,
                        help=f"HTML base directory (default: {HTML_DIR})")
    parser.add_argument("--no-ppi",   action="store_true",
                        help="Disable STRING-DB gene-gene PPI edges")
    parser.add_argument("--no-pharmaco", action="store_true",
                        help="Disable DGIdb pharmacogenetic drug nodes")
    args = parser.parse_args()

    if args.batch:
        csv_dir  = args.csv_dir
        html_dir = args.html_dir
        csv_files = sorted(csv_dir.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in {csv_dir}")
            sys.exit(1)
        ok, fail = 0, 0
        for csv_path in csv_files:
            v1_path = find_v1_for_csv(csv_path, html_dir)
            if not v1_path:
                print(f"[SKIP] No v1 HTML found for {csv_path.name}")
                fail += 1
                continue
            out_path = v1_path.parent / (
                v1_path.stem.replace("_v1", "") + "_v3_auto.html")
            print(f"\n[{csv_path.stem}]")
            try:
                convert(csv_path, v1_path, out_path, top_n=args.top_n,
                        enable_ppi=not args.no_ppi,
                        enable_pharmaco=not args.no_pharmaco)
                ok += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback; traceback.print_exc()
                fail += 1
        print(f"\nDone: {ok} succeeded, {fail} skipped/failed.")

    elif args.csv and args.v1:
        csv_path = args.csv
        v1_path  = args.v1
        if args.out:
            out_path = args.out
        else:
            stem = v1_path.stem.replace("_v1", "")
            out_path = v1_path.parent / f"{stem}_v3_auto.html"
        print(f"\n[{csv_path.stem}]")
        convert(csv_path, v1_path, out_path, top_n=args.top_n,
                enable_ppi=not args.no_ppi,
                enable_pharmaco=not args.no_pharmaco)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
