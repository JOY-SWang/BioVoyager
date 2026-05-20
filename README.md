# BioVoyager

BioVoyager turns disease-associated protein signals into an evidence-grounded,
interactive research artifact. Given a disease name, a protein association table,
and cohort metadata, the pipeline can:

- identify enriched biological pathways from significant proteins;
- retrieve and rank disease-specific literature evidence;
- synthesize pathway and protein mechanisms with citations;
- add PPI and drug-gene context; and
- generate an interactive Cytoscape-based HTML dashboard.

## Repository Layout

```text
BioVoyager/
  README.md
  src/
    run.py                 # Generate the v1 narrative HTML report
    generate_v3.py         # Convert CSV + v1 HTML into *_v3_auto.html
    agents/                # Planning, query, reasoning, and writing agents
    host_webs/templates/   # Optional local HTML viewer templates
  test_data/               # Example disease protein association CSV files
  knowledge_base/          # Offline PPI and protein function data, downloaded separately
```

Generated outputs are usually written under `src/results_0411/`. Runtime caches
for STRING-DB and DGIdb requests are written under `src/.cache_v3/`.

## Data Setup

Download the offline knowledge base and place it at:

```text
BioVoyager/knowledge_base/
  ppi_significant.csv
  protein_functions.json
```

Knowledge base download link:

```text
https://www.dropbox.com/scl/fo/0fe7kz9xdt8az1f6etsen/AJSL8RXkUOgMpI_ZaftQ_To?rlkey=pwlv4x2vxf9j3mms3fnpj0uj1&st=br2iey0a&dl=0
```

If you run the full pathway ranking pipeline, also download a BioBERT checkpoint
and configure its path in the code or through your own configuration wrapper.
Avoid hard-coding machine-specific absolute paths before publishing the project.

## Environment

Python 3.10 or newer is recommended.

Install the full set of Python dependencies:

```bash
pip install pandas markdown openai python-dotenv httpx requests \
  biopython scikit-learn torch transformers tqdm networkx \
  fastapi jinja2 uvicorn pdfkit weasyprint mysql-connector-python
```

For PDF export through `pdfkit`, install the system package `wkhtmltopdf`.

## API Keys

Create a local `.env` file for private credentials. Do not commit it.

```bash
OPENAI_API_KEY=...
NCBI_API_KEY=...
S2_API_KEY=...
```

`OPENAI_API_KEY` is required for the LLM-based agents. `NCBI_API_KEY` and
`S2_API_KEY` are optional but improve PubMed and Semantic Scholar access.

## Quick Start

Run from the repository root unless noted otherwise.

Generate the narrative v1 report:

```bash
cd src
python run.py
```

Generate an interactive v3 dashboard from an existing protein CSV and v1 report:

```bash
python src/generate_v3.py \
  --csv test_data/Alzheimer_disease.csv \
  --v1 src/results_0411/alzheimer/Alzheimer_disease_v1.html \
  --out src/results_0411/alzheimer/Alzheimer_disease_v3_auto.html
```

To avoid external STRING-DB and DGIdb requests during v3 generation:

```bash
python src/generate_v3.py \
  --csv test_data/Alzheimer_disease.csv \
  --v1 src/results_0411/alzheimer/Alzheimer_disease_v1.html \
  --out src/results_0411/alzheimer/Alzheimer_disease_v3_auto.html \
  --no-ppi \
  --no-pharmaco
```

Batch conversion is also supported:

```bash
python src/generate_v3.py --batch
```

## Optional Local Viewer

The FastAPI viewer can serve generated reports from `src/results_0411/`.

```bash
cd src
uvicorn html_viewer:app --reload
```

Then open the URL printed by Uvicorn.

