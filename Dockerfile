# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── Install LaTeX (texlive-latex-base covers pdflatex + core packages) ────────
# texlive-latex-extra adds \needspace, \enumerate, etc.
# texlive-fonts-recommended adds standard fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ─────────────────────────────────────────────────────
COPY . .

# ── Run ──────────────────────────────────────────────────────────────────────
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "app:app"]
