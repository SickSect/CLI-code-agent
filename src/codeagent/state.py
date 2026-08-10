from typing import Optional


class AgentState:
    """Everything one task produces, plus what carries over between tasks."""

    def __init__(self, max_iterations: Optional[int] = 5, lang: str = "python"):
        self.task = None
        self.plan = None
        self.code = None            # content of the entry file (convenience)
        self.test_results = None
        self.review = None
        self.iteration = 0
        self.max_iterations = max_iterations
        self.done = False
        self.lang = lang
        self.asserts = None         # generated test module source
        self.files = None           # planned files: [{path, purpose}, ...]
        self.entry = None           # file to run, e.g. "main.py"
        self.files_content = None   # produced files: {path: content}
        self.previous_files = None  # all files from the previous task (session memory)
        # True until something tells us otherwise: False means the code could
        # not be checked (no toolchain, unknown language), not that it is wrong.
        self.validated = True
        self.validation_note = None  # why validation was skipped, if it was

    def increment(self):
        if self.iteration >= self.max_iterations:
            self.done = True
            return False
        self.iteration += 1
        return True

    def leave_prev_code(self):
        """Reset for a new task, keeping the previous task's files as memory."""
        self.previous_files = self.files_content   # remember ALL files, not just entry
        self.task = None
        self.plan = None
        self.code = None
        self.test_results = None
        self.review = None
        self.iteration = 0
        self.done = False
        self.asserts = None
        self.entry = None
        self.files = None
        self.files_content = None
        self.validated = True
        self.validation_note = None