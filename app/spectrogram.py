import numpy as np
from config import WINDOW_SIZE
from librosa import amplitude_to_db     # takes a couple of seconds!
import matplotlib
from utils import orthographic


hanning = np.hanning(WINDOW_SIZE)
colour_map = matplotlib.colormaps.get_cmap('inferno')


def stft_slice(window):
    data_length = window.shape[0]
    if data_length < WINDOW_SIZE:
        padded_data = np.zeros(WINDOW_SIZE, dtype=window.dtype)
        padded_data[:data_length] = window
        window = padded_data
    tapered = window * hanning
    return np.fft.rfft(tapered)

def stft_colour(signal_slice, min_db=-25, max_db=30):
    signal_slice = np.abs(signal_slice)
    signal_slice = amplitude_to_db(signal_slice)
    signal_slice = signal_slice.clip(min_db, max_db)
    signal_slice = (signal_slice - min_db) / (max_db - min_db)
    signal_slice = colour_map(signal_slice)
    signal_slice = (signal_slice * 255).astype('u1')
    signal_slice = signal_slice[:, :3]
    return signal_slice


class Spectrogram:

    vertex_shader = """
        #version 330 core
        
        uniform mat4 projection;
        in vec2 in_vert;
        in vec2 in_uv;
        
        out vec2 v_uv;
        
        void main() {
            gl_Position = projection * vec4(in_vert, 0.0, 1.0);
            v_uv = in_uv;
        }
"""

    fragment_shader = """
        #version 330 core

        uniform sampler2D image;    
        in vec2 v_uv;
        
        out vec4 f_colour;
        
        void main() {
            vec4 colour = texture(image, v_uv);
            f_colour = vec4(colour.rgb, 1.0);
        }
"""

    def __init__(self, ctx, x, y, w, h):
        self.ctx = ctx
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.prog = self.ctx.program(
            vertex_shader=self.vertex_shader,
            fragment_shader=self.fragment_shader,
        )

        vertices = np.array([
            0, y, 0, 1,         # A
            0, y + h, 0, 0,     # B
            w, y + h, 1, 0,     # C
            0, y, 0, 1,         # A
            w, y + h, 1, 0,     # C
            w, y, 1, 1,         # D
        ])

        vertices = vertices.astype('f4')
        buffer = self.ctx.buffer(vertices)
        self.vao = self.ctx.vertex_array(self.prog, buffer, 'in_vert', 'in_uv')

        self.frame = np.zeros((513, self.w, 3), dtype='u1')

        self.texture = self.ctx.texture(size=(self.w, 513), components=3, data=self.frame)
        self.texture.repeat_x = False
        self.texture.repeat_y = False

        self.slice = np.zeros((513, 3), dtype='u1')

    def add(self, window):
        self.frame[:, :-1, :] = self.frame[:, 1:, :]

        if window is not None:
            data_slice = stft_slice(window)
            data_slice = stft_colour(data_slice)
            self.slice = data_slice

        self.frame[:, -1, :] = self.slice

    def update(self):
        self.texture.write(self.frame)

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog['projection'].write(projection)

    def draw(self):
        self.texture.use(0)
        self.vao.render()
