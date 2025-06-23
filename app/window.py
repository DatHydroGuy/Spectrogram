import time
import moderngl
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QSurfaceFormat
from PyQt5.QtWidgets import QApplication, QOpenGLWidget, QShortcut
from config import APP_WIDTH, WINDOW_HEIGHT
from utils import logger


class Window(QOpenGLWidget):
    frame_rate = 60

    def __init__(self):
        super().__init__()

        self.t = None
        self.ctx = None
        self.setFixedSize(APP_WIDTH, WINDOW_HEIGHT)

        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        fmt.setDefaultFormat(fmt)
        fmt.setSamples(4)
        self.setFormat(fmt)

        QShortcut(Qt.Key_Escape, self, self.quit)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(int(1000 / self.frame_rate))

    # region OpenGL Logic
    def initializeGL(self):
        self.ctx = moderngl.create_context(require=330)
        self.ctx.clear(0.0, 0.0, 0.0)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.multisample = True
        self.init()

    def resizeGL(self, width, height):
        self.win_size(width, height)

    def paintGL(self):
        now = time.time()
        dt = now - self.t if self.t else 1.0 / self.frame_rate
        self.t = now
        self.draw(dt)

    # end region OpenGL Logic

    def quit(self):
        self.exit()
        self.close()

    @classmethod
    def run(cls):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)     # Respect OS scaling factor
        app = QApplication([])
        main = cls()
        main.show()
        app,exit(app.exec())

    # region Interface
    def init(self):
        logger.info("init")

    def win_size(self, w, h):
        logger.info(f"size, width:{w}, height:{h}")

    def draw(self, dt):
        logger.info(f"draw, dt:{dt:.4f}")

    def exit(self):
        logger.info("exit")

    # end region Interface
