"""
Этап 1: Простое окно на PyQt6
Учимся создавать базовое приложение
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    """Наше главное окно приложения"""
    
    def __init__(self):
        # Вызываем конструктор родительского класса
        super().__init__()
        
        # Настраиваем окно
        self.setWindowTitle("AI Code Agent")  # Заголовок окна
        self.setGeometry(100, 100, 800, 600)  # x, y, ширина, высота
        
        # Показываем окно
        self.show()


if __name__ == "__main__":
    # 1. Создаём приложение
    app = QApplication(sys.argv)
    
    # 2. Создаём главное окно
    window = MainWindow()
    
    # 3. Запускаем цикл обработки событий
    # (ждёт действий пользователя: клики, ввод текста и т.д.)
    sys.exit(app.exec())
