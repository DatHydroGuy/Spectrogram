from moderngl import LINE_STRIP
from utils import orthographic
from config import *


class Oscilloscope:
    """Real-time oscilloscope display showing waveform details"""

    vert_shader = """
#version 330 core
uniform mat4 projection;
uniform float x, y, w, h;
in float sample;
void main() {
    float x_pos = x + (gl_VertexID * w / 8192.0);  // WINDOW_SIZE samples
    float y_pos = y + (h / 2) + sample * (h / 2);
    gl_Position = projection * vec4(x_pos, y_pos, 0.0, 1.0);
}
"""
    frag_shader = """
#version 330 core
uniform vec4 colour;
out vec4 out_colour;
void main() {
    out_colour = colour;
}
"""

    def __init__(self, ctx, x, y, w, h, colour=(0.2, 1.0, 0.2, 1.0)):
        self.ctx = ctx
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.prog = self.ctx.program(
            vertex_shader=self.vert_shader,
            fragment_shader=self.frag_shader,
        )
        self.prog["colour"] = colour
        self.prog["x"] = x
        self.prog["y"] = y
        self.prog["w"] = w
        self.prog["h"] = h

        self.samples = np.zeros(WINDOW_SIZE, dtype="f4")
        self.buffer = ctx.buffer(reserve=self.samples.nbytes, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, self.buffer, "sample")

    def add(self, window):
        if window is not None:
            # Downsample if needed to fit display
            if len(window) > WINDOW_SIZE:
                step = len(window) // WINDOW_SIZE
                self.samples = window[::step][:WINDOW_SIZE]
            else:
                self.samples[: len(window)] = window
                self.samples[len(window) :] = 0

    def update(self):
        self.buffer.write(self.samples)

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog["projection"].write(projection)

    def draw(self):
        self.vao.render(LINE_STRIP)
