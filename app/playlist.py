import os
import json
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import pyqtSignal


class Playlist(QWidget):
    file_selected = pyqtSignal(str)  # Signal emitted when a file is selected
    playlist_changed = pyqtSignal()  # Signal emitted when playlist changes

    def __init__(self):
        super().__init__()
        self.playlist = []
        self.current_index = -1
        self.setup_ui()
        self.set_stylesheet()

    def set_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1A1A1C;
                color: #DDDDDD;
                font-family: Arial;
                font-size: 12px;
            }
            QListWidget {
                background-color: #1A1A1C;
                border: 1px solid #333;
            }
            QListWidget::item:selected {
                background: #444;
            }
            QListWidget:disabled {
                background-color: #222;
                border: 1px solid #111;
                color: #777777;
            }
            QPushButton {
                background-color: #2A2A2D;
                border: 1px solid #444;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #3A3A3D;
            }
            QPushButton:disabled {
                background-color: #222;
                border: 1px solid #111;
                color: #777777;
            }
            QLabel {
                color: #AAAAAA;
            }
            QLabel:disabled {
                background-color: #222;
                border: 1px solid #111;
                color: #777777;
            }
        """)

    def setup_ui(self):
        layout = QVBoxLayout()

        controls_layout = QHBoxLayout()

        # self.add_file_btn = QPushButton("Add File")
        self.add_files_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        self.clear_btn = QPushButton("Clear")
        self.save_playlist_btn = QPushButton("Save List")
        self.load_playlist_btn = QPushButton("Load List")

        # controls_layout.addWidget(self.add_file_btn)
        controls_layout.addWidget(self.add_files_btn)
        controls_layout.addWidget(self.remove_btn)
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addWidget(self.save_playlist_btn)
        controls_layout.addWidget(self.load_playlist_btn)

        self.playlist_widget = QListWidget()
        self.playlist_widget.setSelectionMode(QListWidget.SingleSelection)

        self.info_label = QLabel("Playlist: 0 files")

        layout.addLayout(controls_layout)
        layout.addWidget(self.playlist_widget)
        layout.addWidget(self.info_label)

        self.setLayout(layout)

        # Connect signals
        # self.add_file_btn.clicked.connect(self.add_file)
        self.add_files_btn.clicked.connect(self.add_files)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn.clicked.connect(self.clear_playlist)
        self.save_playlist_btn.clicked.connect(self.save_playlist)
        self.load_playlist_btn.clicked.connect(self.load_playlist)
        self.playlist_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.playlist_widget.currentRowChanged.connect(self.on_selection_changed)

    def add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.m4a *.ogg);;All Files (*)",
        )

        if file_path:
            self.add_file_to_playlist(file_path)

    def add_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.m4a *.ogg);;All Files (*)",
        )

        for file_path in file_paths:
            self.add_file_to_playlist(file_path)

    def add_file_to_playlist(self, file_path):
        if file_path not in self.playlist:
            self.playlist.append(file_path)

            # Add to widget display
            filename = os.path.basename(file_path)
            item = QListWidgetItem(filename)
            item.setToolTip(file_path)  # Show full path on hover
            self.playlist_widget.addItem(item)

            self.update_info()
            self.playlist_changed.emit()

    def remove_selected(self):
        current_row = self.playlist_widget.currentRow()
        if current_row >= 0:
            # Remove from playlist
            del self.playlist[current_row]

            # Remove from widget
            self.playlist_widget.takeItem(current_row)

            # Update current index
            if self.current_index == current_row:
                self.current_index = -1
            elif self.current_index > current_row:
                self.current_index -= 1

            self.update_info()
            self.playlist_changed.emit()

    def clear_playlist(self):
        self.playlist.clear()
        self.playlist_widget.clear()
        self.current_index = -1
        self.update_info()
        self.playlist_changed.emit()

    def save_playlist(self):
        if not self.playlist:
            QMessageBox.information(self, "Info", "Playlist is empty")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist", "playlist.json", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump(self.playlist, f, indent=2)
                QMessageBox.information(self, "Success", "Playlist saved successfully")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save playlist:\n{str(e)}"
                )

    def load_playlist(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Playlist", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "r") as f:
                    loaded_playlist = json.load(f)

                # Verify files exist
                valid_files = []
                missing_files = []

                for audio_file in loaded_playlist:
                    if os.path.exists(audio_file):
                        valid_files.append(audio_file)
                    else:
                        missing_files.append(audio_file)

                # Clear current playlist and add valid files
                self.clear_playlist()
                for audio_file in valid_files:
                    self.add_file_to_playlist(audio_file)

                # Show info about missing files
                if missing_files:
                    missing_list = "\n".join(missing_files[:10])  # Limit display
                    if len(missing_files) > 10:
                        missing_list += f"\n... and {len(missing_files) - 10} more"
                    QMessageBox.warning(
                        self,
                        "Missing Files",
                        f"The following files could not be found:\n\n{missing_list}",
                    )

                if valid_files:
                    QMessageBox.information(
                        self, "Success", f"Loaded {len(valid_files)} files successfully"
                    )

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load playlist:\n{str(e)}"
                )

    def on_item_double_clicked(self, item):
        row = self.playlist_widget.row(item)
        if 0 <= row < len(self.playlist):
            self.current_index = row
            self.file_selected.emit(self.playlist[row])
            self.highlight_current()

    def on_selection_changed(self, current_row):
        if 0 <= current_row < len(self.playlist):
            # You might want to emit a signal here for preview or other actions
            pass

    def get_current_file(self):
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def get_next_file(self):
        if self.playlist and self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.highlight_current()
            self.file_selected.emit(self.playlist[self.current_index])
            return self.playlist[self.current_index]
        return None

    def get_previous_file(self):
        if self.playlist and self.current_index > 0:
            self.current_index -= 1
            self.highlight_current()
            self.file_selected.emit(self.playlist[self.current_index])
            return self.playlist[self.current_index]
        return None

    def has_next(self):
        """Check if there's a next track available"""
        return self.playlist and self.current_index < len(self.playlist) - 1

    def has_previous(self):
        """Check if there's a previous track available"""
        return self.playlist and self.current_index > 0

    def highlight_current(self):
        # Clear all selections first
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            item.setSelected(False)

        # Highlight current item
        if 0 <= self.current_index < self.playlist_widget.count():
            current_item = self.playlist_widget.item(self.current_index)
            current_item.setSelected(True)
            self.playlist_widget.setCurrentItem(current_item)

    def update_info(self):
        current_info = ""
        if self.current_index >= 0 and self.current_index < len(self.playlist):
            current_file = os.path.basename(self.playlist[self.current_index])
            current_info = f" | Current: {current_file}"
        self.info_label.setText(f"Playlist: {len(self.playlist)} files{current_info}")
