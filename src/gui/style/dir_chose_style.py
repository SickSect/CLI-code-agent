# src/gui/directory_dialog_style.py

DIRECTORY_DIALOG_STYLE = """
/* ===== ОСНОВНЫЕ ЦВЕТА DRACULA ===== */
/* Фон: #282a36, #1e1f29 */
/* Токены: #f8f8f2, #6272a4, #bd93f9 */
/* Акцент: #6272a4 (ирисово-серый) */

QDialog {
    background-color: #1e1f29;
    color: #f8f8f2;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* Заголовок окна */
QDialog QLabel#infoLabel {
    color: #f8f8f2;
    font-size: 14px;
    padding: 8px;
    background-color: transparent;
    border: none;
}

/* Поле ввода */
QDialog QLineEdit#dirInput {
    background-color: #282a36;
    color: #f8f8f2;
    border: 2px solid #44475a;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-family: 'Segoe UI', Arial, sans-serif;
    selection-background-color: #6272a4;
    selection-color: #f8f8f2;
    height: 20px;
}

QDialog QLineEdit#dirInput:focus {
    border: 2px solid #6272a4;
    background-color: #2a2c3a;
}

QDialog QLineEdit#dirInput::placeholder {
    color: #6272a4;
    font-style: italic;
}

/* Кнопки */
QDialog QPushButton {
    background-color: #44475a;
    color: #f8f8f2;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-family: 'Segoe UI', Arial, sans-serif;
    min-width: 80px;
    transition: background-color 0.3s ease, transform 0.2s ease;
}

QDialog QPushButton:hover {
    background-color: #6272a4;
    transform: translateY(-1px);
}

QDialog QPushButton:pressed {
    background-color: #44475a;
    transform: translateY(0px);
}

/* Специальный стиль для кнопки "Обзор" */
QDialog QPushButton#browseBtn {
    background-color: #282a36;
    border: 2px solid #44475a;
}

QDialog QPushButton#browseBtn:hover {
    background-color: #6272a4;
    border-color: #6272a4;
}

/* Специальный стиль для кнопки "Создать новую" */
QDialog QPushButton#createBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6272a4, stop:1 #bd93f9);
    color: #f8f8f2;
    font-weight: 700;
}

QDialog QPushButton#createBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6e7db8, stop:1 #c9a5fa);
    transform: translateY(-2px);
}

QDialog QPushButton#createBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #505f8c, stop:1 #8b6fc4);
    transform: translateY(0px);
}

/* Кнопки OK/Cancel */
QDialog QPushButton[text="OK"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #50fa7b, stop:1 #69dba0);
    color: #1e1f29;
    font-weight: 700;
}

QDialog QPushButton[text="OK"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5ffa8b, stop:1 #7adbaa);
    transform: translateY(-2px);
}

QDialog QPushButton[text="OK"]:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3ad06a, stop:1 #59cba0);
}

QDialog QPushButton[text="Cancel"] {
    background-color: #44475a;
    color: #f8f8f2;
}

QDialog QPushButton[text="Cancel"]:hover {
    background-color: #ff5555;
    color: #f8f8f2;
}

/* Кнопка закрытия окна (X) */
QDialog QPushButton#closeBtn {
    background-color: transparent;
    color: #6272a4;
    min-width: 30px;
    padding: 4px;
    font-size: 16px;
}

QDialog QPushButton#closeBtn:hover {
    background-color: #ff5555;
    color: #f8f8f2;
}

/* Контейнер для кнопок */
QDialog QDialogButtonBox {
    background-color: transparent;
    border: none;
    padding: 8px 0;
}

QDialog QDialogButtonBox QPushButton {
    min-width: 100px;
    padding: 10px 20px;
}

/* Анимация появления */
QDialog {
    animation: fadeIn 0.3s ease;
}
"""

def get_directory_dialog_style():
    """Возвращает стиль для диалога выбора директории"""
    return DIRECTORY_DIALOG_STYLE