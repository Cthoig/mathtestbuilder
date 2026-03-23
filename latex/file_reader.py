from docx import Document
from questions.custom_question import CustomQuestion
from questions.section import Section
from questions.MultiPartQuestion import MultiPartQuestion
from questions.MCQuestion import MCQuestion


# -------------------------
# METADATA PREFIXES
# -------------------------
_META_PREFIXES = ("marks", "time", "space", "image")


def _is_metadata(line):
    return any(line.lower().startswith(p) for p in _META_PREFIXES)


def _is_part_label(line):
    """Return True for sub-part labels like (a), (b), (c)."""
    return line.startswith("(") and ")" in line[:4]


def _is_mc_option(line):
    """
    Return True if the line is a MC option.
    Accepts:  A  text,  A. text,  A) text  (case-insensitive)
    """
    if len(line) < 2:
        return False
    first  = line[0].upper()
    second = line[1]
    return first in ("A", "B", "C", "D") and second in (" ", ".", ")")


# -------------------------
# BLOCK PROCESSOR
# -------------------------
def process_block(block):
    if not block:
        return None

    q_lines    = []
    parts      = []
    mc_options = []

    marks = 1
    time  = 1
    space = "3cm"
    image = None

    for line in block:
        lower = line.lower()

        if lower.startswith("marks"):
            try:
                marks = int(line.split(":")[1].strip())
            except (IndexError, ValueError):
                pass

        elif lower.startswith("time"):
            try:
                time = int(line.split(":")[1].strip())
            except (IndexError, ValueError):
                pass

        elif lower.startswith("space"):
            try:
                space = line.split(":")[1].strip()
            except IndexError:
                pass

        elif lower.startswith("image"):
            try:
                image = line.split(":", 1)[1].strip()
            except IndexError:
                pass

        elif _is_mc_option(line):
            mc_options.append(line.strip())

        elif _is_part_label(line):
            label_end = line.index(")")
            label = line[: label_end + 1]
            text  = line[label_end + 1 :].strip()
            parts.append((label, text))

        else:
            q_lines.append(line.strip())

    prompt = " ".join(q_lines).rstrip(":").strip()

    # ---- MULTIPLE CHOICE ----
    if mc_options:
        return MCQuestion(
            text=prompt,
            options=mc_options,
            marks=marks,
            time_estimate=time,
            image=image,
        )

    # ---- MULTI-PART ----
    if parts:
        num_parts      = len(parts)
        marks_per_part = max(1, marks // num_parts)
        parsed_parts = [
            {"label": label, "text": text,
             "marks": marks_per_part, "space": space}
            for label, text in parts
        ]
        return MultiPartQuestion(
            prompt, parts=parsed_parts,
            marks=marks, time_estimate=time, image=image,
        )

    # ---- SINGLE ----
    if not q_lines:
        return None

    return CustomQuestion(
        prompt, marks=marks, working_space=space,
        time_estimate=time, image=image,
    )


# -------------------------
# SECTION DETECTION
# -------------------------
def _looks_like_section(line, next_line):
    if _is_metadata(line):
        return False
    if _is_part_label(line):
        return False
    if _is_mc_option(line):
        return False
    return next_line == ""


# -------------------------
# DOCX PARSER
# -------------------------
def parse_docx(filepath):
    """
    Read a .docx and return a list of Section/Question objects.

    Supported block formats in the Word doc
    ----------------------------------------
    Section heading          (standalone line followed by blank)

    Single question
      Question text
      Image: filename.png    (optional)
      Marks: N  |  Time: N  |  Space: Xcm

    Multiple choice
      Question text
      Image: filename.png    (optional)
      A  option one
      B  option two
      C  option three
      D  option four
      Marks: 1

    Multi-part
      Prompt text
      Image: filename.png    (optional)
      (a) first part
      (b) second part
      Marks: N  |  Space: Xcm
    """
    doc   = Document(filepath)
    lines = [p.text.strip() for p in doc.paragraphs]
    lines.append("")   # sentinel

    questions = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if line == "":
            i += 1
            continue

        next_line = lines[i + 1] if i + 1 < len(lines) else ""

        if _looks_like_section(line, next_line):
            questions.append(Section(line))
            i += 1
            continue

        current_block = []
        while i < len(lines) and lines[i] != "":
            current_block.append(lines[i])
            i += 1

        q = process_block(current_block)
        if q:
            questions.append(q)

    return questions
