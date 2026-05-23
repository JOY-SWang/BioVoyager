from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import re
import csv
import json
import tempfile

from jobs import (
    CSVValidationError,
    JobCreateResponse,
    JobView,
    RateLimitError,
    create_job,
    get_job,
    parse_and_validate_csv,
    run_pipeline_stub,
)

# Repo layout: <repo_root>/src/html_viewer.py ; results live in <repo_root>/src/results_0411
# and inputs live in <repo_root>/test_data. Resolve relative to this file so the
# viewer runs from any working directory, on any machine.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SRC_DIR)
RESULTS_DIR = os.environ.get("BIOVOYAGER_RESULTS_DIR", os.path.join(_SRC_DIR, "results_0411"))
TEST_DATA_DIR = os.environ.get("BIOVOYAGER_TEST_DATA_DIR", os.path.join(_REPO_ROOT, "test_data"))
TEMPLATES_DIR = os.path.join(_SRC_DIR, "host_webs", "templates")

# Ordered list of diseases: (display_name, csv_filename, report_rel_path_or_None, body_system)
DISEASE_CONFIG = [
    {
        "name": "Alzheimer Disease",
        "csv": "Alzheimer_disease.csv",
        "report": "alzheimer/Alzheimer_disease_v3_auto.html",
        "category": "Diseases of the Nervous System",
    },
    {
        "name": "Atrial Fibrillation & Flutter",
        "csv": "Atrial_fibrillation_and_flutter.csv",
        "report": "arrhythmia/Atrial_fibrillation_and_flutter_v3_auto.html",
        "category": "Diseases of the Circulatory System",
    },
    {
        "name": "Heart Failure",
        "csv": "Heart_failure,_strict.csv",
        "report": "heartfailure/Heart_failure,_strict_v3_auto.html",
        "category": "Diseases of the Circulatory System",
    },
    {
        "name": "Hypertension",
        "csv": "Hypertension,_essential.csv",
        "report": "hypertension/Hypertension,_essential_v3_auto.html",
        "category": "Diseases of the Circulatory System",
    },
    {
        "name": "Stroke (incl. SAH)",
        "csv": "Stroke,_including_SAH.csv",
        "report": "stroke/Stroke,_including_SAH_v3_auto.html",
        "category": "Diseases of the Circulatory System",
    },
    {
        "name": "Type 2 Diabetes",
        "csv": "Type_2_diabetes_without_complications.csv",
        "report": "diabetes/Type_2_diabetes_without_complications_v3_auto.html",
        "category": "Endocrine / Metabolic Diseases",
    },
    {
        "name": "Parkinson's Disease",
        "csv": "Parkinson's_disease.csv",
        "report": "parkinsons/Parkinson's_disease_v3_auto.html",
        "category": "Diseases of the Nervous System",
    },
    {
        "name": "Depression",
        "csv": "Depression.csv",
        "report": "depression/Depression_v3_auto.html",
        "category": "Mental & Behavioural Disorders",
    },
    {
        "name": "Rheumatoid Arthritis",
        "csv": "Rheumatoid_arthritis.csv",
        "report": "arthritis/Rheumatoid_arthritis_v3_auto.html",
        "category": "Musculoskeletal Diseases",
    },
    {
        "name": "Chronic Kidney Disease",
        "csv": "Chronic_kidney_disease.csv",
        "report": "kidneydisease/Chronic_kidney_disease_v3_auto.html",
        "category": "Diseases of the Genitourinary System",
    },
    {
        "name": "Liver Cirrhosis & Fibrosis",
        "csv": "Fibrosis_and_cirrhosis_of_liver.csv",
        "report": None,
        "category": "Diseases of the Digestive System",
    },
]


def load_portal_data():
    """Load protein rows from each disease CSV; return enriched DISEASE_CONFIG list."""
    result = []
    for cfg in DISEASE_CONFIG:
        entry = dict(cfg)
        csv_path = os.path.join(TEST_DATA_DIR, cfg["csv"])
        proteins = []
        if os.path.exists(csv_path):
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    proteins.append({
                        "protein": row.get("Protein", ""),
                        "definition": row.get("Protein_definition", ""),
                        "nb_individual": row.get("NB_individual", ""),
                        "nb_case": row.get("NB_case", ""),
                        "hr": row.get("HR[95%CI]", ""),
                        "p_value": row.get("P_value", ""),
                    })
        entry["proteins"] = proteins
        entry["n_proteins"] = len(proteins)
        result.append(entry)
    return result


app = FastAPI()
app.mount("/static", StaticFiles(directory=RESULTS_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def get_html_files():
    html_files = []
    for root, dirs, files in os.walk(RESULTS_DIR):
        for file in files:
            if (file.endswith('_v1.html') or file.endswith('_v2.html')
                    or file.endswith('_v3.html') or file.endswith('_v3_auto.html')
                    or file.endswith('_v3_modern.html')
                    or file.endswith('.textextract.html')
                    or file.endswith('.legacy.html')):
                rel_dir = os.path.relpath(root, RESULTS_DIR)
                rel_file = os.path.join(rel_dir, file) if rel_dir != '.' else file
                html_files.append(rel_file)
    return sorted(html_files)

def load_html_content(rel_path):
    abs_path = os.path.join(RESULTS_DIR, rel_path)
    with open(abs_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # The report's own subfolder relative to RESULTS_DIR (e.g. "alzheimer").
    report_subdir = os.path.dirname(rel_path)

    def repl_relative_img(match):
        # src="imgs/xyz.png" or "./imgs/xyz.png" or "/imgs/xyz.png" -> /static/<subdir>/imgs/xyz.png
        filename = match.group(1)
        joined = f"{report_subdir}/imgs/{filename}" if report_subdir else f"imgs/{filename}"
        static_path = f"/static/{joined}"
        return f'src="{static_path}"'

    def repl_absolute_img(match):
        # Any absolute path that contains "/results_0411/<subdir>/imgs/<file>" -> /static/<subdir>/imgs/<file>
        # Captures the trailing portion starting at the report subdir.
        tail = match.group(1)
        static_path = f"/static/{tail}"
        return f'src="{static_path}"'

    # 1) Relative imgs/ references inside the report
    html = re.sub(r'src=["\'](?:\.?/)?imgs/([^"\']+)["\']', repl_relative_img, html)
    # 2) Any absolute path that points into a results_0411 imgs dir, regardless of
    #    which machine generated the report.
    html = re.sub(
        r'src=["\'][^"\']*?/results_0411/([^"\']+/imgs/[^"\']+)["\']',
        repl_absolute_img,
        html,
    )

    # Enforce image size for display as well
    # Inject CSS for hover effect (only for web display, not PDF)
    hover_css = '''<style>
    .enlarge-on-hover {
        width: 300px !important;
        height: 300px !important;
        max-width: 300px !important;
        max-height: 300px !important;
        object-fit: contain;
        display: block;
        margin: auto;
        transition: width 0.2s, height 0.2s, max-width 0.2s, max-height 0.2s;
    }
    .enlarge-on-hover:hover {
        width: 600px !important;
        height: 600px !important;
        max-width: 600px !important;
        max-height: 600px !important;
        z-index: 10;
        box-shadow: 0 4px 24px rgba(44,62,80,0.20);
    }
    </style>'''
    def clean_style(m):
        style = m.group(1)
        # Remove width/height/max-width/max-height from style
        style = re.sub(r'(?:max-)?width\s*:\s*[^;]+;?', '', style)
        style = re.sub(r'max-height\s*:\s*[^;]+;?', '', style)
        style = re.sub(r'height\s*:\s*[^;]+;?', '', style)
        return f'style="{style}"'
    def add_img_style(match):
        tag = match.group(0)
        # Remove any existing width/height attributes
        tag = re.sub(r'\s(width|height)="[^"]*"', '', tag)
        tag = re.sub(r'\s(width|height)=\'[^"]*\'', '', tag)
        # Remove any width/height in style
        tag = re.sub(r'style=["\']([^"\']*)["\']', clean_style, tag)
        # Add our fixed size and center, and class for hover
        if 'style=' in tag:
            tag = re.sub(r'style=["\']([^"\']*)["\']', lambda m: f'style="{m.group(1)};width:300px;height:300px;max-width:300px;max-height:300px;object-fit:contain;display:block;margin:auto;"', tag)
        else:
            tag = tag.replace('<img', '<img style="width:300px;height:300px;max-width:300px;max-height:300px;object-fit:contain;display:block;margin:auto;"')
        # Add width/height attributes
        tag = re.sub(r'<img', '<img width="300" height="300"', tag)
        # Add class for hover effect
        if 'class=' in tag:
            tag = re.sub(r'class=["\']([^"\']*)["\']', lambda m: f'class="{m.group(1)} enlarge-on-hover"', tag)
        else:
            tag = tag.replace('<img', '<img class="enlarge-on-hover"')
        return tag
    html = re.sub(r'<img[^>]*>', add_img_style, html)
    # Inject CSS for hover effect at the top (if not already present)
    if 'enlarge-on-hover' in html and '<style>' not in html:
        html = hover_css + html

    return html



def format_label(f):
    if "/" not in f:
        return f
    first = f.split("/")[0]
    last = f.split("/")[-1]
    return f"[{first}] {last}"

# NOTE: The old Jinja "/" portal is gone — the React UI in ui/dist owns "/" now.
# Same for /viewer and /view (replaced by React Router routes /demo and /chat).
# /raw, /static, /export_pdf, /api/* remain because the React UI calls them.

@app.get("/api/diseases")
def api_diseases():
    """JSON view of every disease's input proteins and whether a v3 report exists.
    Consumed by the React UI in ui/."""
    return load_portal_data()


@app.get("/api/reports")
def api_reports():
    """List of available pre-generated report files (relative paths under RESULTS_DIR)."""
    return {"files": get_html_files()}


def _client_ip(request: Request) -> str:
    """Best-effort client IP. Honors X-Forwarded-For (Cloudflare adds it)."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.post("/api/jobs", response_model=JobCreateResponse)
async def api_create_job(
    request: Request,
    background: BackgroundTasks,
    disease_name: str = Form(...),
    email: str = Form(...),
    csv_file: UploadFile = ...,
) -> JobCreateResponse:
    """Accept a CSV + disease metadata, validate, start a stub pipeline run."""
    disease_name = disease_name.strip()
    email = email.strip()
    if not disease_name:
        raise HTTPException(status_code=422, detail="disease_name is required")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="email looks invalid")

    raw = await csv_file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="CSV file is empty")

    try:
        proteins = parse_and_validate_csv(raw)
    except CSVValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        job = create_job(
            disease_name=disease_name,
            email=email,
            client_ip=_client_ip(request),
            proteins=proteins,
        )
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e

    background.add_task(run_pipeline_stub, job.job_id)
    return JobCreateResponse(job_id=job.job_id, status=job.status)


@app.get("/api/jobs/{job_id}", response_model=JobView)
def api_get_job(job_id: str) -> JobView:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_view()


@app.get("/raw", response_class=HTMLResponse)
def raw_html(file: str):
    """Serve a pre-generated v3 dashboard with image-paths rewritten to /static.
    Used by the React UI's <ReportView> in an iframe."""
    html_files = get_html_files()
    if file not in html_files:
        return HTMLResponse("<h2>File not found.</h2>", status_code=404)
    return HTMLResponse(load_html_content(file))

@app.get("/export_pdf")
def export_pdf(file: str):
    try:
        import pdfkit  # noqa: F401
    except ImportError:
        return Response(
            "PDF export requires the 'pdfkit' Python package and the wkhtmltopdf system binary. "
            "Install with: pip install pdfkit && brew install wkhtmltopdf (macOS) or apt install wkhtmltopdf (Ubuntu).",
            status_code=501,
        )
    html_files = get_html_files()
    if file not in html_files:
        return Response("File not found.", status_code=404)
    html_content = load_html_content(file)
    # Rewrite /static/<subdir>/imgs/xyz.png back to file:// URLs so wkhtmltopdf
    # can find the image on local disk.
    def static_to_fileurl(match):
        rel_path = match.group(1)
        abs_img_path = os.path.abspath(os.path.join(RESULTS_DIR, rel_path))
        return f'src="file://{abs_img_path}"'
    import re
    html_content = re.sub(r'src=["\']/static/([^"\']+)["\']', static_to_fileurl, html_content)
    # Adjust all <img> tags to have a fixed medium size (e.g., width: 100px, height: 100px)
    def clean_style(m):
        style = m.group(1)
        # Remove width/height/max-width/max-height from style
        style = re.sub(r'(?:max-)?width\s*:\s*[^;]+;?', '', style)
        style = re.sub(r'max-height\s*:\s*[^;]+;?', '', style)
        style = re.sub(r'height\s*:\s*[^;]+;?', '', style)
        return f'style="{style}"'
    def add_img_style(match):
        tag = match.group(0)
        # Remove any existing width/height attributes
        tag = re.sub(r'\s(width|height)="[^"]*"', '', tag)
        tag = re.sub(r'\s(width|height)=\'[^"]*\'', '', tag)
        # Remove any width/height in style
        tag = re.sub(r'style=["\']([^"\']*)["\']', clean_style, tag)
        # Add our fixed size and center
        if 'style=' in tag:
            tag = re.sub(r'style=["\']([^"\']*)["\']', lambda m: f'style="{m.group(1)};width:300px;height:300px;max-width:300px;max-height:300px;object-fit:contain;display:block;margin:auto;"', tag)
        else:
            tag = tag.replace('<img', '<img style="width:300px;height:300px;max-width:300px;max-height:300px;object-fit:contain;display:block;margin:auto;"')
        # Add width/height attributes
        tag = re.sub(r'<img', '<img width="300" height="300"', tag)
        return tag
    html_content = re.sub(r'<img[^>]*>', add_img_style, html_content)
    # Save HTML to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp_html:
        tmp_html.write(html_content)
        tmp_html_path = tmp_html.name
    # Output PDF path
    tmp_pdf_path = tmp_html_path.replace(".html", ".pdf")
    # Convert HTML to PDF with local file access enabled
    options = {'enable-local-file-access': None}
    pdfkit.from_file(tmp_html_path, tmp_pdf_path, options=options)
    # Serve the PDF as a download
    filename = os.path.basename(file).replace(".html", ".pdf")
    response = FileResponse(tmp_pdf_path, filename=filename, media_type="application/pdf")
    return response


# ── React UI (Vite) — production build mount ────────────────────────────────
# `cd ui && bun run build` produces ui/dist/. We mount it as a SPA:
#   - /assets/* and other built files are served directly
#   - any other unmatched GET → index.html (so React Router's /demo, /chat
#     work on hard refresh)
# IMPORTANT: this MUST come after every /api, /static, /raw, /view route above,
# otherwise the catch-all swallows them.
UI_DIST_DIR = os.path.join(_REPO_ROOT, "ui", "dist")

if os.path.isdir(UI_DIST_DIR):
    _ASSETS_DIR = os.path.join(UI_DIST_DIR, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="ui-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Serve a real file if it exists in dist/, otherwise hand back index.html.
        # Path traversal is bounded by os.path.normpath + the isfile check.
        candidate = os.path.normpath(os.path.join(UI_DIST_DIR, full_path))
        if candidate.startswith(UI_DIST_DIR) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(UI_DIST_DIR, "index.html"))
else:
    @app.get("/_ui_status", include_in_schema=False)
    def ui_status():
        return HTMLResponse(
            "<h2>React UI not built. Run <code>cd ui && bun run build</code>.</h2>",
            status_code=503,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3009)
