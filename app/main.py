from config import WINDOW_WIDTH, WINDOW_HEIGHT
from source import File, Microphone
from window import Window
from wave import Wave
from spectrogram import Spectrogram
from utils import logger
from rect import Rect
from ticks import Ticks
from text import Text


class App(Window):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectrogram App")
        self.source = None
        self.wave = None
        self.spectrogram = None
        self.nodes = []

    def init(self):
        logger.info("init")
        self.source = Microphone()
        # self.source = File(r"<add path to audio file here>")

        self.wave = Wave(self.ctx, 0, 0, WINDOW_WIDTH, WINDOW_HEIGHT // 3)
        self.nodes.append(self.wave)
        self.spectrogram = Spectrogram(self.ctx, 0, self.wave.h, WINDOW_WIDTH, (1.76 * WINDOW_HEIGHT) // 3)
        self.nodes.append(self.spectrogram)

        bg_colour = (0.06, 0.06, 0.07, 1.0)

        # time axis background
        self.nodes.append(Rect(self.ctx, 0, 830, WINDOW_WIDTH, 80, bg_colour))

        # frequency axis background
        self.nodes.append(Rect(self.ctx, 0, 0, 99, WINDOW_HEIGHT, bg_colour))

        # wave / frequency separator
        self.nodes.append(Rect(self.ctx, 0, self.wave.h, WINDOW_WIDTH, 3, bg_colour))

        # 1/20th second ticks
        self.nodes.append(Ticks(self.ctx, x=100, y=830, w=WINDOW_WIDTH - 100, h=15, colour=(0.3, 0.3, 0.4, 1.0), gap=6))

        # 1/10th second ticks
        self.nodes.append(Ticks(self.ctx, x=100, y=830, w=WINDOW_WIDTH - 100, h=20, colour=(0.3, 0.3, 0.4, 1.0), gap=12))

        # 1 second ticks
        self.nodes.append(Ticks(self.ctx, x=100 + 60, y=830, w=WINDOW_WIDTH - 100, h=25, colour=(0.4, 0.4, 0.5, 1.0), gap=120))

        # 2000 Hz frequency ticks
        pixels_per_freq = self.spectrogram.h / 11046        # 11046 is the max freq of our FFT
        self.nodes.append(Ticks(self.ctx, x=80, y=self.spectrogram.y + pixels_per_freq * 1046, w=20, h=pixels_per_freq * 10000, colour=(0.4, 0.4, 0.5, 1.0), gap=pixels_per_freq * 2000, horizontal=False))

        # create text renderer
        text = Text(self.ctx)
        self.nodes.append(text)

        # seconds text
        for i in range(0, 13):
            postfix = "s"
            if i == 0:
                postfix = " "
            x = WINDOW_WIDTH - i * 120
            text.add(f"{i}{postfix}", x, 875, align="center")

        # frequency text
        for i in range(6):
            hz = i * 2000
            y = 830 - pixels_per_freq * hz + 2
            text.add(f"{hz} Hz", 70, y, align="right")

    def win_size(self, w, h):
        logger.info(f"size, width:{w}, height:{h}")
        for node in self.nodes:
            node.size(w, h)

    def draw(self, dt):
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
        self.source.release()


if __name__ == '__main__':
    App.run()
