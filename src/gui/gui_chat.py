import logging
import os.path
import sys
import threading

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from gui.agent_starter import AgentConnector
from gui.settings import GuiSettings
from gui.window.agent_chat_window import AgentWindowChat
from gui.window.dir_selection_window import DirectorySelectionDialog


def main():
    app = QApplication(sys.argv)

    # CHOSE DOCKER OR SUBPROCESS

    # AGENT START
    try:
        # DIR SELECTION
        # Показываем диалог выбора директории
        dir_dialog = DirectorySelectionDialog()
        if dir_dialog.exec() == QDialog.DialogCode.Accepted:
            working_dir = dir_dialog.get_directory()
            if not working_dir:
                QMessageBox.warning(None, "ERROR", "Directory selection failed!")
                sys.exit(1)

            # Проверяем доступность директории
            if not os.path.exists(working_dir):
                try:
                    os.makedirs(working_dir, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(None, "ERROR", f"Could not chose directory:\n{str(e)}")
                    sys.exit(1)

            # Сохраняем в настройках
            settings = QSettings('MyCompany', 'CodeAgent')
            gui_settings = GuiSettings(working_dir,
                                      'subprocess',
                                      port=9999)
        else:
            sys.exit(1)
        agent = AgentConnector(
            port=gui_settings.port,
            backend_mode=gui_settings.backend_mode
        )
        connection_success = agent.start_agent_app()
        if connection_success:
            # GUI START
            agent.create_connection(10)
            window = AgentWindowChat(agent)
            window.show()

        else:
            raise ConnectionError('Connection failed')
    except Exception as e:
        logging.error(e)

    sys.exit(app.exec())



if __name__ == "__main__":
    main()