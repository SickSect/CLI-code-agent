from typing import Optional


class AgentState:
    def __init__(self, max_iterations: Optional[int] = 5, lang: str = "python"):
        self.task = None
        self.plan = None
        self.code = None
        self.test_results = None
        self.review = None
        self.iteration = 0
        self.max_iterations = max_iterations
        self.done = False
        self.lang = lang

    def increment(self):
        if self.iteration >= self.max_iterations:
            self.done = True
            return False
        self.iteration += 1
        return True

