from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import re
import csv
import json
import pdfkit
import tempfile

RESULTS_DIR = "/Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/src/results_0411"
TEST_DATA_DIR = "/Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/test_data"

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
        "report": "kidney disease/Chronic_kidney_disease_v3_auto.html",
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
templates = Jinja2Templates(directory="host_webs/templates")

def get_html_files():
    html_files = []
    for root, dirs, files in os.walk(RESULTS_DIR):
        for file in files:
            if (file.endswith('_v1.html') or file.endswith('_v2.html')
                    or file.endswith('_v3.html') or file.endswith('_v3_auto.html')):
                rel_dir = os.path.relpath(root, RESULTS_DIR)
                rel_file = os.path.join(rel_dir, file) if rel_dir != '.' else file
                html_files.append(rel_file)
    return sorted(html_files)

def load_html_content(rel_path):
    abs_path = os.path.join(RESULTS_DIR, rel_path)
    with open(abs_path, 'r', encoding='utf-8') as f:
        html = f.read()

    def repl(match):
        original_path = match.group(1)
        # Extract filename only
        filename = os.path.basename(original_path)
        static_path = f"/static/{original_path}"
        print(f"[DEBUG] Rewriting image path: {original_path} → {static_path}")
        return f'src="{static_path}"'

    # Handles:
    #   src="imgs/xyz.png"
    #   src="./imgs/xyz.png"
    #   src="/imgs/xyz.png"
    #   src="/home/ubuntu/BMAgent/src/results/imgs/xyz.png"
    html = re.sub(r'src=["\'](?:\.?/)?imgs/([^"\']+)["\']', repl, html)
    html = re.sub(r'src=["\']/Users/joysw/Desktop/PKU/RA/Upenn/sweSearchMed/drug-target-agent/src/results_0411/([^"\']+)["\']', repl, html)

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

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    portal_data = load_portal_data()
    portal_json = json.dumps(portal_data, ensure_ascii=False)
    return templates.TemplateResponse("portal.html", {"request": request, "portal_json": portal_json})


@app.get("/viewer", response_class=HTMLResponse)
def viewer_index(request: Request):
    html_files = get_html_files()
    html_file_tuples = [(f, format_label(f)) for f in html_files]
    return templates.TemplateResponse("viewer.html", {"request": request, "html_files": html_file_tuples})

@app.get("/raw", response_class=HTMLResponse)
def raw_html(file: str):
    """Serve the processed HTML file directly so it can be loaded in an iframe."""
    html_files = get_html_files()
    if file not in html_files:
        return HTMLResponse("<h2>File not found.</h2>", status_code=404)
    return HTMLResponse(load_html_content(file))


@app.get("/view", response_class=HTMLResponse)
def view_html(request: Request, file: str):
    html_files = get_html_files()
    html_file_tuples = [(f, format_label(f)) for f in html_files]
    if file not in html_files:
        return HTMLResponse("<h2>File not found.</h2>", status_code=404)
    return templates.TemplateResponse("viewer.html", {
        "request": request,
        "html_files": html_file_tuples,
        "selected_file": file,
    })

@app.get("/export_pdf")
def export_pdf(file: str):
    html_files = get_html_files()
    if file not in html_files:
        return Response("File not found.", status_code=404)
    html_content = load_html_content(file)
    # Rewrite /static/src/results/imgs/xyz.png to file:///home/ubuntu/BMAgent/src/results/imgs/xyz.png
    def static_to_fileurl(match):
        filename = match.group(1)
        abs_img_path = os.path.abspath(os.path.join(RESULTS_DIR, 'src/results/imgs', filename))
        file_url = f"file://{abs_img_path}"
        return f'src="{file_url}"'
    import re
    html_content = re.sub(r'src=["\']/static/src/results/imgs/([^"\']+)["\']', static_to_fileurl, html_content)
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


TEMPLATE_PATH = "host_webs/templates/viewer.html"
if not os.path.exists("host_webs/templates"):
    os.makedirs("host_webs/templates")
if not os.path.exists(TEMPLATE_PATH):
    with open(TEMPLATE_PATH, "w") as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Results Viewer</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            background: #f4f6fb;
            color: #222;
        }
        .header {
            background: #2d3e50;
            color: #fff;
            padding: 1.5em 2em 1em 2em;
            box-shadow: 0 2px 8px rgba(44,62,80,0.08);
        }
        .header h3{
            margin: 0;
            font-size: 1.2em;
            letter-spacing: 1px;
        }
        .container {
            max-width: 1400px;
            margin: 2em auto;
            padding: 2em;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(44,62,80,0.10);
        }
        .toc {
            margin-bottom: 2em;
            display: flex;
            align-items: center;
            gap: 1em;
        }
        .toc label {
            font-weight: 500;
            font-size: 1.1em;
        }
        .toc select {
            font-size: 1em;
            padding: 0.5em 1.2em 0.5em 0.8em;
            border-radius: 8px;
            border: 1px solid #bfc9d9;
            background: #f8fafc;
            box-shadow: 0 1px 2px rgba(44,62,80,0.03);
            transition: border 0.2s;
        }
        .toc select:focus {
            border: 1.5px solid #2d3e50;
            outline: none;
        }
        .viewer {
            border: none;
            padding: 2em;
            background: #f8fafc;
            border-radius: 12px;
            min-height: 200px;
            box-shadow: 0 2px 8px rgba(44,62,80,0.06);
        }
        @media (max-width: 1200px) {
            .container {
                padding: 1em;
            }
            .viewer {
                padding: 1em;
            }
            .header {
                padding: 1em;
            }
        }
    </style>
    <script>
        function onFileChange(sel) {
            window.location = '/view?file=' + encodeURIComponent(sel.value);
        }
        function exportToPDF() {
            var sel = document.getElementById('file-select');
            var file = sel.value;
            if (!file) {
                alert('Please select a file to export.');
                return;
            }
            window.open('/export_pdf?file=' + encodeURIComponent(file), '_blank');
        }
    </script>
</head>
<body>
    <div class="header">
        <h3>AI-Agents Results Viewer</h3>
    </div>
    <div class="container">
        <div class="toc">
            <label for="file-select">Select a result to display:</label>
            <select id="file-select" onchange="onFileChange(this)">
                <option value="">-- Select --</option>
                {% for f, label in html_files %}
                    <option value="{{ f }}" {% if selected_file == f %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="viewer">
            {% if html_content %}
                {{ html_content | safe }}
            {% else %}
                <p>Select a file to preview its HTML report.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
''')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3009) 