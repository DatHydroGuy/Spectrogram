import librosa
from math import ceil
import pyaudio

from utils import logger
from config import *


class Source:
    def __init__(self, *args, **kwargs):
        self.audio = pyaudio.PyAudio()
        self.complete = False
        self.data_left = []
        self.data_right = []
        self.index = 0
        self.total = 0
        self.stream = None
        self.channels = 2  # Default to stereo
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        raise NotImplementedError("source.init")

    def callback(self, in_data, frame_count, time_info, status):
        raise NotImplementedError("source.callback")

    def normalise_audio(self, target_level=0.95, min_threshold=0.9):
        max_amplitude_left = np.max(np.abs(self.data_left))
        max_amplitude_right = np.max(np.abs(self.data_right))
        max_amplitude = max(max_amplitude_left, max_amplitude_right)
        if max_amplitude == 0:
            print("WARNING: Silent audio detected")
            return
        if max_amplitude > 1.0 or max_amplitude < min_threshold:
            original_level = max_amplitude
            self.data_left = self.data_left / max_amplitude * target_level
            self.data_right = self.data_right / max_amplitude * target_level
            action = "reduced" if original_level > 1.0 else "amplified"
            print(f"Audio {action}: {original_level:.3f} -> {target_level:.3f}")
        else:
            print(f"Audio level OK: {max_amplitude:.3f}")

    def get(self):
        if self.index + WINDOW_SIZE > self.total:
            return None, None
        a = self.index
        b = self.index + WINDOW_SIZE
        data_left = self.data_left[a:b]
        data_right = self.data_right[a:b] if self.channels == 2 else data_left
        self.index = a + HOP_SIZE
        return np.array(data_left), np.array(data_right)

    def available(self):
        samples = self.total - self.index
        samples -= WINDOW_SIZE
        available = ceil(samples / HOP_SIZE)
        return max(0, available)

    def release(self):
        self.stream.close()
        self.audio.terminate()


class File(Source):
    def init(self, file_name):
        # Load stereo audio - librosa returns (samples, channels) for stereo
        self.data, _ = librosa.load(file_name, sr=SAMPLE_RATE, mono=False)

        if self.data.ndim == 1:
            # Mono file - duplicate to both channels
            self.data_left = self.data.tolist()
            self.data_right = self.data.tolist()
            self.channels = 1
        else:
            # Stereo file
            self.data_left = self.data[0].tolist()
            self.data_right = self.data[1].tolist()
            self.channels = 2

        self.normalise_audio(target_level=0.95, min_threshold=0.9)

        # Use the longer channel length
        max_length = max(len(self.data_left), len(self.data_right))

        # Pad shorter channel if needed
        while len(self.data_left) < max_length:
            np.append(self.data_left, [0.0])
        while len(self.data_right) < max_length:
            np.append(self.data_right, [0.0])

        self.stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=2,  # Always output stereo
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=BUFFER_SIZE,
            stream_callback=self.callback,
        )

    def callback(self, in_data, frame_count, time_info, status):
        a = self.total
        b = self.total + BUFFER_SIZE

        # Get data for both channels
        data_left = self.data_left[a:b] if a < len(self.data_left) else [0.0] * (b - a)
        data_right = (
            self.data_right[a:b] if a < len(self.data_right) else [0.0] * (b - a)
        )

        # Pad if necessary
        while len(data_left) < BUFFER_SIZE:
            np.append(data_left, [0.0])
        while len(data_right) < BUFFER_SIZE:
            np.append(data_right, [0.0])

        # Interleave stereo data (LRLRLR...)
        stereo_data = np.zeros(BUFFER_SIZE * 2, dtype=np.float32)
        stereo_data[0::2] = data_left[:BUFFER_SIZE]
        stereo_data[1::2] = data_right[:BUFFER_SIZE]

        self.total = b
        if self.total >= max(len(self.data_left), len(self.data_right)):
            self.complete = True

        return stereo_data, pyaudio.paContinue


class Microphone(Source):
    def init(self):
        # Try to open stereo microphone first
        try:
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=2,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=BUFFER_SIZE,
                stream_callback=self.callback,
            )
            self.channels = 2
            logger.info("Opened stereo microphone")
        except:
            # Fall back to mono if stereo not available
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=BUFFER_SIZE,
                stream_callback=self.callback,
            )
            self.channels = 1
            logger.info("Opened mono microphone (stereo not available)")

    def callback(self, in_data, frame_count, time_info, status):
        data = np.frombuffer(in_data, dtype=np.float32)

        if self.channels == 2:
            # Stereo data - deinterleave (LRLRLR... -> separate L and R)
            data_left = data[0::2].tolist()
            data_right = data[1::2].tolist()
        else:
            # Mono data - duplicate to both channels
            data_mono = data.tolist()
            data_left = data_mono
            data_right = data_mono

        self.data_left.extend(data_left)
        self.data_right.extend(data_right)
        self.total = len(self.data_left)
        return None, pyaudio.paContinue



class PlaylistSource(Source):
    """Source that manages a playlist of audio files"""

    def init(self, playlist_widget):
        self.playlist_widget = playlist_widget
        self.current_file_source = None
        self.current_file = None

    def load_file(self, file_path):
        """Load a specific file from the playlist"""
        try:
            # Create a new File source for the selected file
            if self.current_file_source:
                self.current_file_source.release()

            # Load the file data
            self.data, _ = librosa.load(file_path, sr=SAMPLE_RATE, mono=False)
            if self.data.ndim == 1:
                # Mono file - duplicate to both channels
                self.data_left = self.data.tolist()
                self.data_right = self.data.tolist()
                self.channels = 1
            else:
                # Stereo file
                self.data_left = self.data[0].tolist()
                self.data_right = self.data[1].tolist()
                self.channels = 2

            self.normalise_audio(target_level=0.95, min_threshold=0.9)

            # Use the longer channel length
            max_length = max(len(self.data_left), len(self.data_right))

            # Pad shorter channel if needed
            while len(self.data_left) < max_length:
                np.append(self.data_left, [0.0])
            while len(self.data_right) < max_length:
                np.append(self.data_right, [0.0])

            # Set up our data
            self.index = 0
            self.total = 0
            self.complete = False
            self.current_file = file_path

            # Close existing stream if any
            if self.stream:
                self.stream.close()

            # Create new stream
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=2,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=BUFFER_SIZE,
                stream_callback=self.callback,
            )

            print(f"Loaded playlist file: {file_path}")

        except Exception as e:
            print(f"Error loading playlist file {file_path}: {e}")
            self.data = np.zeros(SAMPLE_RATE)  # 1 second of silence as fallback
            self.complete = True

    def callback(self, in_data, frame_count, time_info, status):
        """Stream callback for audio playback"""
        if not hasattr(self, "data") or len(self.data) == 0:
            return np.zeros(BUFFER_SIZE, dtype=np.float32), pyaudio.paContinue

        a = self.total
        b = self.total + BUFFER_SIZE

        # Get data for both channels
        data_left = self.data_left[a:b] if a < len(self.data_left) else [0.0] * (b - a)
        data_right = (
            self.data_right[a:b] if a < len(self.data_right) else [0.0] * (b - a)
        )

        # Pad if necessary
        while len(data_left) < BUFFER_SIZE:
            np.append(data_left, [0.0])
        while len(data_right) < BUFFER_SIZE:
            np.append(data_right, [0.0])

        # Interleave stereo data (LRLRLR...)
        stereo_data = np.zeros(BUFFER_SIZE * 2, dtype=np.float32)
        stereo_data[0::2] = data_left[:BUFFER_SIZE]
        stereo_data[1::2] = data_right[:BUFFER_SIZE]

        self.total = b
        if self.total >= len(self.data):
            self.complete = True

        return stereo_data, pyaudio.paContinue

    # def get(self):
    #     if self.index + WINDOW_SIZE > self.total:
    #         return None, None
    #     a = self.index
    #     b = self.index + WINDOW_SIZE
    #     data_left = self.data_left[a:b]
    #     data_right = self.data_right[a:b] if self.channels == 2 else data_left
    #     self.index = a + HOP_SIZE
    #     return np.array(data_left), np.array(data_right)

    # def available(self):
    #     """Get number of available audio windows"""
    #     if not hasattr(self, "data") or len(self.data) == 0:
    #         return 0
    #
    #     samples = self.total - self.index
    #     samples -= WINDOW_SIZE
    #     available = ceil(samples / HOP_SIZE)
    #     return max(0, available)
