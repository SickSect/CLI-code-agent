# src/codeagent/logger.py
import logging
import sys
from typing import Optional


class CodeAgentLogger:
    """Simple logger wrapper with on/off switch."""

    def __init__(self, name: str = "codeagent", verbose: bool = True, log_file: Optional[str] = None):
        self.verbose = verbose
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if verbose else logging.WARNING)

        if not self.logger.handlers:
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s - %(message)s",
                datefmt="%H:%M:%S"
            )

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            if log_file:
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

    def set_verbose(self, verbose: bool):
        self.verbose = verbose
        self.logger.setLevel(logging.DEBUG if verbose else logging.WARNING)

    def info(self, msg: str):
        self.logger.info(msg)

    def debug(self, msg: str):
        if self.verbose:
            self.logger.debug(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def step(self, agent_name: str, input_summary: str = "", output_preview: str = ""):
        self.info(f"===== {agent_name.upper()} =====")
        if input_summary:
            self.debug(f"  Input: {input_summary}")
        if output_preview:
            self.info(f"  Output: {output_preview}")