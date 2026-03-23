from questions.section import Section
from questions.MultiPartQuestion import MultiPartQuestion
from questions.MCQuestion import MCQuestion



# -------------------------
# TEXT SANITISER
# -------------------------
def sanitise(text):
    """
    Escape LaTeX special characters in plain-text portions of question text,
    while leaving $...$ inline maths and \\command sequences untouched.

    Users write:  What is the gradient of $y=3x^2$ at $x=1$?
    LaTeX gets:   What is the gradient of $y=3x^2$ at $x=1$?  (no change needed)

    Users write:  Cost is $50 & profit is 10%
    LaTeX gets:   Cost is \$50 \& profit is 10\%

    Characters escaped outside maths: & % # _ { } ~ ^
    Characters NOT escaped: $ (maths delimiter), \\ (already a command)
    """
    import re
    result = []
    # Split on $...$ blocks, alternating plain/maths
    parts = re.split(r'(\$[^$]*\$)', text)
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Inside $...$ — pass through unchanged
            result.append(part)
        else:
            # Plain text — escape special chars (but not backslash, already commands)
            part = part.replace('&',  r'\&')
            part = part.replace('%',  r'\%')
            part = part.replace('#',  r'\#')
            part = part.replace('_',  r'\_')
            part = part.replace('{',  r'\{')
            part = part.replace('}',  r'\}')
            part = part.replace('~',  r'\textasciitilde{}')
            part = part.replace('^',  r'\textasciicircum{}')
            result.append(part)
    return ''.join(result)


# -------------------------
# WORKING LINES (top-level)
# -------------------------
def generate_working_lines(space):
    """Ruled working lines at top-level (full text width)."""
    try:
        cm = float(space.replace("cm", ""))
    except ValueError:
        cm = 3
    num_lines = max(1, int(cm / 0.7))
    latex = r"\vspace{0.4cm}" + "\n"
    for _ in range(num_lines):
        latex += r"\noindent\rule{\textwidth}{0.5pt}\par\vspace{0.5cm}" + "\n"
    latex += r"\vspace{0.2cm}" + "\n"
    return latex


# -------------------------
# WORKING LINES (nested)
# -------------------------
def generate_working_lines_fullwidth(space):
    """Working lines inside a nested enumerate, always full text width."""
    try:
        cm = float(space.replace("cm", ""))
    except ValueError:
        cm = 3
    num_lines = max(1, int(cm / 0.7))
    # No leading \vspace here — spacing is controlled by the caller
    # so that all lines (first and subsequent) are evenly spaced.
    latex = ""
    for _ in range(num_lines):
        latex += (
            r"\noindent\hspace*{-\leftskip}"
            r"\rule{\textwidth}{0.5pt}\par\vspace{0.5cm}" + "\n"
        )
    latex += r"\vspace{0.2cm}" + "\n"
    return latex


# -------------------------
# QUESTION HEADER LINE
# -------------------------
def render_question_header(text, marks):
    """
    Render  "text  [marks]"  on one line with marks pinned to the
    right margin regardless of enumerate indentation.

    Uses makebox[textwidth] anchored with a negative hspace to
    break out of the enumerate indent — same trick as the working lines.
    Keeps the question number on the same line as the text.
    """
    return (
        "\\leavevmode\n"
        f"\\hspace*{{-\\leftskip}}\\makebox[\\textwidth][l]{{{sanitise(text)} \\hfill [{marks}]}}\\par\n"
    )


# -------------------------
# IMAGE BLOCK
# -------------------------
def render_image(filename, width="8cm"):
    """Centred image block. Images live in images/ next to the .tex file."""
    return (
        r"\begin{center}" + "\n"
        rf"  \includegraphics[width={width}]{{images/{filename}}}" + "\n"
        r"\end{center}" + "\n"
        r"\vspace{0.2cm}" + "\n"
    )


# -------------------------
# SAMEPAGE WRAPPER
# -------------------------
def nobreak(content):
    """
    Prepend \\filbreak so LaTeX starts a new page if the question
    does not fit, rather than splitting it mid-way.
    Works reliably inside list environments (unlike samepage/minipage).
    """
    return "\\filbreak\n" + content


# -------------------------
# SPACE ESTIMATION
# -------------------------
def estimate_total_space(space):
    try:
        cm = float(space.replace("cm", ""))
    except ValueError:
        cm = 3
    return cm + 1.8


# -------------------------
# SECTION MARKS
# -------------------------
def calculate_section_marks(questions):
    sections = []
    current_section = None
    current_marks   = 0
    for q in questions:
        if isinstance(q, Section):
            if current_section is not None:
                sections.append((current_section, current_marks))
            current_section = q.title
            current_marks   = 0
        else:
            current_marks += getattr(q, "marks", 0)
    if current_section is not None:
        sections.append((current_section, current_marks))
    return sections


# -------------------------
# MULTI-PART RENDERER
# -------------------------
def render_multipart_question(q):
    """
    Layout:
      N.  Prompt text                              [total marks]
          [image if present]
          (a) part text                            [part marks]
              ___ working lines ___
          (b) ...
    """
    prompt = q.question_latex().strip()

    body = ""

    # 1. Question header (number + text + marks on one clean line)
    if prompt:
        body += "\\item " + render_question_header(prompt, q.marks)
    else:
        body += f"\\item \\hfill [{q.marks}]\n"
    body += r"\par\vspace{0.2cm}" + "\n"

    # 2. Image
    if getattr(q, "image", None):
        body += render_image(q.image)

    # 3. Sub-parts
    body += "\\begin{enumerate}[(a)]\n"
    for part in q.parts:
        text  = part.get("text", "")
        marks = part.get("marks", 1)
        space = part.get("space", "3cm")
        body += "  \\item " + render_question_header(text, marks)
        body += r"\vspace{0.4cm}" + "\n"   # consistent gap before ALL working lines
        body += generate_working_lines_fullwidth(space)
    body += "\\end{enumerate}\n"

    return nobreak(body)


# -------------------------
# MC RENDERER
# -------------------------
def render_mc_question(q):
    """
    Layout:
      N.  Question text                            [marks]
          [image if present]
          A  ...    C  ...
          B  ...    D  ...
    """
    marks = getattr(q, "marks", 1)

    body = ""

    # 1. Question header
    body += "\\item " + render_question_header(q.question_latex(), marks)
    body += r"\par\vspace{0.3cm}" + "\n"

    # 2. Image
    if getattr(q, "image", None):
        body += render_image(q.image)

    # 3. Options — 2-column table (A/C left, B/D right)
    options = list(q.options)
    while len(options) < 4:
        options.append("")

    body += (
        r"\begin{tabular}{p{0.45\linewidth}p{0.45\linewidth}}" + "\n"
        f"  {options[0]} & {options[2]} \\\\\n"
        f"  {options[1]} & {options[3]} \\\\\n"
        r"\end{tabular}" + "\n"
        r"\par\vspace{0.4cm}" + "\n"
    )

    return nobreak(body)


# -------------------------
# LATEX BUILDER
# -------------------------
def build_latex_test(questions, title="Mathematics Test", school_name="", has_logo=False):

    total_marks   = sum(getattr(q, "marks", 0) for q in questions)
    total_time    = sum(getattr(q, "time_estimate", 0) for q in questions)
    section_marks = calculate_section_marks(questions)


    logo_block = "\\includegraphics[width=4cm]{logo.png}\n\n\\vspace{0.5cm}\n" if has_logo else ""
    school_block = ("\\LARGE \\textbf{" + school_name.replace("&", "\\&") + "}\n\n\\vspace{0.5cm}\n") if school_name else ""
    latex = rf"""
\documentclass[12pt]{{article}}

\usepackage{{amsmath}}
\usepackage{{needspace}}
\usepackage{{graphicx}}
\usepackage{{array}}
\usepackage{{enumerate}}

\setlength{{\parindent}}{{0pt}}

\begin{{document}}

% =========================
% TITLE PAGE
% =========================

\begin{{center}}

{logo_block}

\vspace{{0.5cm}}

{school_block}

\vspace{{0.5cm}}

\Huge \textbf{{{title}}}

\vspace{{0.5cm}}

\large

Teacher:\hspace{{0.5cm}}\rule{{6cm}}{{0.4pt}}

\vspace{{0.5cm}}

Student Name:\hspace{{0.5cm}}\rule{{6cm}}{{0.4pt}}

\vspace{{1cm}}

\end{{center}}

\textbf{{Total Marks:}} {total_marks} \\
\textbf{{Estimated Time:}} {total_time} minutes

\vspace{{1cm}}

\textbf{{Marks Breakdown}}

\vspace{{0.3cm}}

\begin{{tabular}}{{|p{{8cm}}|c|}}
\hline
\textbf{{Section}} & \textbf{{Marks}} \\
\hline
"""

    for name, marks in section_marks:
        latex += f"{name} & {marks} \\\\\n\\hline\n"

    latex += rf"""
\textbf{{Total}} & \textbf{{{total_marks}}} \\
\hline
\end{{tabular}}

\vfill

\textit{{Show all working. Give exact answers where appropriate.}}

\newpage
"""

    # =========================
    # QUESTIONS
    # =========================

    enumerate_open = False

    for q in questions:

        # ---- SECTION HEADING ----
        if isinstance(q, Section):
            if enumerate_open:
                latex += "\\end{enumerate}\n"
                enumerate_open = False
            latex += r"\Needspace{4cm}" + "\n"
            latex += f"\n{{\\large \\textbf{{{q.title}}}}}\n\\vspace{{0.4cm}}\n"
            continue

        if not enumerate_open:
            latex += "\\begin{enumerate}\n"
            enumerate_open = True

        # ---- MULTI-PART ----
        if isinstance(q, MultiPartQuestion):
            latex += render_multipart_question(q)
            continue

        # ---- MULTIPLE CHOICE ----
        if isinstance(q, MCQuestion):
            latex += render_mc_question(q)
            continue

        # ---- SINGLE QUESTION ----
        marks = getattr(q, "marks", 0)
        space = getattr(q, "working_space", "3cm")

        body  = ""
        body += "\\item " + render_question_header(q.question_latex(), marks)
        body += r"\par\vspace{0.2cm}" + "\n"

        if getattr(q, "image", None):
            body += render_image(q.image)

        body += generate_working_lines(space)

        latex += nobreak(body)

    if enumerate_open:
        latex += "\\end{enumerate}\n"

    latex += "\n\\end{document}\n"
    return latex
