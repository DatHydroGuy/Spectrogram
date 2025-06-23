import librosa
import math
import numpy as np
import pyaudio
from config import WINDOW_SIZE, HOP_SIZE, SAMPLE_RATE, BUFFER_SIZE


class Source:
    def __init__(self, *args, **kwargs):
        self.audio = pyaudio.PyAudio()
        self.complete = False
        self.data = []
        self.index = 0
        self.total = 0
        self.stream = None
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        raise NotImplementedError("source.init")

    def callback(self, in_data, frame_count, time_info, status):
        raise NotImplementedError("source.callback")

    def get(self):
        if self.index + WINDOW_SIZE > self.total:
            return None
        a = self.index
        b = self.index + WINDOW_SIZE
        data = self.data[a:b]
        self.index = a + HOP_SIZE
        return np.array(data)

    def available(self):
        samples = self.total - self.index
        samples -= WINDOW_SIZE
        available = math.ceil(samples / HOP_SIZE)
        return max(0, available)

    def normalise_audio(self, target_level=0.95, min_threshold=0.9):
        max_amplitude = np.max(np.abs(self.data))
        if max_amplitude == 0:
            print("WARNING: Silent audio detected")
            return
        if max_amplitude > 1.0 or max_amplitude < min_threshold:
            original_level = max_amplitude
            self.data = self.data / max_amplitude * target_level
            action = "reduced" if original_level > 1.0 else "amplified"
            print(f"Audio {action}: {original_level:.3f} -> {target_level:.3f}")
        else:
            print(f"Audio level OK: {max_amplitude:.3f}")

    def is_complete(self):
        """Check if the current audio source has finished playing"""
        return self.complete

    def release(self):
        if self.stream:
            self.stream.close()
        self.audio.terminate()


class File(Source):
    def init(self, file_name):
        self.file_name = file_name
        self.load_file(file_name)

    def load_file(self, file_name):
        """Load a new audio file"""
        try:
            self.data, _ = librosa.load(file_name, sr=SAMPLE_RATE)
            self.normalise_audio(target_level=0.95, min_threshold=0.9)
            self.index = 0
            self.total = 0
            self.complete = False

            # Close existing stream if any
            if self.stream:
                self.stream.close()

            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=BUFFER_SIZE,
                stream_callback=self.callback,
            )
            print(f"Loaded audio file: {file_name}")
        except Exception as e:
            print(f"Error loading file {file_name}: {e}")
            self.data = np.zeros(SAMPLE_RATE)  # 1 second of silence as fallback
            self.complete = True

    def callback(self, in_data, frame_count, time_info, status):
        a = self.total
        b = self.total + BUFFER_SIZE
        data = self.data[a:b]
        self.total = b
        if self.total >= len(self.data):
            self.complete = True
        return data, pyaudio.paContinue


class Microphone(Source):
    def init(self):
        # create audio stream
        self.stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=BUFFER_SIZE,
            stream_callback=self.callback,
        )

    def callback(self, in_data, frame_count, time_info, status):
        data = np.frombuffer(in_data, dtype=np.float32)
        data = data.tolist()
        self.data.extend(data)
        self.total = len(self.data)
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
            self.data, _ = librosa.load(file_path, sr=SAMPLE_RATE)
            self.normalise_audio(target_level=0.95, min_threshold=0.9)

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
                channels=1,
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

        if b <= len(self.data):
            data = self.data[a:b]
        else:
            # Pad with zeros if we're at the end
            data = np.zeros(BUFFER_SIZE, dtype=np.float32)
            if a < len(self.data):
                remaining = len(self.data) - a
                data[:remaining] = self.data[a:]

        self.total = b
        if self.total >= len(self.data):
            self.complete = True

        return data, pyaudio.paContinue

    def get(self):
        """Get audio window for processing"""
        if not hasattr(self, "data") or len(self.data) == 0:
            return None

        if self.index + WINDOW_SIZE > self.total:
            return None

        a = self.index
        b = self.index + WINDOW_SIZE
        data = self.data[a:b]
        self.index = a + HOP_SIZE
        return np.array(data)

    def available(self):
        """Get number of available audio windows"""
        if not hasattr(self, "data") or len(self.data) == 0:
            return 0

        samples = self.total - self.index
        samples -= WINDOW_SIZE
        available = math.ceil(samples / HOP_SIZE)
        return max(0, available)
