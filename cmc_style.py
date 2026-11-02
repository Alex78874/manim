"""
Briques partagées de la série d'onboarding cmc-archi.

Chaque épisode fait `from cmc_style import *` et hérite d'`EpisodeScene`,
qui pose le fond, le titre fixe en haut à gauche et la puce de section.

Contenu :
  - la palette et les polices ;
  - des textes et puces (label, make_chip) ;
  - des pictogrammes (personne, référent·e, téléphone, navigateur, réseau) ;
  - des nœuds et liens pour les cartes d'architecture ;
  - du code coloré façon IDE (CodeView) et le curseur qui flashe (flash) ;
  - la scène de base EpisodeScene.
"""

import re
from html import escape

import numpy as np
from manimlib import *
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.token import Token
from pygments.util import ClassNotFound


# ---------------------------------------------------------------------------
# Palette et polices
# ---------------------------------------------------------------------------

UI_FONT = "Sans"
MONO_FONT = "DejaVu Sans Mono"
CODE_FONT = MONO_FONT
CODE_STYLE = "monokai"           # style pygments pour la coloration

BG = "#14151C"
PANEL_BG = "#1E1F29"
PANEL_STROKE = "#3A3C4E"
TXT = "#E6E6E6"
DIM = "#7A7F99"
ACCENT = "#4EC9B0"        # vert « Brigades Vertes »
GOLD = "#F7B93E"          # référent·es, et Prettier
VIOLET = "#8C7CF0"        # back-office, et ESLint
SEA = "#163247"
SEA_EDGE = "#2E6A8E"
WARN = "#E2B714"
ERROR = "#F14C4C"
OK_GREEN = "#4EC9B0"
BLUE = "#61DAFB"

SEVERITY = {
    "error": ("✖", ERROR),
    "warning": ("▲", WARN),
}

CHIP_Y = 3.05

# Par défaut ManimGL repeint tout MarkupText en blanc après l'avoir construit,
# ce qui efface les <span foreground=...> : ces options gardent leurs couleurs.
KEEP_SPAN_COLORS = dict(fill_color=None, stroke_color=None)


# ---------------------------------------------------------------------------
# Textes
# ---------------------------------------------------------------------------

def label(text, size=22, color=TXT, font=UI_FONT, bold=False):
    if bold:
        mob = MarkupText(f"<b>{escape(text, quote=False)}</b>", font=font, font_size=size)
    else:
        mob = Text(text, font=font, font_size=size)
    return mob.set_color(color)


def markup(text, size=22, font=UI_FONT):
    """MarkupText multicolore : les <span foreground=...> sont conservés."""
    return MarkupText(text, font=font, font_size=size, **KEEP_SPAN_COLORS)


def make_chip(text, color, y=CHIP_Y):
    lab = label(text, 24, color, bold=True)
    bg = RoundedRectangle(
        width=lab.get_width() + 0.6, height=lab.get_height() + 0.32, corner_radius=0.16
    )
    bg.set_fill(color, 0.12).set_stroke(color, 1.5)
    lab.move_to(bg)
    return VGroup(bg, lab).move_to([0, y, 0])


def fit_x(mob, margin=0.3):
    """Décale horizontalement un objet pour qu'il reste dans le cadre."""
    limit = FRAME_X_RADIUS - margin
    if mob.get_right()[0] > limit:
        mob.shift((mob.get_right()[0] - limit) * LEFT)
    if mob.get_left()[0] < -limit:
        mob.shift((-limit - mob.get_left()[0]) * RIGHT)
    return mob


def fr_int(n):
    return f"{int(round(n)):,}".replace(",", " ")


def counter(value_fn, anchor, size=46, color=TXT):
    """Un nombre qui défile de 0 à sa valeur, centré sur `anchor`."""
    mob = label(value_fn(0), size, color, bold=True).move_to(anchor)

    def update(m, alpha):
        m.become(label(value_fn(alpha), size, color, bold=True).move_to(anchor))

    return mob, UpdateFromAlphaFunc(mob, update, rate_func=smooth)


# ---------------------------------------------------------------------------
# Pictogrammes
# ---------------------------------------------------------------------------

def person(color=TXT, scale=1.0):
    head = Circle(radius=0.09).set_fill(color, 1).set_stroke(width=0)
    body = RoundedRectangle(width=0.26, height=0.2, corner_radius=0.1)
    body.set_fill(color, 1).set_stroke(width=0)
    body.next_to(head, DOWN, buff=0.03)
    return VGroup(head, body).scale(scale)


def star_shape(radius):
    """Étoile à cinq branches (ManimGL n'a pas de classe Star)."""
    pts = [
        (radius if k % 2 == 0 else radius * 0.45)
        * np.array([np.cos(PI / 2 + k * PI / 5), np.sin(PI / 2 + k * PI / 5), 0])
        for k in range(10)
    ]
    return Polygon(*pts)


def star_person(scale=1.0):
    """Un·e référent·e : une personne dorée surmontée d'une étoile."""
    p = person(GOLD, scale)
    star = star_shape(0.09 * scale).set_fill(GOLD, 1).set_stroke(width=0)
    star.next_to(p, UP, buff=0.04 * scale)
    return VGroup(p, star)


def phone(width=1.9, height=3.6):
    body = RoundedRectangle(width=width, height=height, corner_radius=0.25)
    body.set_fill("#0E0F15", 1).set_stroke(PANEL_STROKE, 2)
    screen = RoundedRectangle(width=width - 0.2, height=height - 0.45, corner_radius=0.14)
    screen.set_fill(PANEL_BG, 1).set_stroke(width=0)
    screen.move_to(body).shift(0.05 * DOWN)
    notch = RoundedRectangle(width=0.5, height=0.08, corner_radius=0.04)
    notch.set_fill(PANEL_STROKE, 1).set_stroke(width=0)
    notch.move_to(body.get_top() + 0.13 * DOWN)
    return VGroup(body, screen, notch)


def window_dots(radius=0.05):
    return VGroup(*[
        Circle(radius=radius).set_fill(c, 1).set_stroke(width=0)
        for c in ("#FF5F57", "#FEBC2E", "#28C840")
    ]).arrange(RIGHT, buff=radius * 1.6)


def browser(width=4.2, height=2.8):
    box = RoundedRectangle(width=width, height=height, corner_radius=0.15)
    box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 2)
    bar = Line(box.get_corner(UL) + 0.38 * DOWN, box.get_corner(UR) + 0.38 * DOWN)
    bar.set_stroke(PANEL_STROKE, 1.5)
    dots = window_dots().move_to(box.get_corner(UL) + np.array([0.3, -0.19, 0]))
    return VGroup(box, bar, dots)


def signal_bars(n_on=4, color=ACCENT):
    bars = VGroup(*[
        Rectangle(width=0.07, height=0.07 + 0.06 * i).set_stroke(width=0)
        for i in range(4)
    ]).arrange(RIGHT, buff=0.04, aligned_edge=DOWN)
    for i, b in enumerate(bars):
        b.set_fill(color if i < n_on else PANEL_STROKE, 1)
    return bars


# ---------------------------------------------------------------------------
# Cartes d'architecture : nœuds et liens
# ---------------------------------------------------------------------------

def dashed(mob, num_dashes=None, dash_ratio=0.55):
    """Version en pointillé du contour d'un objet (pour ce qui est décidé, pas codé)."""
    if num_dashes is None:
        num_dashes = max(12, int(mob.get_arc_length() / 0.14))
    return DashedVMobject(mob, num_dashes=num_dashes, positive_space_ratio=dash_ratio)


def node(title, subtitle=None, color=ACCENT, width=2.6, height=None, planned=False,
         title_size=22, subtitle_size=15):
    """Une boîte de la carte : titre, sous-titre, contour plein ou pointillé."""
    t = label(title, title_size, color if not planned else DIM, font=MONO_FONT, bold=True)
    texts = VGroup(t)
    if subtitle:
        texts.add(label(subtitle, subtitle_size, DIM))
    texts.arrange(DOWN, buff=0.1)
    if texts.get_width() > width - 0.3:
        texts.set_width(width - 0.3)
    h = height or texts.get_height() + 0.45
    box = RoundedRectangle(width=width, height=h, corner_radius=0.14)
    box.set_fill(color, 0.08 if not planned else 0.03)
    if planned:
        box.set_stroke(width=0)
        outline = dashed(RoundedRectangle(width=width, height=h, corner_radius=0.14))
        outline.set_stroke(color, 1.8, opacity=0.85)
        outline.move_to(box)
    else:
        box.set_stroke(color, 2)
        outline = VGroup()
    texts.move_to(box)
    group = VGroup(box, outline, texts)
    group.box = box
    return group


def link(start, end, color=DIM, planned=False, width=2.2, buff=0.08, tip=True):
    """Une flèche entre deux points (pointillée si prévue)."""
    if planned:
        line = DashedLine(start, end, dash_length=0.09, buff=buff)
        line.set_stroke(color, width, opacity=0.85)
        if not tip:
            return line
        direction = (end - start) / np.linalg.norm(end - start)
        head = ArrowTip().set_fill(color, 0.85).set_stroke(width=0).scale(0.6)
        head.rotate(np.arctan2(direction[1], direction[0]))
        head.move_to(end - direction * (buff + head.get_width() / 2))
        return VGroup(line, head)
    if not tip:
        return Line(start, end, buff=buff).set_stroke(color, width)
    return Arrow(start, end, buff=buff, thickness=width).set_color(color)


def edge_point(mob, direction):
    """Point du bord d'un nœud, dans une direction (UP, LEFT, UR...)."""
    target = mob.box if hasattr(mob, "box") else mob
    return target.get_boundary_point(direction)


def packet(color=ACCENT, radius=0.07):
    return Dot(radius=radius).set_fill(color, 1).set_stroke(width=0)


# ---------------------------------------------------------------------------
# Code façon IDE : coloration syntaxique, lignes, blocs
# ---------------------------------------------------------------------------

BASE_FS = 24                     # taille de construction (tout est rescalé ensuite)
LINE_SPACING = 1.12
GUTTER_COLS = 2                  # largeur des numéros de ligne
GUTTER_GAP = 2                   # espace entre numéros et code

# Glyphe "étai" invisible placé en début de chaque ligne : il donne à toutes
# les lignes la même hauteur et le même point d'origine, ce qui préserve
# l'indentation et permet de calculer la position exacte d'une colonne.
STRUT = "█"  # █

WORD_RE = re.compile(r"[\w$#@.]+|[^\w\s]+")


def pick_lexer(names):
    for name in names:
        try:
            return get_lexer_by_name(name)
        except ClassNotFound:
            continue
    raise ValueError(f"Aucun lexer pygments trouvé parmi {names}")


def token_color(style, ttype, default):
    if ttype in Token.Error:
        return default
    # Certains lexers (yaml) émettent des jetons que le style ne connaît pas,
    # comme Literal.Scalar.Plain : on remonte au parent le plus proche connu.
    while ttype not in style._styles and ttype.parent is not None:
        ttype = ttype.parent
    color = style.style_for_token(ttype)["color"]
    return f"#{color}" if color else default


def highlight_lines(source, lexer_names):
    """Une chaîne de markup Pango colorée par ligne de `source`."""
    lexer = pick_lexer(lexer_names)
    style = get_style_by_name(CODE_STYLE)
    base = style.style_for_token(Token)["color"]
    default = f"#{base}" if base else TXT

    lines = [[]]
    for ttype, value in lexer.get_tokens(source):
        color = token_color(style, ttype, default)
        for k, part in enumerate(value.split("\n")):
            if k:
                lines.append([])
            if part:
                lines[-1].append(
                    f'<span foreground="{color}">{escape(part, quote=False)}</span>'
                )
    while lines and not lines[-1]:
        lines.pop()
    return ["".join(spans) for spans in lines]


def make_line(markup_text, font_size, font=CODE_FONT):
    """MarkupText précédé d'un étai invisible. Renvoie (ligne, étai)."""
    mob = MarkupText(
        f'<span foreground="{TXT}">{STRUT}</span>{markup_text}',
        font=font,
        font_size=font_size,
        **KEEP_SPAN_COLORS,
    )
    strut = min(mob.family_members_with_points(), key=lambda m: m.get_left()[0])
    strut.set_opacity(0)
    return mob, strut


def place(mob, strut, x, y):
    """Place la ligne pour que le bord gauche de l'étai soit en (x, y)."""
    mob.shift(np.array([x, y, 0]) - strut.get_left())


class CodeView:
    """Un bloc de code : numéros de ligne + lignes colorées, positionnable."""

    def __init__(self, source, lexer_names, font_size=BASE_FS, gutter=True):
        spans = highlight_lines(source, lexer_names)
        cal = MarkupText(STRUT * 20, font=CODE_FONT, font_size=font_size)
        self.adv = cal.get_width() / 20
        self.block_h = cal.get_height()
        self.line_h = self.block_h * LINE_SPACING
        self.text = source.split("\n")

        self.gutter = VGroup()
        self.lines = VGroup()
        self.gutter_struts = []
        self.code_struts = []
        code_x = (GUTTER_COLS + GUTTER_GAP) * self.adv if gutter else 0
        for i, line_markup in enumerate(spans):
            y = -i * self.line_h
            if gutter:
                num, num_strut = make_line(
                    f'<span foreground="{DIM}">{i + 1:>{GUTTER_COLS}}</span>', font_size
                )
                place(num, num_strut, 0, y)
                self.gutter.add(num)
                self.gutter_struts.append(num_strut)
            code, code_strut = make_line(line_markup, font_size)
            place(code, code_strut, code_x, y)
            self.lines.add(code)
            self.code_struts.append(code_strut)
        self.group = VGroup(self.gutter, self.lines)

    @property
    def size(self):
        return self.group.get_width(), self.group.get_height()

    def fit(self, scale, top_left):
        self.group.scale(scale, about_point=ORIGIN)
        corner = np.array([self.group.get_left()[0], self.group.get_top()[1], 0])
        self.group.shift(top_left - corner)
        self.adv *= scale
        self.block_h *= scale
        self.line_h *= scale
        return self

    # --- géométrie (valable une fois fit() appelé) ---
    def line_y(self, line):
        return self.code_struts[line - 1].get_center()[1]

    def col_x(self, line, col):
        # l'étai occupe la colonne 0, la colonne c (base 1) commence c avances plus loin
        return self.code_struts[line - 1].get_left()[0] + col * self.adv

    def gutter_x(self):
        return self.gutter_struts[0].get_left()[0]

    def span_box(self, line, start, length):
        """(centre, largeur, hauteur) des caractères [start, start+length) d'une ligne."""
        x0 = self.col_x(line, start + 1)
        center = np.array([x0 + length * self.adv / 2, self.line_y(line), 0])
        return center, length * self.adv + 0.06, self.block_h * 1.08

    def word_boxes(self, line, text=None):
        text = self.text[line - 1] if text is None else text
        return [self.span_box(line, m.start(), len(m.group())) for m in WORD_RE.finditer(text)]

    def line_box(self, line, text=None):
        text = self.text[line - 1] if text is None else text
        start = len(text) - len(text.lstrip())
        return self.span_box(line, start, max(1, len(text.strip())))

    def token_box(self, line, token):
        """Boîte du premier `token` trouvé sur la ligne."""
        start = self.text[line - 1].find(token)
        if start < 0:
            raise ValueError(f"{token!r} absent de la ligne {line}")
        return self.span_box(line, start, len(token))


def highlight_rect(box, color, opacity=0.18):
    """Rectangle de surlignage à partir d'une boîte (centre, largeur, hauteur)."""
    center, w, h = box
    rect = Rectangle(width=w, height=h).move_to(center)
    return rect.set_fill(color, opacity).set_stroke(color, 1.5)


def flash(boxes, color, per_box):
    """Un carré qui flashe sur chaque boîte, l'une après l'autre."""
    square = Rectangle(width=1, height=1)
    n = len(boxes)

    def update(sq, alpha):
        i = min(int(alpha * n), n - 1)
        fade = 0.0 if alpha >= 1 else 1 - (alpha * n - i)
        center, w, h = boxes[i]
        sq.set_width(w, stretch=True).set_height(h, stretch=True).move_to(center)
        sq.set_fill(color, 0.28 * fade).set_stroke(color, 2, opacity=fade)

    update(square, 0)
    return UpdateFromAlphaFunc(
        square, update, run_time=n * per_box, rate_func=linear, remover=True
    )


class EditorPanel:
    """Une fenêtre d'éditeur : pastilles, nom de fichier, étiquette, zone de code."""

    def __init__(self, filename, center, width=6.85, height=5.2, tag=None, tag_color=DIM):
        box = RoundedRectangle(width=width, height=height, corner_radius=0.18)
        box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
        box.move_to(center)
        top, left, right = box.get_top()[1], box.get_left()[0], box.get_right()[0]
        dots = window_dots(0.065)
        dots.move_to([left + 0.28 + dots.get_width() / 2, top - 0.25, 0])
        fname = label(filename, 17, TXT, font=CODE_FONT).next_to(dots, RIGHT, buff=0.3)
        parts = [box, dots, fname]
        if tag:
            t = label(tag, 17, tag_color)
            t.move_to([right - 0.28 - t.get_width() / 2, top - 0.25, 0])
            parts.append(t)
        sep = Line([left, top - 0.5, 0], [right, top - 0.5, 0]).set_stroke(PANEL_STROKE, 1)
        parts.append(sep)
        self.box = box
        self.chrome = VGroup(*parts)
        self.code_left = left + 0.32
        self.code_top = top - 0.72
        self.code_w = width - 0.64
        self.code_h = height - 0.95

    def code_top_left(self):
        return np.array([self.code_left, self.code_top, 0])

    def fit_code(self, view, max_scale=1.0):
        w, h = view.size
        scale = min(max_scale, self.code_w / w, self.code_h / h)
        return view.fit(scale, self.code_top_left())


# ---------------------------------------------------------------------------
# La scène de base
# ---------------------------------------------------------------------------

class EpisodeScene(Scene):
    """Fond, titre fixe en haut à gauche, et puce de section au centre."""

    EPISODE = "00"
    TITLE = "Titre"

    def setup(self):
        super().setup()
        background = FullScreenRectangle().set_fill(BG, 1).set_stroke(width=0)
        header = markup(
            f'<span foreground="{ACCENT}"><b>Brigades Vertes</b></span>'
            f'<span foreground="{DIM}">  ·  {self.EPISODE}  {escape(self.TITLE, quote=False)}</span>',
            size=26,
        )
        header.to_corner(UL, buff=0.35)
        self.add(background, header)
        self.permanent = {background, header}
        self.chip = None

    def show_chip(self, text, color=ACCENT):
        chip = make_chip(text, color)
        if self.chip is None:
            self.play(FadeIn(chip, shift=0.15 * DOWN), run_time=0.6)
        else:
            self.play(FadeTransform(self.chip, chip), run_time=0.6)
        self.chip = chip

    def clear_stage(self, keep=(), run_time=0.6):
        keep = set(keep) | self.permanent | {self.chip}
        mobs = [m for m in self.mobjects if m not in keep]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=run_time)
