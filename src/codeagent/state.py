from typing import Optional


class AgentState:
    def __init__(self, max_iterations: Optional[int] = 5):
        self.task = None
        self.plan = None
        self.code = None
        self.test_results = None
        self.review = None
        self.iteration = 0
        self.max_iterations = max_iterations
        self.done = False

    def set_task(self, task: str):
        self.task = task

    def increment(self):
        if self.iteration >= self.max_iterations:
            self.done = True
            return False
        self.iteration += 1
        return True

    def set_code(self, code: str):
        self.code = code

    def set_test_results(self, test_results: str):
        self.test_results = test_results

    def set_review(self, review: str):
        self.review = review

    def set_plan(self, plan: str):
        self.plan = plan

    def set_done(self, done: bool):
        self.done = done

    def set_plan(self, plan: str):
        self.plan = plan

    def set_role(self, role: str):
        self.role = role
