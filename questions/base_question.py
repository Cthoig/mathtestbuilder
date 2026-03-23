class BaseQuestion:
    marks         = 1
    time_estimate = 1
    working_space = "3cm"
    image         = None   # filename in images/ folder, or None

    def generate(self):
        raise NotImplementedError

    def question_latex(self):
        raise NotImplementedError