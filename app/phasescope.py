from moderngl import BLEND, POINTS
from utils import orthographic
from config import *


class PhaseScope:
    """Lissajous curve display for stereo phase relationship"""

    vert_shader = """
#version 330 core
uniform mat4 projection;
uniform float x, y, w, h;
in vec2 sample;  // Mid-side processed samples
void main() {
    float x_pos = x + (w / 2) + sample.x * (w / 2) * 0.9;  // Side component (stereo width)
    float y_pos = y + (h / 2) + sample.y * (h / 2) * 0.9;  // Mid component (mono sum)
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

    def __init__(self, ctx, x, y, w, h, colour=(0.9, 0.7, 1.0, 0.8)):
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

        self.points = np.zeros((WINDOW_SIZE, 2), dtype="f4")
        self.buffer = ctx.buffer(reserve=self.points.nbytes, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, self.buffer, "sample")

    def add(self, window_left, window_right):
        if window_left is not None and window_right is not None:
            # Apply windowing to reduce spectral leakage
            windowed_left = window_left * HANNING[: len(window_left)]
            windowed_right = window_right * HANNING[: len(window_right)]

            # Calculate Mid-Side components for proper phase analysis
            # Mid = (L + R) / 2  - represents the mono content
            # Side = (L - R) / 2 - represents the stereo width/difference
            mid = (windowed_left + windowed_right) / 2.0
            side = (windowed_left - windowed_right) / 2.0

            # Downsample for display
            step = max(1, len(mid) // NUM_PHASE_SCOPE_POINTS)
            mid_samples = mid[::step][:NUM_PHASE_SCOPE_POINTS]
            side_samples = side[::step][:NUM_PHASE_SCOPE_POINTS]

            # Pad with zeros if needed
            if len(mid_samples) < NUM_PHASE_SCOPE_POINTS:
                mid_samples = np.pad(mid_samples, (0, NUM_PHASE_SCOPE_POINTS - len(mid_samples)))
                side_samples = np.pad(side_samples, (0, NUM_PHASE_SCOPE_POINTS - len(side_samples)))

            # X-axis: Side component (stereo width)
            # Y-axis: Mid component (mono content) - inverted for proper display
            self.points[:len(side_samples), 0] = side_samples
            self.points[:len(mid_samples), 1] = mid_samples  # Negative for correct orientation

    def update(self):
        self.buffer.write(self.points)

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog["projection"].write(projection)

    def draw(self):
        self.ctx.enable(BLEND)
        self.vao.render(POINTS)
