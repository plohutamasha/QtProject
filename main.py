import sys
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, QListWidget,
                             QTextEdit, QPushButton, QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QAction,
                             QDateTimeEdit, QDialogButtonBox, QWidget, QComboBox)
from PyQt5.QtCore import Qt, QDateTime, QTimer


class Note:
    def __init__(self, title="Новая заметка", content="", category="Без категории", created=None, modified=None):
        self.title = title
        self.content = content
        self.category = category
        self.created = created or QDateTime.currentDateTime()
        self.modified = modified or QDateTime.currentDateTime()

    def to_dict(self):
        return {
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "created": self.created.toString(Qt.ISODate),
            "modified": self.modified.toString(Qt.ISODate),
        }

    @staticmethod
    def from_dict (data):
        created = QDateTime.fromString(data.get("created"), Qt.ISODate) if data.get("created") else None
        modified = QDateTime.fromString(data.get("modified"), Qt.ISODate) if data.get("modified") else None

        return Note(
            data.get("title", "Новая заметка"),
            data.get("content", ""),
            str(data.get("category", "Без категории")),
            created,
            modified
        )


class NoteEditDialog(QDialog):
    def __init__(self, parent=None, note=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать заметку")
        self.title_edit = QLineEdit()
        self.content_edit = QTextEdit()
        self.created_edit = QDateTimeEdit()
        self.created_edit.setReadOnly(True)
        self.modified_edit = QDateTimeEdit()
        self.modified_edit.setReadOnly(True)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        layout.insertWidget(2, QLabel("Категория:"))
        layout.insertWidget(3, self.category_combo)
        layout.addWidget(QLabel("Заголовок:"))
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("Создана:"))
        layout.addWidget(self.created_edit)
        layout.addWidget(QLabel("Изменена:"))
        layout.addWidget(self.modified_edit)
        layout.addWidget(QLabel("Текст:"))
        layout.addWidget(self.content_edit)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

        if note:
            self.title_edit.setText(note.title)
            self.content_edit.setText(note.content)
            self.created_edit.setDateTime(note.created)
            self.modified_edit.setDateTime(QDateTime.currentDateTime())
            self.category_combo.setCurrentText(note.category)
        else:
            self.created_edit.setDateTime(QDateTime.currentDateTime())

        if note:
            if note.category not in [self.category_combo.itemText(i) for i in range(self.category_combo.count())]:
                self.category_combo.addItem(note.category)

            self.category_combo.setCurrentText(note.category)

    def get_note(self):
        return Note(
            self.title_edit.text(),
            self.content_edit.toPlainText(),
            self.category_combo.currentText(),
            self.created_edit.dateTime(),
            QDateTime.currentDateTime()
        )

    def accept(self):
        if not self.title_edit.text():
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите заголовок.")
            return

        if not self.content_edit.toPlainText():
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите текст заметки.")
            return

        if not self.category_combo.currentText():
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите категорию.")
            return

        super().accept()

class NoteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.notes = []
        self.filepath = "notes.json"
        self.list_widget = QListWidget(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.category_filter = QComboBox(self)
        self.category_filter.addItem("Все категории")
        self.category_filter.currentIndexChanged.connect(self.filter_notes_by_category)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.text_edit)
        self.setCentralWidget(splitter)

        add_button = QPushButton("Add Note", self)
        edit_button = QPushButton("Edit Note", self)
        remove_button = QPushButton("Remove Note", self)

        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(self.category_filter, 1)

        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        main_layout.addLayout(button_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        add_button.clicked.connect(self.add_note)
        edit_button.clicked.connect(self.edit_note)
        remove_button.clicked.connect(self.remove_note)
        self.list_widget.currentItemChanged.connect(self.display_note)
        self.load_notes()

        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        edit_menu = menubar.addMenu("&Edit")
        help_menu = menubar.addMenu("&Help")

        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        add_action = QAction("Add Note", self)
        edit_action = QAction("Edit Note", self)
        remove_action = QAction("Remove Note", self)

        edit_menu.addAction(add_action)
        edit_menu.addAction(edit_action)
        edit_menu.addAction(remove_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.save_notes)
        self.autosave_timer.start(300000)

    def add_note(self):
        dialog = NoteEditDialog(self)
        dialog.category_combo.clear()
        for category in self.get_categories():
            dialog.category_combo.addItem(category)

        if dialog.exec_() == QDialog.Accepted:
            note = dialog.get_note()
            self.notes.append(note)
            self.update_list_widget()
            self.save_notes()
            if note.category not in self.get_categories():
                self.category_filter.addItem(note.category)
            self.update_category_filter()

    def edit_note(self):
        current_row = self.list_widget.currentRow()
        if current_row == -1:
            return

        dialog = NoteEditDialog(self, self.notes[current_row])

        dialog.category_combo.clear()
        for category in self.get_categories():
            dialog.category_combo.addItem(category)

        if dialog.exec_() == QDialog.Accepted:

            old_category = self.notes[current_row].category

            self.notes[current_row] = dialog.get_note()
            new_category = self.notes[current_row].category

            if (old_category != new_category and new_category
                    and new_category not in
                    [self.category_filter.itemText(i) for i in range(self.category_filter.count())]):
                self.category_filter.addItem(new_category)

            self.notes[current_row] = dialog.get_note()
            self.update_list_widget()
            self.display_note()
            self.save_notes()
            if old_category and self.notes[current_row].category != old_category:
                self.update_list_widget()
            self.update_category_filter()

    def remove_note(self):
        current_row = self.list_widget.currentRow()
        if current_row == -1:
            return

        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы действительно хотите удалить заметку: {self.notes[current_row].title}?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.notes[current_row]
            self.update_list_widget()
            self.text_edit.clear()
            self.save_notes()

    def display_note(self, item=None):
        current_row = self.list_widget.currentRow()

        if current_row != -1:

            note = self.notes[current_row]
            self.text_edit.setPlainText(note.content)

        elif item:
            index = self.list_widget.indexFromItem(item).row()
            self.text_edit.setPlainText(self.notes[index].content)

    def filter_notes_by_category(self):
        self.update_list_widget(self.category_filter.currentText())

    def update_list_widget(self, category_filter=None):

        self.list_widget.clear()

        if category_filter is not None and category_filter != "Все категории":
            notes_to_show = [note for note in self.notes if note.category == category_filter]
        else:
            notes_to_show = self.notes

        for note in notes_to_show:
            self.list_widget.addItem(note.title)

    def load_notes(self):
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.notes = [Note.from_dict(note_data) for note_data in data]

        except (FileNotFoundError, json.JSONDecodeError):
            pass

        self.update_list_widget()
        if self.notes:
            self.list_widget.setCurrentRow(0)

        self.update_category_filter()

    def update_category_filter(self):
        self.category_filter.clear()
        self.category_filter.addItem("Все категории")
        for category in self.get_categories():
            self.category_filter.addItem(category)

    def save_notes(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump([note.to_dict() for note in self.notes], f, ensure_ascii=False,
                          indent=4)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить заметки: {e}")

    def show_about(self):
        QMessageBox.about(self, "О программе NoteApp", """
            <p><b>NoteApp</b></p>
            <p>Версия: 1.0.0</p>
            <p>Автор: Плохута Мария</p>
            <p>GitHub: <a href="https://github.com/plohutamasha">plohutamasha</a></p>  </a>
        """)

    def get_categories(self):
        categories = set()
        for note in self.notes:
            if isinstance(note, Note) and hasattr(note, 'category'):
                categories.add(note.category)
        return sorted(list(categories.union({"Без категории"})))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NoteApp()
    window.show()
    sys.exit(app.exec_())
