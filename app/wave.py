from moderngl import LINES
from numpy import zeros, abs
from utils import orthographic


class Wave:
    vert_shader = """
#version 330 core
uniform mat4 projection;
uniform float x, y, h;
in float sample;
void main() {
    int x_interp = gl_VertexID / 2;
    float height = (h / 2) + sample * (h / 2);
    gl_Position = projection * vec4(x + x_interp, y + height, 0.0, 1.0);
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

    def __init__(self, ctx, x, y, w, h, colour=(0.1, 1.0, 0.6, 1.0)):
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
        self.samples = zeros(int(w * 2), dtype="f4")
        self.buffer = ctx.buffer(reserve=self.samples.nbytes, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, self.buffer, "sample")
        self.prog["x"] = x
        self.prog["y"] = y
        self.prog["h"] = h
        self.update()
        self.sample = 0.002

    def add(self, window):
        if window is not None:
            self.sample = abs(window[:100]).max()
        self.samples[:-2] = self.samples[2:]
        self.samples[-2:] = [-self.sample, self.sample]

    def update(self):
        self.buffer.write(self.samples)

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog["projection"].write(projection)

    def draw(self):
        self.vao.render(LINES)
