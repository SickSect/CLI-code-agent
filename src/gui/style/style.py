# src/gui/style.py

DARK_THEME = """
/* ===== ОСНОВНЫЕ ЦВЕТА DRACULA ===== */
/* Фон: #282a36 (темно-фиолетово-серый) */
/* Токены: #f8f8f2, #50fa7b, #ffb86c, #ff79c6, #8be9fd, #bd93f9 */
/* Акцент: #6272a4 (ирисово-серый) */

QMainWindow {
    background-color: #1e1f29;
    color: #f8f8f2;
    font-family: 'Segoe UI', 'JetBrains Mono', Arial, sans-serif;
}

/* ===== ОБЛАСТЬ ЧАТА ===== */
QTextEdit#chatArea {
    background-color: #282a36;
    color: #f8f8f2;
    border: 1px solid #44475a;
    border-radius: 12px;
    padding: 16px;
    font-size: 14px;
    font-family: 'Segoe UI', Arial, sans-serif;
    selection-background-color: #44475a;
    selection-color: #f8f8f2;
}

QTextEdit#chatArea:focus {
    border: 1px solid #6272a4;
}

/* ===== ПОЛЕ ВВОДА ===== */
QLineEdit#inputField {
    background-color: #282a36;
    color: #f8f8f2;
    border: 2px solid #44475a;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px;
    font-family: 'Segoe UI', Arial, sans-serif;
    selection-background-color: #6272a4;
}

QLineEdit#inputField:focus {
    border: 2px solid #6272a4;
    background-color: #2a2c3a;
}

QLineEdit#inputField::placeholder {
    color: #6272a4;
    font-style: italic;
}

/* ===== КНОПКИ ===== */
QPushButton {
    background-color: #44475a;
    color: #f8f8f2;
    font-weight: 600;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 14px;
    font-family: 'Segoe UI', Arial, sans-serif;
    min-width: 100px;
    transition: background-color 0.3s ease, transform 0.2s ease;
}

QPushButton:hover {
    background-color: #6272a4;
    transform: translateY(-1px);
}

QPushButton:pressed {
    background-color: #44475a;
    transform: translateY(0px);
}

QPushButton:disabled {
    background-color: #3d3f4a;
    color: #6272a4;
}

/* ===== КНОПКА ОТПРАВКИ (особый стиль) ===== */
QPushButton#sendButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6272a4, stop:1 #bd93f9);
    color: #f8f8f2;
    font-weight: 700;
    border: none;
}

QPushButton#sendButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6e7db8, stop:1 #c9a5fa);
    transform: translateY(-2px);
}

QPushButton#sendButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #505f8c, stop:1 #8b6fc4);
    transform: translateY(0px);
}

/* ===== СКРОЛЛБАРЫ (Dracula style) ===== */
QScrollBar:vertical {
    background: #1e1f29;
    width: 8px;
    border-radius: 4px;
    margin: 4px 0px;
}

QScrollBar::handle:vertical {
    background: #44475a;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #6272a4;
}

QScrollBar::add-line:vertical, 
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #1e1f29;
    height: 8px;
    border-radius: 4px;
    margin: 0px 4px;
}

QScrollBar::handle:horizontal {
    background: #44475a;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #6272a4;
}

QScrollBar::add-line:horizontal, 
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== ПРОКРУТКА ВНИЗ (анимация) ===== */
QTextEdit#chatArea {
    scroll-behavior: smooth;
}

/* ===== АНИМАЦИИ ДЛЯ СООБЩЕНИЙ (через QPropertyAnimation) ===== */
/* Это будет работать только если добавить анимации в Python коде */
"""

def get_theme(theme_name="dark"):
    if theme_name == "dark":
        return DARK_THEME
    return ""