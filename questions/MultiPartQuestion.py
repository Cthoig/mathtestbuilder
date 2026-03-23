from questions.base_question import BaseQuestion


class MultiPartQuestion(BaseQuestion):

    def __init__(self, prompt, parts, marks=0, time_estimate=0, image=None):
        """
        prompt : str   — the lead-in text, e.g. "Expand:"
        parts  : list  — each item is {"label": "(a)", "text": "...",
                                        "marks": int, "space": "3cm"}
        marks  : int   — total marks (sum of parts)
        time_estimate : int — minutes
        image  : str|None — filename in images/ folder, or None
        """
        self.text          = prompt
        self.parts         = parts
        self.marks         = marks
        self.time_estimate = time_estimate
        self.image         = image
        # working_space is not used directly for multi-part;
        # each part carries its own space. Provide a fallback so
        # BaseQuestion attribute access never crashes.
        self.working_space = parts[0]["space"] if parts else "3cm"

    def question_latex(self):
        """Return just the prompt line (used as the item text)."""
        return self.text
