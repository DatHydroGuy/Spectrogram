from equaliser import Equaliser
from oscilloscope import Oscilloscope
from phasescope import PhaseScope
from config import *
from source import Microphone, PlaylistSource
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
        self.switch_source("playlist")
        self.playlist_widget.add_file_to_playlist(INIT_FILE)
        self.play_first_file_in_playlist()

        # Background elements
        bg_colour = (0.06, 0.06, 0.07, 1.0)
        # Bottom border
        self.nodes.append(
            Rect(self.ctx, 0, WINDOW_HEIGHT - BOTTOM_BORDER_HEIGHT, WINDOW_WIDTH, BOTTOM_BORDER_HEIGHT, bg_colour)
        )
        # Middle (left/right) separator
        self.nodes.append(Rect(self.ctx, VISUALISATION_HALF_WIDTH, VISUALISATION_HEIGHT, FREQUENCY_LABEL_WIDTH, WINDOW_HEIGHT, bg_colour))
        # One-third separator
        self.nodes.append(Rect(self.ctx, VISUALISATION_THIRD_WIDTH, 0, 6, VISUALISATION_HEIGHT, bg_colour))
        # Two-thirds separator
        self.nodes.append(Rect(self.ctx, WINDOW_WIDTH - VISUALISATION_THIRD_WIDTH - 6, 0, 6, VISUALISATION_HEIGHT, bg_colour))

        # Time ticks
        for x_value in [5, RIGHT_CHANNEL_VISUALISATION_START + 5]:
            self.nodes.append(
                Ticks(
                    self.ctx,
                    x=x_value,
                    y=WINDOW_HEIGHT - BOTTOM_BORDER_HEIGHT,
                    w=x_value - 9 + VISUALISATION_HALF_WIDTH,
                    h=15,
                    colour=(0.3, 0.3, 0.4, 1.0),
                    gap=6,
                )
            )
            self.nodes.append(
                Ticks(
                    self.ctx,
                    x=x_value,
                    y=WINDOW_HEIGHT - BOTTOM_BORDER_HEIGHT,
                    w=x_value - 9 + VISUALISATION_HALF_WIDTH,
                    h=20,
                    colour=(0.3, 0.3, 0.4, 1.0),
                    gap=12,
                )
            )
            self.nodes.append(
                Ticks(
                    self.ctx,
                    x=x_value + 30,
                    y=WINDOW_HEIGHT - BOTTOM_BORDER_HEIGHT,
                    w=x_value - 9 + VISUALISATION_HALF_WIDTH,
                    h=25,
                    colour=(0.4, 0.4, 0.5, 1.0),
                    gap=120,
                )
            )

        # Frequency ticks on left
        pixels_per_freq = SPECTROGRAM_HEIGHT / SPECTROGRAM_MAX_FREQUENCY  # SAMPLE_RATE // 2 is the max freq of our FFT (Nyquist frequency)
        self.nodes.append(
            Ticks(
                self.ctx,
                x=VISUALISATION_HALF_WIDTH,
                y=VISUALISATION_HEIGHT * NUM_VISUALISATIONS + 1,
                w=15,
                h=SPECTROGRAM_HEIGHT,
                colour=(0.4, 0.4, 0.5, 1.0),
                gap=pixels_per_freq * 2000,
                horizontal=False,
            )
        )
        # Frequency ticks on right
        self.nodes.append(
            Ticks(
                self.ctx,
                x=RIGHT_CHANNEL_VISUALISATION_START - 15,
                y=VISUALISATION_HEIGHT * NUM_VISUALISATIONS + 1,
                w=15,
                h=SPECTROGRAM_HEIGHT,
                colour=(0.4, 0.4, 0.5, 1.0),
                gap=pixels_per_freq * 2000,
                horizontal=False,
            )
        )

        # Create separate visualisations for left and right channels
        # Left channel
        self.eq_left = Equaliser(
            self.ctx,
            0,
            0,
            VISUALISATION_THIRD_WIDTH,
            VISUALISATION_HEIGHT,
            #colour=(0.2, 1.0, 0.2, 1.0)
        )
        self.nodes.append(self.eq_left)
        self.osc_left = Oscilloscope(
            self.ctx,
            0,
            VISUALISATION_HEIGHT,
            VISUALISATION_HALF_WIDTH,
            VISUALISATION_HEIGHT,
            # colour=(0.1, 1.0, 0.6, 1.0),
        )
        self.nodes.append(self.osc_left)
        self.wave_left = Wave(
            self.ctx,
            0,
            VISUALISATION_HEIGHT * 2,
            VISUALISATION_HALF_WIDTH,
            VISUALISATION_HEIGHT,
            colour=(0.1, 1.0, 0.6, 1.0),
        )
        self.nodes.append(self.wave_left)
        self.spectrogram_left = Spectrogram(
            self.ctx, 0, VISUALISATION_HEIGHT * NUM_VISUALISATIONS, VISUALISATION_HALF_WIDTH, SPECTROGRAM_HEIGHT, max_freq=SPECTROGRAM_MAX_FREQUENCY
        )
        self.nodes.append(self.spectrogram_left)

        # Right channel
        self.eq_right = Equaliser(
            self.ctx,
            WINDOW_WIDTH - VISUALISATION_THIRD_WIDTH,
            0,
            VISUALISATION_THIRD_WIDTH,
            VISUALISATION_HEIGHT,
            #colour=(0.2, 1.0, 0.2, 1.0)
        )
        self.nodes.append(self.eq_right)
        self.osc_right = Oscilloscope(
            self.ctx,
            RIGHT_CHANNEL_VISUALISATION_START,
            VISUALISATION_HEIGHT,
            VISUALISATION_HALF_WIDTH,
            VISUALISATION_HEIGHT,
            # colour=(0.1, 1.0, 0.6, 1.0),
        )
        self.nodes.append(self.osc_right)
        self.wave_right = Wave(
            self.ctx,
            RIGHT_CHANNEL_VISUALISATION_START,
            VISUALISATION_HEIGHT * 2,
            VISUALISATION_HALF_WIDTH,
            VISUALISATION_HEIGHT,
            colour=(0.1, 1.0, 0.6, 1.0)
        )
        self.nodes.append(self.wave_right)
        self.spectrogram_right = Spectrogram(
            self.ctx, RIGHT_CHANNEL_VISUALISATION_START, VISUALISATION_HEIGHT * NUM_VISUALISATIONS, VISUALISATION_HALF_WIDTH, SPECTROGRAM_HEIGHT, max_freq=SPECTROGRAM_MAX_FREQUENCY
        )
        self.nodes.append(self.spectrogram_right)

        self.phase = PhaseScope(
            self.ctx,
            VISUALISATION_THIRD_WIDTH + 6,
            0,
            VISUALISATION_THIRD_WIDTH,
            VISUALISATION_HEIGHT,
            colour=(0.8, 0.6, 1.0, 1.0)
        )
        self.nodes.append(self.phase)

        # Dividers between visualisations
        for i in range(NUM_VISUALISATIONS):
            self.nodes.append(Rect(self.ctx, 0, VISUALISATION_HEIGHT * (i + 1), WINDOW_WIDTH, 3, bg_colour))

        text = Text(self.ctx)
        self.nodes.append(text)

        # Time labels
        for i in range(0, 7):
            postfix = " "
            if i > 0:
                postfix = "s"
            x = VISUALISATION_HALF_WIDTH - i * 120
            text.add(f"{i}{postfix}", x, WINDOW_HEIGHT - 25, align="center")
            x2 = WINDOW_WIDTH - i * 120
            text.add(f"{i}{postfix}", x2, WINDOW_HEIGHT - 25, align="center")

        # Frequency labels for left channel
        num_markers = SPECTROGRAM_MAX_FREQUENCY // 2000
        for i in range(num_markers):
            hz = i * 2000
            y = VISUALISATION_HEIGHT * NUM_VISUALISATIONS + SPECTROGRAM_HEIGHT - pixels_per_freq * hz + 2
            if y > VISUALISATION_HEIGHT * NUM_VISUALISATIONS:  # Only show if within spectrogram area
                text.add(f"{hz} Hz", WINDOW_WIDTH // 2, y, align="center")

        # Channel labels
        text.add("LEFT CHANNEL", WINDOW_WIDTH // 4, WINDOW_HEIGHT - 10, align="center")
        text.add("RIGHT CHANNEL", 3 * WINDOW_WIDTH // 4 + FREQUENCY_LABEL_WIDTH // 2, WINDOW_HEIGHT - 10, align="center")

    def play_first_file_in_playlist(self):
        first_file = self.playlist_widget.playlist[0]
        self.playlist_widget.current_index = 0
        self.playlist_widget.highlight_current()
        self.source.load_file(first_file)

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
                self.play_first_file_in_playlist()

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
            elif isinstance(self.source, PlaylistSource) and self.source.complete:
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
            and self.source.complete
        ):
            self.next_track()

        available = self.source.available()
        logger.info(f"{available} available buffers")

        for _ in range(2):
            window_left, window_right = self.source.get()

            # Update left channel
            self.wave_left.add(window_left)
            self.eq_left.add(window_left)
            self.osc_left.add(window_left)
            self.spectrogram_left.add(window_left)

            # Update right channel
            self.wave_right.add(window_right)
            self.eq_right.add(window_right)
            self.osc_right.add(window_right)
            self.spectrogram_right.add(window_right)

            self.phase.add(window_left, window_right)

        self.wave_left.update()
        self.eq_left.update()
        self.osc_left.update()
        self.spectrogram_left.update()
        self.wave_right.update()
        self.eq_right.update()
        self.osc_right.update()
        self.spectrogram_right.update()
        self.phase.update()

        for node in self.nodes:
            node.draw()

    def exit(self):
        logger.info("exit")
        if self.source:
            self.source.release()

if __name__ == '__main__':
    App.run()
