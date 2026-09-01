import sys
import threading

from PyQt6.QtWidgets import QApplication

from gui.window.agent_chat_window import AgentWindowChat

def backend_listener():


def main():
    app = QApplication(sys.argv)
    # GUI START
    window = AgentWindowChat()
    window.show()

    # BRIDGE START
    agentThread = threading.Thread(target=backend_listener, daemon=True)
    agentThread.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()