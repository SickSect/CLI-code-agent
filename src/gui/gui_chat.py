import logging
import os.path
import sys
import threading

from PyQt6.QtWidgets import QApplication

from gui.agent_starter import AgentConnector
from gui.window.agent_chat_window import AgentWindowChat

def main():
    app = QApplication(sys.argv)

    # CHOSE DOCKER OR SUBPROCESS

    # AGENT START
    try:
        agent = AgentConnector(
            port=9999,
            backend_mode='subprocess'
        )
        connection_success = agent.start_agent_app()
        if connection_success:
            # GUI START
            window = AgentWindowChat(agent)
            window.show()
        else:
            raise ConnectionError('Connection failed')
    except Exception as e:
        logging.error(e)

    sys.exit(app.exec())



if __name__ == "__main__":
    main()