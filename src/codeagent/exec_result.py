"""Shared result container used by the validators and the executor."""


class ExecutionResult:
    """Outcome of validating or running generated code.

    Two flags, deliberately separate:
      success   — is the code sound / did it run correctly?
      validated — were we able to check it at all?

    They differ when a toolchain is missing: the code is not broken, we simply
    could not inspect it. Reporting that as success=False would send perfectly
    good code to the fixer.
    """

    def __init__(self, success: bool, output: str = "", error: str = "",
                 returncode: int = -1, validated: bool = True):
        self.success = success        # True if the code passed / ran cleanly
        self.output = output          # Captured stdout
        self.error = error            # Captured stderr, or an explanation
        self.returncode = returncode  # Process return code (0 = success)
        self.validated = validated    # False when the check could not be run

    def __repr__(self):
        return (f"ExecutionResult(success={self.success}, "
                f"validated={self.validated}, returncode={self.returncode})")