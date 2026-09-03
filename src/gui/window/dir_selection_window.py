import os

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDialogButtonBox, QPushButton, QHBoxLayout, QLineEdit, \
    QVBoxLayout, QLabel, QDialog


class DirectorySelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор рабочей директории")
        self.setModal(True)
        self.setFixedSize(500, 200)

        layout = QVBoxLayout()

        # Информация
        info_label = QLabel(
            "Для работы приложения необходимо выбрать рабочую директорию.\n"
            "Все созданные файлы будут сохранены в этой папке."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Поле с выбранной директорией
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Путь к рабочей директории...")
        layout.addWidget(self.dir_input)

        # Кнопки выбора
        btn_layout = QHBoxLayout()

        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self.browse_directory)
        btn_layout.addWidget(self.browse_btn)

        self.create_btn = QPushButton("Создать новую")
        self.create_btn.clicked.connect(self.create_directory)
        btn_layout.addWidget(self.create_btn)

        layout.addLayout(btn_layout)

        # Кнопки OK/Cancel
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # Загружаем последнюю директорию
        settings = QSettings('MyCompany', 'CodeAgent')
        last_dir = settings.value('working_directory', '')
        if last_dir:
            self.dir_input.setText(last_dir)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите рабочую директорию",
            self.dir_input.text() or os.path.expanduser('~')
        )
        if dir_path:
            self.dir_input.setText(dir_path)

    def create_directory(self):
        base_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите место для создания папки",
            os.path.expanduser('~')
        )
        if base_path:
            from PyQt6.QtWidgets import QInputDialog
            folder_name, ok = QInputDialog.getText(
                self,
                "Новая папка",
                "Введите имя новой папки:",
                text="codeagent_project"
            )
            if ok and folder_name:
                new_path = os.path.join(base_path, folder_name)
                try:
                    os.makedirs(new_path, exist_ok=True)
                    self.dir_input.setText(new_path)
                    QMessageBox.information(
                        self,
                        "Успешно",
                        f"Папка создана:\n{new_path}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        f"Не удалось создать папку:\n{str(e)}"
                    )

    def get_directory(self):
        return self.dir_input.text().strip()