import logging
import os.path
import sys
import threading

from PyQt6.QtWidgets import QApplication

from gui.agent_starter import AgentConnector
from gui.window.agent_chat_window import AgentWindowChat

def main():
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('gui_chat.log')
        ]
    )
    
    app = QApplication(sys.argv)

    # CHOSE DOCKER OR SUBPROCESS

    # AGENT START
    try:
        agent = AgentConnector(
            port=9999,
            backend_mode='subprocess'
        )
        
        # Запускаем агент
        agent_started = agent.start_agent_app()
        if not agent_started:
            logging.error('[FRONT] Failed to start agent.')
            raise RuntimeError('Failed to start agent')
        
        # Устанавливаем соединение
        connection_success = agent.create_connection()
        if connection_success:
            # GUI START
            window = AgentWindowChat(agent)
            window.show()
        else:
            logging.error('[FRONT] Connection to agent failed.')
            raise ConnectionError('Connection failed')
            
    except Exception as e:
        logging.error(f'[FRONT] Fatal error: {e}', exc_info=True)

    sys.exit(app.exec())



if __name__ == "__main__":
    main()