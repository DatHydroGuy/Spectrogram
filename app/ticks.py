import moderngl
import numpy as np
from utils import orthographic


class Ticks:

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

    def __init__(self, ctx, x, y, w, h, colour=(1.0, 0.0, 1.0, 1.0), gap=50, horizontal=True):
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

        if horizontal:
            num_ticks = int(w) // int(gap) + 1
        else:
            num_ticks = int(h) // int(gap) + 1

        vertices = np.zeros(num_ticks * 4, dtype='f4')
        for idx in range(num_ticks):
            if horizontal:
                vertices[idx * 4: (idx + 1) * 4] = [x + idx * gap, y, x + idx * gap, y + h]
            else:
                vertices[idx * 4: (idx + 1) * 4] = [x, y + idx * gap, x + w, y + idx * gap]

        buffer = self.ctx.buffer(vertices)
        self.vao = self.ctx.vertex_array(self.prog, buffer, 'vertex')

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog['projection'].write(projection)

    def draw(self):
        self.vao.render(mode=moderngl.LINES)
