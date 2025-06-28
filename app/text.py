import freetype
from config import *
from utils import orthographic


class CharacterSlot:

    def __init__(self, ctx, glyph):
        if not isinstance(glyph, freetype.GlyphSlot):
            raise RuntimeError('unknown glyph type')

        self.width = glyph.bitmap.width
        self.height = glyph.bitmap.rows
        self.advance = glyph.advance.x

        glyph_size = (self.width, self.height)

        data = np.array(glyph.bitmap.buffer, dtype='u1')
        self.texture = ctx.texture(glyph_size, 1, data)
        self.texture.repeat_x = False
        self.texture.repeat_y = False


class Text:
    vert_shader = """
    #version 330 core

    uniform mat4 projection;
    in vec2 vertex;
    in vec2 uv;
    out vec2 vert_uv;

    void main() {
        gl_Position = projection * vec4(vertex, 0.0, 1.0);
        vert_uv = uv;
    }
    """

    frag_shader = """
    #version 330 core

    uniform sampler2D image;
    uniform vec4 colour;
    in vec2 vert_uv;
    out vec4 out_colour;

    void main() {
        float mask = texture(image, vert_uv).r;
        out_colour = vec4(colour.rgb, colour.a * mask);
    }
    """

    def __init__(self, ctx):
        self.characters = None
        self.ctx = ctx
        self.prog = self.ctx.program(
            vertex_shader=self.vert_shader,
            fragment_shader=self.frag_shader,
        )
        self.prog['colour'] = (0.5, 0.5, 0.55, 1.0)

        self.vbo = self.ctx.buffer(reserve=6 * 4 * 4, dynamic=True)

        self.vao = self.ctx.vertex_array(self.prog, self.vbo, 'vertex', 'uv')

        self.init_font(r"..\fonts\Rubik-Regular.ttf")

        self.texts = []

    def init_font(self, font):
        self.characters = dict()

        size = int(FONT_SIZE * FONT_SCALE)
        face = freetype.Face(font)
        face.set_pixel_sizes(size, size)

        # load ASCII characters from 30 to 128
        for i in range(30, 128):
            char = chr(i)
            face.load_char(char)
            character = CharacterSlot(self.ctx, face.glyph)
            self.characters[char] = character

    def set_geometry(self, x, y, w, h):
        vertices = np.array([
            x, y, 0, 1,
            x + w, y, 1, 1,
            x + w, y - h, 1, 0,
            x, y, 0, 1,
            x + w, y - h, 1, 0,
            x, y - h, 0, 0,
        ])
        vertices = vertices.astype('f4')
        self.vbo.write(vertices)

    def text_width(self, text):
        w = 0
        for c in text:
            character = self.characters[c]
            w += (character.advance >> 6) / FONT_SCALE
        return w

    def add(self, text, x, y, align='left'):
        self.texts.append((text, x, y, align))

    def size(self, w, h):
        projection = orthographic(w, h)
        self.prog['projection'].write(projection)

    def draw(self):
        for text, x, y, align in self.texts:
            if align == 'center':
                w = self.text_width(text)
                x -= w / 2
            if align == 'right':
                w = self.text_width(text)
                x -= w
            for i, c in enumerate(text):
                character = self.characters[c]
                character.texture.use(0)
                w = character.width
                h = character.height
                self.set_geometry(x, y, w / FONT_SCALE, h / FONT_SCALE)
                self.vao.render()
                x += (character.advance >> 6) / FONT_SCALE
