import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path
from flask import Flask, request, send_file, jsonify, render_template_string
from docx import Document

sys.path.insert(0, os.path.dirname(__file__))
from latex.file_reader import parse_docx
from latex.latex_builder import build_latex_test
from questions.section import Section

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.mkdtemp()


def parse_text_input(text):
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "input.docx")
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(path)
    questions = parse_docx(path)
    shutil.rmtree(tmp)
    return questions


def compile_pdf(latex_str, images):
    """Write .tex, save uploaded images, run pdflatex, return PDF bytes."""
    tmp = tempfile.mkdtemp()
    tex_path = os.path.join(tmp, "test.tex")
    pdf_path = os.path.join(tmp, "test.pdf")

    # Save any uploaded images into images/ subfolder
    img_dir = os.path.join(tmp, "images")
    os.makedirs(img_dir)
    for name, file_obj in images.items():
        file_obj.save(os.path.join(img_dir, name))

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_str)

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "test.tex"],
        cwd=tmp,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not os.path.exists(pdf_path):
        log = result.stdout.decode(errors="replace")
        shutil.rmtree(tmp)
        raise RuntimeError("pdflatex failed:\n" + log[-2000:])

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    shutil.rmtree(tmp)
    return pdf_bytes


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>MathTest Builder</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;1,8..60,300&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --cream: #f7f3ed; --cream2: #ede7dc; --cream3: #ddd5c8;
    --ink: #1a1612; --ink-mid: #4a3f35; --ink-lite: #8c7b6e;
    --accent: #b5451b; --accent2: #d4692f;
    --success: #2d6a4f; --white: #fff; --rule: #c8bfb0;
  }
  html, body { height: 100%; background: var(--cream); color: var(--ink);
    font-family: 'Source Serif 4', Georgia, serif; font-size: 15px; }

  /* HEADER */
  header { display: flex; align-items: stretch; height: 58px;
    border-bottom: 1px solid var(--rule); background: var(--cream); }
  .hdr-stripe { width: 5px; background: var(--accent); flex-shrink: 0; }
  .hdr-inner { display: flex; align-items: center; gap: 12px; padding: 0 20px; flex: 1; }
  .hdr-title { font-family: 'Playfair Display', serif; font-size: 1.3rem;
    font-weight: 700; color: var(--ink); }
  .hdr-sub { font-size: 0.82rem; font-style: italic; color: var(--ink-lite); }
  .accent-bar { height: 2px; background: linear-gradient(90deg, var(--accent), var(--accent2) 60%, transparent); }

  /* LAYOUT */
  .layout { display: grid; grid-template-columns: 1fr 300px;
    gap: 16px; padding: 16px; height: calc(100vh - 62px); }

  /* PANELS */
  .panel { background: var(--white); border: 1px solid var(--rule);
    border-radius: 5px; overflow: hidden; display: flex; flex-direction: column; }
  .panel-hdr { display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; background: var(--cream2);
    border-bottom: 1px solid var(--cream3); flex-shrink: 0; }
  .panel-hdr-title { font-family: 'Playfair Display', serif;
    font-size: 0.88rem; font-weight: 600; color: var(--ink); }
  .badge { width: 20px; height: 20px; border-radius: 50%; background: var(--accent);
    color: #fff; font-size: 0.68rem; font-weight: 700; font-family: monospace;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

  /* LEFT COLUMN */
  .left { display: flex; flex-direction: column; gap: 0; min-height: 0; }

  .title-row { display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-bottom: 1px solid var(--cream3);
    background: var(--white); flex-shrink: 0; }
  .title-row label { font-size: 0.78rem; color: var(--ink-lite);
    font-style: italic; white-space: nowrap; }
  .title-input { flex: 1; border: none; background: transparent;
    font-family: 'Playfair Display', serif; font-size: 1rem; font-weight: 600;
    color: var(--ink); outline: none; }

  .tabs { display: flex; background: var(--cream2);
    border-bottom: 1px solid var(--cream3); flex-shrink: 0; }
  .tab { padding: 7px 14px; font-size: 0.8rem; color: var(--ink-lite);
    cursor: pointer; border-bottom: 2px solid transparent;
    transition: all 0.15s; user-select: none; }
  .tab:hover { color: var(--ink-mid); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent);
    background: var(--white); }

  .pane { display: none; flex: 1; min-height: 0; flex-direction: column; }
  .pane.active { display: flex; }

  textarea { flex: 1; border: none; font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem; line-height: 1.85; color: var(--ink);
    padding: 14px; resize: none; outline: none; background: var(--white); }

  /* DROP ZONE */
  .drop-zone { flex: 1; margin: 14px; border: 2px dashed var(--rule);
    border-radius: 6px; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 8px;
    cursor: pointer; transition: all 0.2s; background: var(--cream); }
  .drop-zone:hover, .drop-zone.over { border-color: var(--accent); background: #fdf4f1; }
  .drop-icon { font-size: 2.2rem; opacity: 0.4; }
  .drop-label { font-family: 'Playfair Display', serif; font-size: 0.95rem; color: var(--ink-mid); }
  .drop-sub { font-size: 0.75rem; color: var(--ink-lite); font-style: italic; }
  .drop-file { font-size: 0.75rem; font-family: monospace; color: var(--success); }
  #file-input { display: none; }

  /* IMAGES PANE */
  .img-pane { flex: 1; display: flex; flex-direction: column;
    min-height: 0; padding: 10px 12px; gap: 8px; }
  .img-add-btn { display: flex; align-items: center; justify-content: center;
    gap: 6px; padding: 8px; background: var(--accent); color: #fff;
    border: none; border-radius: 4px; font-family: 'Playfair Display', serif;
    font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: background 0.15s; }
  .img-add-btn:hover { background: var(--accent2); }
  .img-note { font-size: 0.72rem; font-style: italic; color: var(--ink-lite); }
  .img-list { flex: 1; overflow-y: auto; border: 1px solid var(--cream3);
    border-radius: 4px; background: var(--cream); min-height: 0; }
  .img-item { display: flex; align-items: center; justify-content: space-between;
    padding: 6px 10px; border-bottom: 1px solid var(--cream3); font-size: 0.78rem;
    font-family: monospace; color: var(--ink-mid); }
  .img-item:last-child { border-bottom: none; }
  .img-remove { background: none; border: none; color: var(--ink-lite);
    cursor: pointer; font-size: 0.9rem; padding: 0 2px; line-height: 1; }
  .img-remove:hover { color: var(--accent); }
  .img-empty { padding: 20px; text-align: center; color: var(--ink-lite);
    font-size: 0.78rem; font-style: italic; }
  #img-file-input { display: none; }

  /* HINT BAR */
  .hint-bar { display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
    padding: 6px 12px; background: var(--cream2);
    border-top: 1px solid var(--cream3); flex-shrink: 0; }
  .hint-bar span { font-size: 0.7rem; color: var(--ink-lite); font-style: italic; }
  .chip { font-size: 0.68rem; font-family: monospace; background: var(--cream3);
    color: var(--ink-mid); padding: 2px 6px; border-radius: 3px; }

  /* RIGHT COLUMN */
  .right { display: flex; flex-direction: column; gap: 10px; min-height: 0; }

  .gen-inner { padding: 12px; display: flex; flex-direction: column; gap: 8px; }
  .gen-btn { padding: 12px; background: var(--accent); color: #fff; border: none;
    border-radius: 4px; font-family: 'Playfair Display', serif; font-size: 1rem;
    font-weight: 600; cursor: pointer; transition: all 0.15s; width: 100%; }
  .gen-btn:hover:not(:disabled) { background: var(--accent2); }
  .gen-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .dl-btn { display: flex; align-items: center; justify-content: center;
    gap: 6px; padding: 11px; background: var(--success); color: #fff;
    border: none; border-radius: 4px; font-family: 'Playfair Display', serif;
    font-size: 0.95rem; font-weight: 600; cursor: pointer; width: 100%;
    text-decoration: none; transition: opacity 0.15s; display: none; }
  .dl-btn:hover { opacity: 0.88; }
  .dl-btn.visible { display: flex; }

  /* LOG */
  .log-panel { flex: 1; min-height: 0; display: flex; flex-direction: column; }
  .log-body { flex: 1; overflow-y: auto; background: #1a1612;
    padding: 10px 12px; min-height: 0; }
  .log-line { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    line-height: 1.9; color: #c8c0b0; white-space: pre-wrap; }
  .log-line.ok  { color: #6fcf97; }
  .log-line.err { color: #eb5757; }
  .log-line.hdr { color: #f2c94c; }

  /* GUIDE */
  .guide-body { padding: 10px 12px; overflow-y: auto; flex: 1; }
  .g-head { font-family: monospace; font-size: 0.7rem; font-weight: 700;
    color: var(--accent); margin-top: 8px; }
  .g-head:first-child { margin-top: 0; }
  .g-code { font-family: monospace; font-size: 0.68rem; color: var(--ink-mid);
    background: var(--cream2); padding: 5px 8px; border-radius: 3px;
    white-space: pre; margin-top: 3px; line-height: 1.6; }

  .spinner { display: inline-block; width: 13px; height: 13px;
    border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
    border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 700px) {
    .layout { grid-template-columns: 1fr; height: auto; }
    .hdr-sub { display: none; }
  }
</style>
</head>
<body>

<header>
  <div class="hdr-stripe"></div>
  <div class="hdr-inner">
    <span class="hdr-title">MathTest Builder</span>
    <span class="hdr-sub">— typeset maths assessments from plain text</span>
  </div>
</header>
<div class="accent-bar"></div>

<div class="layout">

  <!-- LEFT: editor + images tabs -->
  <div class="left panel">
    <div class="panel-hdr">
      <div class="badge">1</div>
      <span class="panel-hdr-title">Test content</span>
    </div>

    <div class="title-row">
      <label>Title —</label>
      <input class="title-input" id="test-title" type="text"
             placeholder="Year 9 Algebra Test" value="Year 9 Algebra Test"/>
    </div>

    <div class="tabs">
      <div class="tab active" onclick="switchTab('text')">Type / paste</div>
      <div class="tab" onclick="switchTab('file')">Upload .docx</div>
      <div class="tab" onclick="switchTab('images')">Images <span id="img-badge"></span></div>
    </div>

    <!-- Text pane -->
    <div class="pane active" id="pane-text">
      <textarea id="text-input" spellcheck="false" placeholder="Start typing your test...">Equations

Solve 3x + 5 = 17
Marks: 2
Time: 2
Space: 3cm

Factorise x^2 + 5x + 6
Marks: 3
Time: 3
Space: 4cm

Expand:
(a) (x+2)(x+3)
(b) (x-1)^2
(c) 2x(x+5)
Marks: 6
Time: 4
Space: 3cm

Multiple Choice

Which is the correct factorisation of x^2 + 5x + 6?
A  (x+1)(x+6)
B  (x+2)(x+3)
C  (x-2)(x-3)
D  (x+6)(x-1)
Marks: 1
Time: 1</textarea>
    </div>

    <!-- File pane -->
    <div class="pane" id="pane-file">
      <div class="drop-zone" id="drop-zone"
           onclick="document.getElementById('file-input').click()"
           ondragover="ev(event,'over',true)" ondragleave="ev(event,'over',false)"
           ondrop="onDrop(event)">
        <div class="drop-icon">📄</div>
        <div class="drop-label">Drop your .docx here</div>
        <div class="drop-sub">or click to browse</div>
        <div class="drop-file" id="drop-file"></div>
      </div>
      <input type="file" id="file-input" accept=".docx" onchange="onFileSelect(event)"/>
    </div>

    <!-- Images pane -->
    <div class="pane" id="pane-images">
      <div class="img-pane">
        <button class="img-add-btn"
                onclick="document.getElementById('img-file-input').click()">
          + Add images
        </button>
        <input type="file" id="img-file-input" multiple
               accept=".png,.jpg,.jpeg,.pdf,.eps"
               onchange="onImgSelect(event)"/>
        <div class="img-note">
          Add any images referenced in your test with <code>Image: filename.png</code>
        </div>
        <div class="img-list" id="img-list">
          <div class="img-empty" id="img-empty">No images added yet</div>
        </div>
      </div>
    </div>

    <div class="hint-bar">
      <span>Keywords:</span>
      <span class="chip">Marks: N</span>
      <span class="chip">Time: N</span>
      <span class="chip">Space: Xcm</span>
      <span class="chip">Image: file.png</span>
      <span class="chip">(a) sub-part</span>
      <span class="chip">A  option</span>
    </div>
  </div>

  <!-- RIGHT column -->
  <div class="right">

    <!-- Generate -->
    <div class="panel" style="flex-shrink:0">
      <div class="panel-hdr">
        <div class="badge">2</div>
        <span class="panel-hdr-title">Generate PDF</span>
      </div>
      <div class="gen-inner">
        <button class="gen-btn" id="gen-btn" onclick="generate()">
          Generate test PDF
        </button>
        <a class="dl-btn" id="dl-btn" href="#" download>
          ⬇ Download PDF
        </a>
      </div>
    </div>

    <!-- Log -->
    <div class="panel log-panel">
      <div class="panel-hdr">
        <div class="badge">↓</div>
        <span class="panel-hdr-title">Build log</span>
      </div>
      <div class="log-body" id="log-body"></div>
    </div>

    <!-- Guide -->
    <div class="panel" style="flex-shrink:0">
      <div class="panel-hdr">
        <div class="badge">?</div>
        <span class="panel-hdr-title">Format reference</span>
      </div>
      <div class="guide-body">
        <div class="g-head">SECTION</div>
        <div class="g-code">Algebra

Next question...</div>
        <div class="g-head">SINGLE QUESTION</div>
        <div class="g-code">Solve 3x + 5 = 17
Marks: 2  Time: 2  Space: 3cm</div>
        <div class="g-head">MULTI-PART</div>
        <div class="g-code">Expand:
(a) (x+2)(x+3)
(b) (x-1)^2
Marks: 4  Space: 3cm</div>
        <div class="g-head">MULTIPLE CHOICE</div>
        <div class="g-code">Which is correct?
A  option one
B  option two
C  option three
D  option four
Marks: 1</div>
        <div class="g-head">WITH IMAGE</div>
        <div class="g-code">Find the gradient.
Image: graph.png
Marks: 2  Space: 3cm</div>
      </div>
    </div>

  </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────────────────────
let docxFile  = null;
let imgFiles  = {};   // name -> File object

// ── Tabs ───────────────────────────────────────────────────────────────────
function switchTab(key) {
  document.querySelectorAll('.tab').forEach((t, i) => {
    const keys = ['text', 'file', 'images'];
    t.classList.toggle('active', keys[i] === key);
  });
  document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
  document.getElementById('pane-' + key).classList.add('active');
}

// ── Drag helpers ───────────────────────────────────────────────────────────
function ev(e, cls, add) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.toggle(cls, add);
}

function onDrop(e) {
  e.preventDefault();
  ev(e, 'over', false);
  const f = e.dataTransfer.files[0];
  if (f && f.name.endsWith('.docx')) setDocx(f);
}

function onFileSelect(e) {
  if (e.target.files[0]) setDocx(e.target.files[0]);
}

function setDocx(f) {
  docxFile = f;
  document.getElementById('drop-file').textContent = '✓ ' + f.name;
}

// ── Image management ───────────────────────────────────────────────────────
function onImgSelect(e) {
  for (const f of e.target.files) imgFiles[f.name] = f;
  renderImgList();
}

function removeImg(name) {
  delete imgFiles[name];
  renderImgList();
}

function renderImgList() {
  const list  = document.getElementById('img-list');
  const empty = document.getElementById('img-empty');
  const badge = document.getElementById('img-badge');
  const names = Object.keys(imgFiles);
  badge.textContent = names.length ? ` (${names.length})` : '';
  if (!names.length) {
    list.innerHTML = '<div class="img-empty" id="img-empty">No images added yet</div>';
    return;
  }
  list.innerHTML = names.map(n =>
    `<div class="img-item">
       <span>${n}</span>
       <button class="img-remove" onclick="removeImg('${n}')" title="Remove">✕</button>
     </div>`
  ).join('');
}

// ── Logging ────────────────────────────────────────────────────────────────
function log(msg, cls = '') {
  const body = document.getElementById('log-body');
  const d = document.createElement('div');
  d.className = 'log-line ' + cls;
  d.textContent = msg;
  body.appendChild(d);
  body.scrollTop = body.scrollHeight;
}

function clearLog() {
  document.getElementById('log-body').innerHTML = '';
}

// ── Generate ───────────────────────────────────────────────────────────────
async function generate() {
  const btn    = document.getElementById('gen-btn');
  const dlBtn  = document.getElementById('dl-btn');
  const title  = document.getElementById('test-title').value.trim() || 'Mathematics Test';
  const active = document.querySelector('.tab.active').textContent.trim();

  clearLog();
  dlBtn.classList.remove('visible');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Building…';

  const fd = new FormData();
  fd.append('title', title);

  if (active.startsWith('Upload')) {
    if (!docxFile) { log('No .docx file selected.', 'err'); reset(btn); return; }
    fd.append('docx', docxFile);
  } else {
    const text = document.getElementById('text-input').value.trim();
    if (!text) { log('Editor is empty.', 'err'); reset(btn); return; }
    fd.append('text', text);
  }

  for (const [name, file] of Object.entries(imgFiles)) {
    fd.append('images', file, name);
  }

  log('→ Parsing content…', 'hdr');

  try {
    const resp = await fetch('/generate', { method: 'POST', body: fd });
    const data = await resp.json();

    if (!resp.ok || !data.ok) {
      log('✗ ' + (data.error || 'Unknown error'), 'err');
    } else {
      log(`✓ ${data.num_questions} question(s) in ${data.num_sections} section(s)`, 'ok');
      log('✓ LaTeX generated', 'ok');
      log('✓ PDF compiled', 'ok');
      const safe = title.replace(/\s+/g, '_');
      dlBtn.href     = '/download/' + data.filename;
      dlBtn.download = safe + '.pdf';
      dlBtn.classList.add('visible');
    }
  } catch (err) {
    log('✗ Network error: ' + err.message, 'err');
  }

  reset(btn);
}

function reset(btn) {
  btn.disabled = false;
  btn.textContent = 'Generate test PDF';
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/generate", methods=["POST"])
def generate():
    try:
        title = request.form.get("title", "Mathematics Test")

        # Parse questions
        if "docx" in request.files:
            f = request.files["docx"]
            tmp = tempfile.mkdtemp()
            p = os.path.join(tmp, "input.docx")
            f.save(p)
            questions = parse_docx(p)
            shutil.rmtree(tmp)
        else:
            text = request.form.get("text", "")
            questions = parse_text_input(text)

        n_sections  = sum(1 for q in questions if isinstance(q, Section))
        n_questions = sum(1 for q in questions if not isinstance(q, Section))

        # Build LaTeX
        latex = build_latex_test(questions, title=title)

        # Collect uploaded images
        images = {}
        for f in request.files.getlist("images"):
            if f.filename:
                images[f.filename] = f

        # Compile
        pdf_bytes = compile_pdf(latex, images)

        # Save for download
        import uuid
        filename = str(uuid.uuid4()) + ".pdf"
        out_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)

        return jsonify(
            ok=True,
            filename=filename,
            num_questions=n_questions,
            num_sections=n_sections,
        )

    except Exception as e:
        import traceback
        return jsonify(ok=False, error=str(e)), 500


@app.route("/download/<filename>")
def download(filename):
    safe = Path(filename).name
    path = os.path.join(UPLOAD_FOLDER, safe)
    if not os.path.exists(path):
        return "Not found", 404
    return send_file(path, mimetype="application/pdf",
                     as_attachment=True, download_name=safe)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
