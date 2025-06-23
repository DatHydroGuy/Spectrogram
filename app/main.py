from config import WINDOW_WIDTH, WINDOW_HEIGHT, PLAYLIST_WIDTH
from source import File, Microphone, PlaylistSource
from window import Window
from wave import Wave
from spectrogram import Spectrogram
from utils import logger
from rect import Rect
from ticks import Ticks
from text import Text
from playlist import Playlist
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QButtonGroup


class App(Window):
    def __init__(self):
        super().__init__()
        self.source = None
        self.wave = None
        self.spectrogram = None
        self.nodes = []
        self.playlist_widget = None
        self.current_source_type = "playlist"  # "file", "microphone", "playlist"

    def init(self):
        logger.info("init")

        # Set up the main layout with controls
        self.setup_ui()
        self.set_stylesheet()

        # Initialize with default file source
        self.source = File(r"<add path to audio file here>")

        # Set up visualisation components
        self.wave = Wave(
            self.ctx, 0, 0, WINDOW_WIDTH, WINDOW_HEIGHT // 3
        )  # Leave space for controls
        self.nodes.append(self.wave)

        self.spectrogram = Spectrogram(
            self.ctx, 0, self.wave.h, WINDOW_WIDTH, (1.76 * WINDOW_HEIGHT) // 3
        )
        self.nodes.append(self.spectrogram)

        # Background elements
        bg_colour = (0.06, 0.06, 0.07, 1.0)
        self.nodes.append(Rect(self.ctx, 0, 830, WINDOW_WIDTH, 80, bg_colour))
        self.nodes.append(Rect(self.ctx, 0, 0, 99, WINDOW_HEIGHT, bg_colour))
        self.nodes.append(
            Rect(self.ctx, 0, self.wave.h, WINDOW_WIDTH, 3, bg_colour)
        )

        # Ticks and labels
        self.nodes.append(
            Ticks(
                self.ctx,
                x=100,
                y=830,
                w=WINDOW_WIDTH - 100,
                h=15,
                colour=(0.3, 0.3, 0.4, 1.0),
                gap=6,
            )
        )
        self.nodes.append(
            Ticks(
                self.ctx,
                x=100,
                y=830,
                w=WINDOW_WIDTH - 100,
                h=20,
                colour=(0.3, 0.3, 0.4, 1.0),
                gap=12,
            )
        )
        self.nodes.append(
            Ticks(
                self.ctx,
                x=100 + 60,
                y=830,
                w=WINDOW_WIDTH - 100,
                h=25,
                colour=(0.4, 0.4, 0.5, 1.0),
                gap=120,
            )
        )

        pixels_per_freq = self.spectrogram.h / 11046
        self.nodes.append(
            Ticks(
                self.ctx,
                x=80,
                y=self.spectrogram.y + pixels_per_freq * 1046,
                w=20,
                h=pixels_per_freq * 10000,
                colour=(0.4, 0.4, 0.5, 1.0),
                gap=pixels_per_freq * 2000,
                horizontal=False,
            )
        )

        text = Text(self.ctx)
        self.nodes.append(text)

        # Time labels
        for i in range(0, 13):
            postfix = "s"
            if i == 0:
                postfix = " "
            x = WINDOW_WIDTH - i * 120
            text.add(f"{i}{postfix}", x, 875, align="center")

        # Frequency labels
        for i in range(6):
            hz = i * 2000
            y = 830 - pixels_per_freq * hz + 2
            text.add(f"{hz} Hz", 70, y, align="right")

    def setup_ui(self):
        """Set up the control panel UI"""
        # Create control panel
        control_panel = QWidget()
        two_row_layout = QVBoxLayout()
        control_layout = QHBoxLayout()
        playback_layout = QHBoxLayout()

        # Source selection buttons
        self.source_button_group = QButtonGroup()

        self.file_btn = QPushButton("Single File")
        self.file_btn.setCheckable(True)
        self.file_btn.setChecked(True)
        self.file_btn.clicked.connect(lambda: self.switch_source("file"))

        self.playlist_btn = QPushButton("Playlist")
        self.playlist_btn.setCheckable(True)
        self.playlist_btn.clicked.connect(lambda: self.switch_source("playlist"))

        self.microphone_btn = QPushButton("Microphone")
        self.microphone_btn.setCheckable(True)
        self.microphone_btn.clicked.connect(lambda: self.switch_source("microphone"))

        # self.source_button_group.addButton(self.file_btn)
        self.source_button_group.addButton(self.playlist_btn)
        self.source_button_group.addButton(self.microphone_btn)

        # Playlist controls (only visible when playlist mode is active)
        self.prev_btn = QPushButton("Previous")
        self.play_pause_btn = QPushButton("Play/Pause")
        self.next_btn = QPushButton("Next")
        self.prev_btn.clicked.connect(self.previous_track)
        self.play_pause_btn.clicked.connect(self.play_pause_track)
        self.next_btn.clicked.connect(self.next_track)
        # self.prev_btn.setVisible(False)
        # self.next_btn.setVisible(False)

        # control_layout.addWidget(self.file_btn)
        control_layout.addWidget(self.playlist_btn)
        control_layout.addWidget(self.microphone_btn)
        playback_layout.addWidget(self.prev_btn)
        playback_layout.addWidget(self.play_pause_btn)
        playback_layout.addWidget(self.next_btn)
        # control_layout.addStretch()
        control_layout.setContentsMargins(0, 0, 0, 0)  # Remove outer margins
        control_layout.setSpacing(0)  # Remove spacing between widgets

        two_row_layout.addLayout(control_layout)
        two_row_layout.addLayout(playback_layout)
        control_panel.setLayout(two_row_layout)
        # control_panel.setFixedHeight(50)

        # Create playlist widget
        self.playlist_widget = Playlist()
        self.playlist_widget.file_selected.connect(self.on_playlist_file_selected)
        self.playlist_widget.setMinimumWidth(PLAYLIST_WIDTH)
        # self.playlist_widget.setVisible(False)
        # self.playlist_widget.setEnabled(True)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove outer margins
        main_layout.setSpacing(0)  # Remove spacing between widgets
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.playlist_widget)
        # main_layout.addStretch()  # This pushes everything to the top

        # Set the layout on the main widget
        container = QWidget()
        container.setLayout(main_layout)

        # This is a bit of a hack - we're adding Qt widgets to our OpenGL widget
        # In a production app, you might want to use a proper Qt layout instead
        container.setParent(self)
        container.move(WINDOW_WIDTH, 0)
        container.resize(PLAYLIST_WIDTH, WINDOW_HEIGHT)

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

    def switch_source(self, source_type):
        """Switch between different audio sources"""
        logger.info(f"Switching to {source_type} source")

        # Clean up current source
        if self.source:
            self.source.release()

        self.current_source_type = source_type

        # Show/hide appropriate controls
        # self.playlist_widget.setVisible(source_type == "playlist")
        # self.prev_btn.setVisible(source_type == "playlist")
        # self.play_pause_btn.setVisible(source_type == "playlist")
        # self.next_btn.setVisible(source_type == "playlist")
        self.playlist_widget.setEnabled(source_type == "playlist")
        self.prev_btn.setEnabled(source_type == "playlist")
        self.play_pause_btn.setEnabled(source_type == "playlist")
        self.next_btn.setEnabled(source_type == "playlist")

        # Create new source
        # if source_type == "file":
        #     self.source = File(r"..\audio\Pacmania.wav")
        if source_type == "microphone":
            self.source = Microphone()
        elif source_type == "playlist":
            self.source = PlaylistSource(self.playlist_widget)
            # If playlist is empty or no file selected, try to start with first file
            if (
                self.playlist_widget.playlist
                and self.playlist_widget.current_index == -1
            ):
                first_file = self.playlist_widget.playlist[0]
                self.playlist_widget.current_index = 0
                self.playlist_widget.highlight_current()
                self.source.load_file(first_file)

    def on_playlist_file_selected(self, file_path):
        """Handle file selection from playlist"""
        if self.current_source_type == "playlist" and isinstance(
            self.source, PlaylistSource
        ):
            logger.info(f"Loading file from playlist: {file_path}")
            self.source.load_file(file_path)

    def previous_track(self):
        """Go to previous track in playlist"""
        if self.current_source_type == "playlist":
            prev_file = self.playlist_widget.get_previous_file()
            if prev_file and isinstance(self.source, PlaylistSource):
                self.source.load_file(prev_file)

    def play_pause_track(self):
        """Play or pause or resume the current track in playlist"""
        if self.current_source_type == "playlist":
            # TODO: implement
            raise NotImplementedError

    def next_track(self):
        """Go to next track in playlist"""
        if self.current_source_type == "playlist":
            next_file = self.playlist_widget.get_next_file()
            if next_file and isinstance(self.source, PlaylistSource):
                self.source.load_file(next_file)
            elif isinstance(self.source, PlaylistSource) and self.source.is_complete():
                # Auto-advance to next track when current one finishes
                next_file = self.playlist_widget.get_next_file()
                if next_file:
                    self.source.load_file(next_file)

    def win_size(self, w, h):
        logger.info(f"size, width:{w}, height:{h}")
        for node in self.nodes:
            node.size(w, h)

    def draw(self, dt):
        # Check for auto-advance in playlist mode
        if (
            self.current_source_type == "playlist"
            and isinstance(self.source, PlaylistSource)
            and self.source.is_complete()
        ):
            self.next_track()

        available = self.source.available()
        logger.info(f"{available} available buffers")

        for _ in range(2):
            window = self.source.get()
            self.wave.add(window)
            self.spectrogram.add(window)

        self.wave.update()
        self.spectrogram.update()

        for node in self.nodes:
            node.draw()

    def exit(self):
        logger.info("exit")
        if self.source:
            self.source.release()

if __name__ == '__main__':
    App.run()
