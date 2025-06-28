from config import *
from utils import orthographic


class Equaliser:
    """Graphics equaliser with frequency bands"""

    vert_shader = """
#version 330 core
uniform mat4 projection;
uniform float eq_bottom;
uniform float eq_height;
in vec2 vertex;
out float norm_y;
void main() {
    gl_Position = projection * vec4(vertex, 0.0, 1.0);
    // Normalise y position: 0.0 at bottom of EQ, 1.0 at top
    norm_y = (vertex.y - eq_bottom) / eq_height;
}
"""
    frag_shader = """
#version 330 core
in float norm_y;
out vec4 out_colour;
void main() {
    // Always gradient from green (bottom) to red (top) based on vertical position
    // norm_y goes from 1.0 (bottom) to 0.0 (top) due to OpenGL coordinates
    float t = 1.0 - norm_y;  // Flip so 0.0 is bottom, 1.0 is top

    vec3 green = vec3(0.0, 1.0, 0.0);
    vec3 yellow = vec3(1.0, 1.0, 0.0);  
    vec3 red = vec3(1.0, 0.0, 0.0);

    vec3 colour;
    if (t <= 0.5) {
        // Bottom half: green to yellow
        colour = mix(green, yellow, t * 2.0);
    } else {
        // Top half: yellow to red  
        colour = mix(yellow, red, (t - 0.5) * 2.0);
    }

    out_colour = vec4(colour, 1.0);
}
"""

    def __init__(self, ctx, x, y, w, h, colour=(0.2, 0.8, 1.0, 1.0)):
        self.ctx = ctx
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.prog = self.ctx.program(
            vertex_shader=self.vert_shader,
            fragment_shader=self.frag_shader,
        )

        # Set uniforms for the equaliser bounds
        self.prog["eq_bottom"] = float(y)
        self.prog["eq_height"] = float(h)

        self.max_level = 0
        self.num_bands = len(EQ_BANDS)
        self.band_width = w / self.num_bands
        self.band_levels = np.zeros(self.num_bands, dtype="f4")
        self.decay_factor = 0.85  # For smooth fall-off
        self.attack_factor = 0.3  # For smooth rise
        self.peak_levels = np.zeros(self.num_bands, dtype="f4")  # Peak hold
        self.peak_decay = 0.99  # Slower decay for peaks

        # Adaptive scaling - track actual levels
        self.target_max = 0.8  # Target maximum bar height (80% of full scale)
        self.headroom = 0  # dB of headroom above current max

        # Create VAO for all bands (vertices only)
        vertices = np.zeros(self.num_bands * 6 * 2, dtype="f4")
        self.vertices = vertices
        self.buffer = ctx.buffer(vertices)
        self.vao = ctx.vertex_array(self.prog, self.buffer, "vertex")

    def add(self, window):
        if window is not None:
            # Apply window function
            windowed = window * HANNING[: len(window)]

            # Compute FFT
            fft_data = np.fft.rfft(windowed)
            fft_magnitude = np.abs(fft_data)
            power_spectrum = fft_magnitude**2

            freqs = np.fft.rfftfreq(len(window), 1 / SAMPLE_RATE)

            for i, band_freq in enumerate(EQ_BANDS):
                if i == 0:
                    band_start = 0
                    band_end = (EQ_BANDS[0] + EQ_BANDS[1]) / 2
                elif i == len(EQ_BANDS) - 1:
                    band_start = (EQ_BANDS[i - 1] + EQ_BANDS[i]) / 2
                    band_end = SAMPLE_RATE / 2
                else:
                    band_start = (EQ_BANDS[i - 1] + EQ_BANDS[i]) / 2
                    band_end = (EQ_BANDS[i] + EQ_BANDS[i + 1]) / 2

                mask = (freqs >= band_start) & (freqs < band_end)
                if np.any(mask):
                    band_power = np.sqrt(np.mean(power_spectrum[mask]))

                    if band_power > 1e-10:
                        db_level = 20 * np.log10(band_power)

                        # Adaptive scaling - update max level for this band
                        if db_level > self.max_level:
                            self.max_level = db_level

                        # Create dynamic range based on observed maximum
                        dynamic_max = self.max_level + self.headroom
                        dynamic_min = self.max_level - 60  # 60dB dynamic range

                        # Normalise using adaptive range
                        if dynamic_max > dynamic_min:
                            normalised_level = np.clip(
                                (db_level - dynamic_min) / (dynamic_max - dynamic_min),
                                0,
                                1,
                            )
                        else:
                            normalised_level = 0

                        # Scale to target maximum
                        normalised_level *= self.target_max

                        # Apply cube root for more responsive visual scaling
                        normalised_level = np.power(normalised_level, 1 / 3)

                    else:
                        normalised_level = 0

                    # Smooth animation
                    if normalised_level > self.band_levels[i]:
                        self.band_levels[i] = (
                            self.band_levels[i] * (1 - self.attack_factor)
                            + normalised_level * self.attack_factor
                        )
                    else:
                        self.band_levels[i] *= self.decay_factor

                    # Update peaks
                    if normalised_level > self.peak_levels[i]:
                        self.peak_levels[i] = normalised_level
                    else:
                        self.peak_levels[i] *= self.peak_decay

    def update(self):
        # Update vertex buffer with current band levels
        for i in range(self.num_bands):
            bar_x = self.x + i * self.band_width + 1
            bar_width = self.band_width - 2
            bar_height = self.band_levels[i] * self.h

            # Note: y coordinates go from bottom (self.y + self.h) to top (self.y)
            base_idx = i * 12

            # Two triangles per bar
            self.vertices[base_idx : base_idx + 12] = [
                bar_x,
                self.y + self.h,  # Bottom left
                bar_x + bar_width,
                self.y + self.h,  # Bottom right
                bar_x + bar_width,
                self.y + self.h - bar_height,  # Top right
                bar_x,
                self.y + self.h,  # Bottom left
                bar_x + bar_width,
                self.y + self.h - bar_height,  # Top right
                bar_x,
                self.y + self.h - bar_height,  # Top left
            ]

        self.buffer.write(self.vertices)

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog["projection"].write(projection)

    def draw(self):
        self.vao.render()
