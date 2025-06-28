from numpy import array
from utils import orthographic


class Rect:

    vert_shader = """
#version 330 core

uniform mat4 projection;
in vec2 vertex;

void main() {
    gl_Position = projection * vec4(vertex, 0.0, 1.0);
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

    def __init__(self, ctx, x, y, w, h, colour=(0.0, 0.5, 1.0, 1.0)):
        self.ctx = ctx
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.prog = self.ctx.program(
            vertex_shader=self.vert_shader,
            fragment_shader=self.frag_shader,
        )
        self.prog['colour'] = colour

        vertices = array([
            x, y,
            x + w, y,
            x + w, y + h,
            x, y,
            x + w, y + h,
            x, y + h,
        ])

        vertices = vertices.astype('f4')
        buffer = self.ctx.buffer(vertices)
        self.vao = self.ctx.vertex_array(self.prog, buffer, 'vertex')

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog['projection'].write(projection)

    def draw(self):
        self.vao.render()
