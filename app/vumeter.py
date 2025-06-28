# class VUMeter:
#     """Classic VU meter style display"""
#
#     vert_shader = """
# #version 330 core
# uniform mat4 projection;
# in vec2 vertex;
# in vec4 colour;
# out vec4 v_colour;
# void main() {
#     gl_Position = projection * vec4(vertex, 0.0, 1.0);
#     v_colour = colour;
# }
# """
#     frag_shader = """
# #version 330 core
# in vec4 v_colour;
# out vec4 out_colour;
# void main() {
#     out_colour = v_colour;
# }
# """
#
#     def __init__(self, ctx, x, y, w, h):
#         self.ctx = ctx
#         self.x = x
#         self.y = y
#         self.w = w
#         self.h = h
#         self.prog = self.ctx.program(
#             vertex_shader=self.vert_shader,
#             fragment_shader=self.frag_shader,
#         )
#
#         self.level = 0.0
#         self.peak_level = 0.0
#         self.peak_hold_time = 0.0
#         self.segments = 20
#
#         # Create vertex buffer
#         vertices_per_segment = 6 * 2  # 6 vertices, 2 coords each
#         colours_per_segment = 6 * 4  # 6 vertices, 4 colour components each
#
#         self.vertices = np.zeros(self.segments * vertices_per_segment, dtype="f4")
#         self.colours = np.zeros(self.segments * colours_per_segment, dtype="f4")
#
#         vertex_buffer = ctx.buffer(self.vertices)
#         colour_buffer = ctx.buffer(self.colours)
#
#         self.vao = ctx.vertex_array(
#             self.prog,
#             [(vertex_buffer, "2f", "vertex"), (colour_buffer, "4f", "colour")],
#         )
#
#     def add(self, window):
#         if window is not None:
#             # Calculate RMS level
#             rms = np.sqrt(np.mean(window**2))
#             self.level = rms
#
#             # Peak detection with hold
#             if rms > self.peak_level:
#                 self.peak_level = rms
#                 self.peak_hold_time = 30  # Hold for 30 frames
#             elif self.peak_hold_time > 0:
#                 self.peak_hold_time -= 1
#             else:
#                 self.peak_level *= 0.95  # Slow decay
#
#     def update(self):
#         segment_height = self.h / self.segments
#
#         for i in range(self.segments):
#             # Calculate segment position
#             seg_y = self.y + self.h - (i + 1) * segment_height
#
#             # Determine if this segment should be lit
#             threshold = (i + 1) / self.segments
#             is_lit = self.level >= threshold
#             is_peak = abs(self.peak_level - threshold) < (1.0 / self.segments)
#
#             # Colour coding: green -> yellow -> red
#             if i < self.segments * 0.6:
#                 colour = (0.2, 1.0, 0.2, 1.0) if is_lit else (0.1, 0.3, 0.1, 1.0)
#             elif i < self.segments * 0.85:
#                 colour = (1.0, 1.0, 0.2, 1.0) if is_lit else (0.3, 0.3, 0.1, 1.0)
#             else:
#                 colour = (1.0, 0.2, 0.2, 1.0) if is_lit else (0.3, 0.1, 0.1, 1.0)
#
#             # Peak indicator
#             if is_peak:
#                 colour = (1.0, 1.0, 1.0, 1.0)
#
#             # Set vertices for this segment
#             base_vertex_idx = i * 12
#             self.vertices[base_vertex_idx : base_vertex_idx + 12] = [
#                 self.x,
#                 seg_y,
#                 self.x + self.w,
#                 seg_y,
#                 self.x + self.w,
#                 seg_y + segment_height - 1,
#                 self.x,
#                 seg_y,
#                 self.x + self.w,
#                 seg_y + segment_height - 1,
#                 self.x,
#                 seg_y + segment_height - 1,
#             ]
#
#             # Set colours for this segment
#             base_colour_idx = i * 24
#             for j in range(6):  # 6 vertices per segment
#                 self.colours[base_colour_idx + j * 4 : base_colour_idx + j * 4 + 4] = (
#                     colour
#                 )
#
#         # Update buffers
#         self.vao.vertex_buffers[0].write(self.vertices)
#         self.vao.vertex_buffers[1].write(self.colours)
#
#     def size(self, w, h):
#         projection = orthographic(w, h)
#         self.prog["projection"].write(projection)
#
#     def draw(self):
#         self.vao.render()
import numpy as np
from utils import orthographic


class VUMeter:
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

    def __init__(self, ctx, x, y, w, h):
        self.ctx = ctx
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.prog = self.ctx.program(
            vertex_shader=self.vert_shader,
            fragment_shader=self.frag_shader,
        )

        self.level = 0.0
        self.peak = 0.0
        self.peak_hold_time = 0
        self.smoothing = 0.8

        # Create buffer for meter bar and peak indicator
        self.buffer = ctx.buffer(reserve=24 * 4, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, self.buffer, "vertex")

    def add(self, window):
        if window is None:
            return

        # Calculate RMS level
        rms = np.sqrt(np.mean(window**2))
        # Convert to dB and normalise
        db_level = 20 * np.log10(rms + 1e-10)
        normalised_level = np.clip((db_level + 60) / 60, 0, 1)

        # Apply smoothing
        self.level = (
            self.smoothing * self.level + (1 - self.smoothing) * normalised_level
        )

        # Peak hold
        if normalised_level > self.peak:
            self.peak = normalised_level
            self.peak_hold_time = 30  # Hold for 30 frames
        elif self.peak_hold_time > 0:
            self.peak_hold_time -= 1
        else:
            self.peak *= 0.95  # Slow decay

    def update(self):
        vertices = []

        # Main level bar
        bar_w = self.level * self.w
        if self.level < 0.7:
            self.prog["colour"] = (0.0, 1.0, 0.0, 1.0)  # Green
        elif self.level < 0.9:
            self.prog["colour"] = (1.0, 1.0, 0.0, 1.0)  # Yellow
        else:
            self.prog["colour"] = (1.0, 0.0, 0.0, 1.0)  # Red

        vertices.extend(
            [
                self.x,
                self.y,
                self.x + bar_w,
                self.y,
                self.x + bar_w,
                self.y + self.h,
                self.x,
                self.y,
                self.x + bar_w,
                self.y + self.h,
                self.x,
                self.y + self.h,
            ]
        )

        # Peak indicator
        peak_x = self.x + self.peak * self.w
        vertices.extend([
            peak_x - 1, self.y,
            peak_x + 1, self.y,
            peak_x + 1, self.y + self.h,
            peak_x - 1, self.y,
            peak_x + 1, self.y + self.h,
            peak_x - 1, self.y + self.h,
            ])

        vertices = np.array(vertices, dtype="f4")
        self.buffer.write(vertices)

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog["projection"].write(projection)

    def draw(self):
        self.vao.render()
