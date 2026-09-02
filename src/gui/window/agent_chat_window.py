import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.agent_starter import AgentConnector
from gui.style.style import get_theme


# Если запускаешь напрямую как скрипт, возможно придется использовать: from style import get_theme

class AgentWindowChat(QMainWindow):
    def __init__(self, agent: AgentConnector):
        super().__init__()

        self.agent = agent

        # --- Настройка окна ---
        self.setWindowTitle("AI Code Agent")
        self.setGeometry(100, 100, 900, 700)

        # --- Применение стилей ---
        # Берем строку CSS из файла style.py и применяем ко всему окну
        self.setStyleSheet(get_theme("dark"))

        # --- Центральный виджет и лейаут ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        central_widget.setLayout(layout)

        # --- Область чата ---
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setPlaceholderText("Ожидание задачи...")
        layout.addWidget(self.chat_area, stretch=1)

        # --- Поле ввода ---
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите задачу и нажмите Enter...")
        layout.addWidget(self.input_field)

        # --- Кнопка отправки ---
        self.send_button = QPushButton("Отправить")
        layout.addWidget(self.send_button)

        # --- Подключение событий ---
        self.input_field.returnPressed.connect(self.send_command)
        self.send_button.clicked.connect(self.send_command)

        # Приветственное сообщение
        self.append_to_chat("<b>Система:</b> Интерфейс готов к работе.", is_system=True)

    def send_command(self):
        text = self.input_field.text().strip()
        if not text:
            return

        # Сообщение пользователя - справа
        self.append_to_chat(
            f"<div align='right' style='background: #1e3a5f; padding: 8px 12px; border-radius: 12px; margin: 4px 0; color: #4fc3f7;'>"
            f"<b>Вы:</b> {text}</div>"
        )
        self.input_field.clear()

        response = self.agent.send_msg(text)

        # Ответ агента - слева
        self.append_to_chat(
            f"<div align='left' style='background: #2d2d2d; padding: 8px 12px; border-radius: 12px; margin: 4px 0; color: #e0e0e0;'>"
            f"<b>Агент:</b> {response}</div>"
        )


    def append_to_chat(self, message, is_system=False):
        self.chat_area.append(message)
        # Автопрокрутка вниз
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
