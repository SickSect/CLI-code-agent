import logging
import os.path
import sys
import threading

from PyQt6.QtWidgets import QApplication

from gui.agent_starter import AgentConnector
from gui.window.agent_chat_window import AgentWindowChat

def chat_mode():
    process_flag = True



def main():
    app = QApplication(sys.argv)
    # GUI START
    window = AgentWindowChat()
    window.show()

    # CHOSE DOCKER OR SUBPROCESS

    # AGENT START
    try:
        agent = AgentConnector(
            port=9999,
            backend_mode='subprocess'
        )
        connection_success = agent.start_agent_app()
        if connection_success:
            return
        else:
            raise ConnectionError('Connection failed')
    except Exception as e:
        logging.error(e)

    # INTERACTION MODE
    chat_mode()

    # BRIDGE LISTENER START
    #agentThread = threading.Thread(target=backend_listener, daemon=True)
    #agentThread.start()

    sys.exit(app.exec())



if __name__ == "__main__":
    main()