class ExecutionResult:
    """
    Container for code execution result.
    Stores success flag, stdout, stderr, and return code.
    """

    def __init__(self, success: bool, output: str = "", error: str = "", returncode: int = -1):
        self.success = success  # True if code executed without errors
        self.output = output  # Captured stdout
        self.error = error  # Captured stderr or error message
        self.returncode = returncode  # Process return code (0 = success)

    def __repr__(self):
        return f"ExecutionResult(success={self.success}, returncode={self.returncode})"
