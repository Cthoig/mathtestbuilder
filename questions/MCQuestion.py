from questions.base_question import BaseQuestion


class MCQuestion(BaseQuestion):

    def __init__(self, text, options, marks=1, time_estimate=1, image=None):
        """
        text         : str        — the question prompt
        options      : list[str]  — exactly 4 strings, e.g.
                                    ["A  3x", "B  5x", "C  7x", "D  9x"]
        marks        : int
        time_estimate: int
        image        : str|None   — filename in images/ folder, or None
        """
        self.text          = text
        self.options       = options
        self.marks         = marks
        self.time_estimate = time_estimate
        self.image         = image

    def generate(self):
        pass

    def question_latex(self):
        return self.text
