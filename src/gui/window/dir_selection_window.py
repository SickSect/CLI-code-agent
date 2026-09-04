# src/gui/directory_dialog.py

import os
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QFileDialog, QInputDialog
)

from gui.style.dir_chose_style import get_directory_dialog_style


class DirectorySelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор рабочей директории")
        self.setModal(True)
        self.setFixedSize(550, 240)

        # Применяем стили
        self.setStyleSheet(get_directory_dialog_style())

        self.setup_ui()
        self.load_last_directory()

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Информация
        self.info_label = QLabel(
            "📁 Для работы приложения необходимо выбрать рабочую директорию.\n"
            "Все созданные файлы будут сохранены в этой папке."
        )
        self.info_label.setObjectName("infoLabel")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Поле с выбранной директорией
        self.dir_input = QLineEdit()
        self.dir_input.setObjectName("dirInput")
        self.dir_input.setPlaceholderText("Путь к рабочей директории...")
        layout.addWidget(self.dir_input)

        # Кнопки выбора
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.browse_btn = QPushButton("📂 Обзор...")
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.clicked.connect(self.browse_directory)
        btn_layout.addWidget(self.browse_btn)

        self.create_btn = QPushButton("✨ Создать новую")
        self.create_btn.setObjectName("createBtn")
        self.create_btn.clicked.connect(self.create_directory)
        btn_layout.addWidget(self.create_btn)

        # Добавляем растяжение чтобы кнопки были слева
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Кнопки OK/Cancel
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Настройка кнопок
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("✅ Подтвердить")
        ok_btn.setMinimumWidth(120)

        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("❌ Отмена")
        cancel_btn.setMinimumWidth(120)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def load_last_directory(self):
        """Загружает последнюю использованную директорию из настроек"""
        settings = QSettings('MyCompany', 'CodeAgent')
        last_dir = settings.value('working_directory', '')
        if last_dir and os.path.exists(last_dir):
            self.dir_input.setText(last_dir)
        elif last_dir:
            # Если директория не существует, очищаем
            settings.remove('working_directory')

    def browse_directory(self):
        """Открывает диалог выбора существующей директории"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите рабочую директорию",
            self.dir_input.text() or os.path.expanduser('~'),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if dir_path:
            self.dir_input.setText(dir_path)
            self.validate_directory(dir_path)

    def create_directory(self):
        """Создает новую директорию"""
        base_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите место для создания папки",
            os.path.expanduser('~'),
            QFileDialog.Option.ShowDirsOnly
        )
        if base_path:
            folder_name, ok = QInputDialog.getText(
                self,
                "Новая папка",
                "Введите имя новой папки:",
                text="codeagent_project"
            )
            if ok and folder_name:
                # Очищаем имя от недопустимых символов
                import re
                folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)

                new_path = os.path.join(base_path, folder_name)
                try:
                    os.makedirs(new_path, exist_ok=True)
                    self.dir_input.setText(new_path)
                    self.validate_directory(new_path)

                    QMessageBox.information(
                        self,
                        "✅ Успешно",
                        f"Папка успешно создана:\n{new_path}"
                    )
                except PermissionError:
                    QMessageBox.critical(
                        self,
                        "❌ Ошибка",
                        f"Нет прав для создания папки:\n{new_path}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "❌ Ошибка",
                        f"Не удалось создать папку:\n{str(e)}"
                    )

    def validate_directory(self, path):
        """Проверяет доступность директории"""
        if not os.path.exists(path):
            return False

        # Проверяем права на запись
        test_file = os.path.join(path, '.test_write')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except:
            QMessageBox.warning(
                self,
                "⚠️ Предупреждение",
                f"Нет прав на запись в директорию:\n{path}\n"
                "Вы сможете просматривать файлы, но создание новых может быть недоступно."
            )
            return False

    def get_directory(self):
        """Возвращает выбранную директорию"""
        path = self.dir_input.text().strip()
        if path:
            # Нормализуем путь
            path = os.path.normpath(path)
        return path

    def accept(self):
        """Обработка подтверждения"""
        dir_path = self.get_directory()

        if not dir_path:
            QMessageBox.warning(
                self,
                "⚠️ Внимание",
                "Пожалуйста, выберите рабочую директорию."
            )
            return

        # Проверяем существование директории
        if not os.path.exists(dir_path):
            reply = QMessageBox.question(
                self,
                "❓ Директория не существует",
                f"Директория не существует:\n{dir_path}\n\n"
                "Создать её?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "❌ Ошибка",
                        f"Не удалось создать директорию:\n{str(e)}"
                    )
                    return
            else:
                return

        # Проверяем права на запись
        if not self.validate_directory(dir_path):
            reply = QMessageBox.question(
                self,
                "⚠️ Предупреждение",
                f"Нет прав на запись в директорию:\n{dir_path}\n\n"
                "Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Сохраняем в настройках
        settings = QSettings('MyCompany', 'CodeAgent')
        settings.setValue('working_directory', dir_path)

        super().accept()