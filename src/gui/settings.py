from PyQt6.QtCore import QSettings


class GuiSettings:
    def __init__(self, working_dir: str,
                 backend_mode: str = 'subprocess',
                 port: int = 9999):
        self.working_dir = working_dir
        self.backend_mode = backend_mode
        self.port = port
