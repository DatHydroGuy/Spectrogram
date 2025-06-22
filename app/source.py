import librosa
import math
import numpy as np
import pyaudio
import time
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
        data = self.data[a: b]
        self.index = a + HOP_SIZE
        return np.array(data)

    def available(self):
        samples = self.total - self.index
        samples -= WINDOW_SIZE
        available = math.ceil(samples / HOP_SIZE)
        return max(0, available)

    # def available(self):
    #     samples = self.total - self.index
    #     samples -= WINDOW_SIZE
    #     available_test = math.ceil(samples / self.hop_size)
    #     self.hop_size = HOP_SIZE
    #     if available_test > 10:
    #         self.hop_size = HOP_SIZE + 50
    #
    #     available = math.ceil(samples / self.hop_size)
    #     return max(0, available)

    def normalise_audio(self, target_level=0.95, min_threshold=0.1):
        """
        Normalise audio to target level.

        Args:
            target_level: Target peak amplitude (default 0.95)
            min_threshold: Minimum level below which to amplify (default 0.1)
        """
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

    def release(self):
        self.stream.close()
        self.audio.terminate()


class File(Source):

    def init(self, file_name):
        self.data, _ = librosa.load(file_name, sr=SAMPLE_RATE)
        self.normalise_audio(target_level=0.95, min_threshold=0.9)

        self.stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=BUFFER_SIZE,
            stream_callback=self.callback,
        )

    def callback(self, in_data, frame_count, time_info, status):
        a = self.total
        b = self.total + BUFFER_SIZE
        data = self.data[a: b]
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


if __name__ == "__main__":
    filename = r"../audio/SuperTwintris.wav"
    source = File(filename)
    time.sleep(5)
