from questions.base_question import BaseQuestion


class CustomQuestion(BaseQuestion):

    def __init__(self, text, marks=1, working_space="5cm", time_estimate=1,
                 image=None):
        self.text          = text
        self.marks         = marks
        self.working_space = working_space
        self.time_estimate = time_estimate
        self.image         = image


    def generate(self):
        pass

    def question_latex(self):

        return self.text