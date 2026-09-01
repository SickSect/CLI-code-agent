# src/gui/style.py

# Темная тема в современном стиле
DARK_THEME = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* Область чата и поле ввода */
QTextEdit, QLineEdit {
    background-color: #3c3f41;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 8px;
    padding: 10px;
    font-size: 14px;
    selection-background-color: #6a9955;
}

QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #6a9955;
}

/* Кнопки */
QPushButton {
    background-color: #6a9955;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 8px 15px;
    font-size: 14px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #7cb366;
}

QPushButton:pressed {
    background-color: #568045;
}

/* Скроллбары (для красоты) */
QScrollBar:vertical {
    background: #2b2b2b;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #555555;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

def get_theme(theme_name="dark"):
    """Возвращает строку стиля по имени темы"""
    if theme_name == "dark":
        return DARK_THEME
    return ""