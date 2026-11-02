"""
Prettier vs ESLint — animation ManimGL (3b1b/manim)

Deux "divs" côte à côte : un composant React et un contrôleur AdonisJS.
  0. Les deux fichiers partent non formatés.
  1. Passe Prettier : un curseur flashe mot par mot et reformate chaque ligne
     dès qu'il l'a parcourue (même logique, mêmes bugs).
  2. Passe ESLint : le curseur flashe ligne par ligne sans rien changer, et
     chaque ligne fautive envoie sa sortie dans la console.

Rendu vidéo :  manimgl prettier_vs_eslint.py PrettierVsESLint -w
Aperçu      :  manimgl prettier_vs_eslint.py PrettierVsESLint

Dépendances : manimgl (qui installe déjà pygments).
Le code formaté correspond à la sortie de Prettier avec sa config par défaut
(guillemets doubles, points-virgules, printWidth 80).
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
# Réglages
# ---------------------------------------------------------------------------

CODE_FONT = "DejaVu Sans Mono"   # n'importe quelle police monospace installée
UI_FONT = "Sans"
CODE_STYLE = "monokai"           # style pygments pour la coloration
BASE_FS = 24                     # taille de construction (tout est rescalé ensuite)
LINE_SPACING = 1.12
GUTTER_COLS = 2                  # largeur des numéros de ligne
GUTTER_GAP = 2                   # espace entre numéros et code

# Glyphe "étai" invisible placé en début de chaque ligne : il donne à toutes
# les lignes la même hauteur et le même point d'origine, ce qui préserve
# l'indentation et permet de calculer la position exacte d'une colonne.
STRUT = "█"  # █

BG = "#14151C"
PANEL_BG = "#1E1F29"
PANEL_STROKE = "#3A3C4E"
TXT = "#E6E6E6"
DIM = "#7A7F99"
PRETTIER = "#F7B93E"
ESLINT = "#8C7CF0"
OK_GREEN = "#4EC9B0"
SEVERITY = {
    "error": ("✖", "#F14C4C"),    # ✖
    "warning": ("▲", "#E2B714"),  # ▲
}

PANEL_W = 6.85
PANEL_H = 5.75
PANEL_Y = -0.72
PANEL_X = 3.55
CHIP_Y = 2.62
PROBLEMS_H = 1.38

WORD_FLASH = 0.02    # durée du flash sur un mot (passe Prettier)
LINE_FLASH = 0.1    # durée du flash sur une ligne (passe ESLint)
LINE_SNAP = 0.1     # durée du reformatage d'une ligne
WORD_RE = re.compile(r"[\w$#@.]+|[^\w\s]+")

# Par défaut ManimGL repeint tout MarkupText en blanc après l'avoir construit,
# ce qui efface les <span foreground=...> : ces options gardent leurs couleurs.
KEEP_SPAN_COLORS = dict(fill_color=None, stroke_color=None)


# ---------------------------------------------------------------------------
# Les deux exemples
# ---------------------------------------------------------------------------

REACT = dict(
    filename="UserCard.jsx",
    tag="React",
    tag_color="#61DAFB",
    lexers=("jsx", "tsx", "javascript"),
    messy="\n".join([
        "import {useState,useEffect} from 'react'",
        "export default function UserCard({user}){",
        "const [count,setCount]=useState(0)",
        "    if(user.isAdmin){const [open,setOpen]=useState(false)}",
        "  return <div onClick={()=>setCount(count+1)}>",
        "<h2>{user.name}</h2>",
        "      <p>Clicks: {count}</p></div>",
        "}",
    ]),
    formatted="\n".join([
        'import { useState, useEffect } from "react";',
        "export default function UserCard({ user }) {",
        "  const [count, setCount] = useState(0);",
        "  if (user.isAdmin) {",
        "    const [open, setOpen] = useState(false);",
        "  }",
        "  return (",
        "    <div onClick={() => setCount(count + 1)}>",
        "      <h2>{user.name}</h2>",
        "      <p>Clicks: {count}</p>",
        "    </div>",
        "  );",
        "}",
    ]),
    # nombre de lignes formatées produites par chaque ligne non formatée
    line_map=[1, 1, 1, 3, 2, 1, 2, 2],
    issues=[
        dict(line=1, token="useEffect", sev="warning",
             msg="'useEffect' is defined but never used",
             rule="no-unused-vars"),
        dict(line=5, token="open", sev="warning",
             msg="'open' is assigned a value but never used",
             rule="no-unused-vars"),
        dict(line=5, token="useState", sev="error",
             msg='React Hook "useState" is called conditionally',
             rule="react-hooks/rules-of-hooks"),
    ],
)

ADONIS = dict(
    filename="users_controller.ts",
    tag="AdonisJS",
    tag_color="#8A7CFF",
    lexers=("typescript", "javascript"),
    messy="\n".join([
        "import type {HttpContext} from '@adonisjs/core/http'",
        "import User from '#models/user'",
        "export default class UsersController{",
        "async destroy({params,response}:HttpContext){",
        "const user=await User.findOrFail(params.id)",
        "      user.delete()",
        "  if(user.role=='admin'){console.log('deleted')}",
        "return response.noContent()}",
        "}",
    ]),
    formatted="\n".join([
        'import type { HttpContext } from "@adonisjs/core/http";',
        'import User from "#models/user";',
        "export default class UsersController {",
        "  async destroy({ params, response }: HttpContext) {",
        "    const user = await User.findOrFail(params.id);",
        "    user.delete();",
        '    if (user.role == "admin") {',
        '      console.log("deleted");',
        "    }",
        "    return response.noContent();",
        "  }",
        "}",
    ]),
    line_map=[1, 1, 1, 1, 1, 1, 3, 2, 1],
    issues=[
        dict(line=6, token="user.delete()", sev="error",
             msg="Promises must be awaited…",
             rule="@typescript-eslint/no-floating-promises"),
        dict(line=7, token="==", sev="error",
             msg="Expected '===' and instead saw '=='",
             rule="eqeqeq"),
        dict(line=8, token="console.log", sev="warning",
             msg="Unexpected console statement",
             rule="no-console"),
    ],
)


# ---------------------------------------------------------------------------
# Coloration syntaxique -> une chaîne de markup Pango par ligne
# ---------------------------------------------------------------------------

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
    color = style.style_for_token(ttype)["color"]
    return f"#{color}" if color else default


def highlight_lines(source, lexer_names):
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


def issue_column(source, issue):
    """Colonne ESLint (base 1) du token signalé dans le code formaté."""
    line_text = source.split("\n")[issue["line"] - 1]
    idx = line_text.find(issue["token"])
    if idx < 0:
        raise ValueError(f"Token {issue['token']!r} absent de la ligne {issue['line']}")
    return idx + 1


# ---------------------------------------------------------------------------
# Briques visuelles
# ---------------------------------------------------------------------------

def make_line(markup, font_size, font=CODE_FONT):
    """MarkupText précédé d'un étai invisible. Renvoie (ligne, étai)."""
    mob = MarkupText(
        f'<span foreground="{TXT}">{STRUT}</span>{markup}',
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

    def __init__(self, source, lexer_names, font_size=BASE_FS):
        spans = highlight_lines(source, lexer_names)
        cal = MarkupText(STRUT * 20, font=CODE_FONT, font_size=font_size)
        self.adv = cal.get_width() / 20
        self.block_h = cal.get_height()
        self.line_h = self.block_h * LINE_SPACING

        self.gutter = VGroup()
        self.lines = VGroup()
        self.gutter_struts = []
        self.code_struts = []
        code_x = (GUTTER_COLS + GUTTER_GAP) * self.adv
        for i, markup in enumerate(spans):
            y = -i * self.line_h
            num, num_strut = make_line(
                f'<span foreground="{DIM}">{i + 1:>{GUTTER_COLS}}</span>', font_size
            )
            code, code_strut = make_line(markup, font_size)
            place(num, num_strut, 0, y)
            place(code, code_strut, code_x, y)
            self.gutter.add(num)
            self.lines.add(code)
            self.gutter_struts.append(num_strut)
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

    # --- géométrie (valable une fois fit() appelé) ---
    def line_y(self, line):
        return self.code_struts[line - 1].get_center()[1]

    def col_x(self, line, col):
        # l'étai occupe la colonne 0, la colonne ESLint c commence c avances plus loin
        return self.code_struts[line - 1].get_left()[0] + col * self.adv

    def gutter_x(self):
        return self.gutter_struts[0].get_left()[0]

    def span_box(self, line, start, length):
        """(centre, largeur, hauteur) des caractères [start, start+length) d'une ligne."""
        x0 = self.col_x(line, start + 1)
        center = np.array([x0 + length * self.adv / 2, self.line_y(line), 0])
        return center, length * self.adv + 0.06, self.block_h * 1.08

    def word_boxes(self, line, text):
        return [self.span_box(line, m.start(), len(m.group())) for m in WORD_RE.finditer(text)]

    def line_box(self, line, text):
        start = len(text) - len(text.lstrip())
        return self.span_box(line, start, len(text.strip()))


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


def squiggle(x0, x1, y, color, amp, period):
    n = max(16, int((x1 - x0) / period * 14))
    xs = np.linspace(x0, x1, n)
    pts = [np.array([x, y + amp * np.sin(TAU * (x - x0) / period), 0]) for x in xs]
    wave = VMobject()
    wave.set_points_as_corners(pts)
    wave.set_stroke(color, 2.2)
    wave.set_fill(opacity=0)
    return wave


def make_chip(label, detail, color):
    lab = MarkupText(f"<b>{escape(label, quote=False)}</b>", font=UI_FONT, font_size=26)
    lab.set_color(color)
    det = Text(detail, font=CODE_FONT, font_size=21)
    det.set_color(TXT)
    row = VGroup(lab, det).arrange(RIGHT, buff=0.4)
    bg = RoundedRectangle(
        width=row.get_width() + 0.6, height=row.get_height() + 0.32, corner_radius=0.16
    )
    bg.set_fill(color, 0.12).set_stroke(color, 1.5)
    row.move_to(bg)
    chip = VGroup(bg, row)
    chip.move_to([0, CHIP_Y, 0])
    return chip


class Panel:
    """La "div" : fenêtre d'éditeur avec en-tête, zone de code et zone problèmes."""

    def __init__(self, cfg, center_x):
        self.cfg = cfg
        box = RoundedRectangle(width=PANEL_W, height=PANEL_H, corner_radius=0.18)
        box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
        box.move_to([center_x, PANEL_Y, 0])
        self.box = box
        top, bottom = box.get_top()[1], box.get_bottom()[1]
        left, right = box.get_left()[0], box.get_right()[0]

        dots = VGroup(*[
            Circle(radius=0.065).set_fill(c, 1).set_stroke(width=0)
            for c in ("#FF5F57", "#FEBC2E", "#28C840")
        ]).arrange(RIGHT, buff=0.1)
        dots.move_to([left + 0.28 + dots.get_width() / 2, top - 0.25, 0])

        fname = Text(cfg["filename"], font=CODE_FONT, font_size=19)
        fname.set_color(TXT)
        fname.next_to(dots, RIGHT, buff=0.3)

        tag = Text(cfg["tag"], font=UI_FONT, font_size=19)
        tag.set_color(cfg["tag_color"])
        tag.move_to([right - 0.28 - tag.get_width() / 2, top - 0.25, 0])
        self.tag = tag

        sep = Line([left, top - 0.5, 0], [right, top - 0.5, 0]).set_stroke(PANEL_STROKE, 1)
        self.chrome = VGroup(box, dots, fname, tag, sep)

        # zones
        self.code_left = left + 0.32
        self.code_right = right - 0.32
        self.code_top = top - 0.72
        self.code_w = self.code_right - self.code_left
        self.problems_top = bottom + PROBLEMS_H
        self.code_h = self.code_top - self.problems_top - 0.15

        self.problems_sep = Line(
            [left, self.problems_top, 0], [right, self.problems_top, 0]
        ).set_stroke(PANEL_STROKE, 1)
        header = Text("PROBLÈMES", font=UI_FONT, font_size=15)
        header.set_color(DIM)
        header.move_to(
            [self.code_left + header.get_width() / 2, self.problems_top - 0.22, 0]
        )
        self.problems_header = header
        self.count = self.make_count(0)

        self.messy = CodeView(cfg["messy"], cfg["lexers"])
        self.formatted = CodeView(cfg["formatted"], cfg["lexers"])

    def make_count(self, n):
        color = DIM if n == 0 else SEVERITY["error"][1]
        badge = Text(str(n), font=UI_FONT, font_size=15)
        badge.set_color(color)
        badge.next_to(self.problems_header, RIGHT, buff=0.15)
        return badge

    def code_top_left(self):
        return np.array([self.code_left, self.code_top, 0])

    def build_problem_items(self, font_size=18):
        src = self.cfg["formatted"]
        items = []
        for issue in self.cfg["issues"]:
            icon, color = SEVERITY[issue["sev"]]
            col = issue_column(src, issue)
            markup = (
                f'<span foreground="{color}">{icon}</span>  '
                f'<span foreground="{DIM}">{issue["line"]}:{col}</span>  '
                f'<span foreground="{TXT}">{escape(issue["msg"], quote=False)}</span>  '
                f'<span foreground="{DIM}">{escape(issue["rule"], quote=False)}</span>'
            )
            items.append(make_line(markup, font_size))
        return items

    def layout_problem_items(self, items, scale):
        y0 = self.problems_header.get_bottom()[1] - 0.2
        for k, (mob, strut) in enumerate(items):
            mob.scale(scale, about_point=ORIGIN)
            step = strut.get_height() * 1.18
            place(mob, strut, self.code_left - strut.get_width(), y0 - k * step)
        return [mob for mob, _ in items]


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class PrettierVsESLint(Scene):
    def construct(self):
        self.add(FullScreenRectangle().set_fill(BG, 1).set_stroke(width=0))

        panels = [Panel(REACT, -PANEL_X), Panel(ADONIS, PANEL_X)]

        # Une seule échelle pour les 4 blocs, pour que la police soit identique partout
        scale = min(
            min(p.code_w / view.size[0], p.code_h / view.size[1])
            for p in panels
            for view in (p.messy, p.formatted)
        )
        scale = min(scale, 1.0)
        for p in panels:
            p.messy.fit(scale, p.code_top_left())
            p.formatted.fit(scale, p.code_top_left())

        # Liste des problèmes : une échelle commune pour que tout tienne en largeur
        raw_items = [p.build_problem_items() for p in panels]
        item_scale = min(
            1.0,
            min(
                p.code_w / mob.get_width()
                for p, items in zip(panels, raw_items)
                for mob, _ in items
            ),
        )
        problem_items = [
            p.layout_problem_items(items, item_scale)
            for p, items in zip(panels, raw_items)
        ]

        # ---------------- 0. Intro : code non formaté ----------------
        title = MarkupText(
            f'<span foreground="{PRETTIER}"><b>Prettier</b></span>'
            f'<span foreground="{DIM}">  +  </span>'
            f'<span foreground="{ESLINT}"><b>ESLint</b></span>',
            **KEEP_SPAN_COLORS,
            font=UI_FONT,
            font_size=40,
        )
        title.to_corner(UL, buff=0.35)
        self.add(title)
        chip = make_chip("Avant", "code non formaté", DIM)

        self.play(
            LaggedStart(*[FadeIn(p.chrome, shift=0.2 * UP) for p in panels], lag_ratio=0.25),
            FadeIn(chip),
            run_time=1.2,
        )
        self.play(
            *[FadeIn(p.messy.gutter) for p in panels],
            *[
                LaggedStartMap(FadeIn, p.messy.lines, shift=0.1 * RIGHT, lag_ratio=0.12)
                for p in panels
            ],
            run_time=2,
        )
        self.wait(1.5)

        # ---------------- 1. Passe Prettier ----------------
        chip1 = make_chip("1 · Prettier", "$ prettier --write .", PRETTIER)
        self.play(FadeTransform(chip, chip1))
        chip = chip1

        # Le curseur flashe mot par mot ; chaque ligne parcourue est reformatée
        # aussitôt, et les lignes suivantes descendent pour lui faire de la place.
        messy_text = [p.cfg["messy"].split("\n") for p in panels]
        placed = [0 for _ in panels]   # lignes formatées déjà en place
        for k in range(max(len(t) for t in messy_text)):
            active = [i for i, t in enumerate(messy_text) if k < len(t)]
            self.play(*[
                flash(panels[i].messy.word_boxes(k + 1, messy_text[i][k]), PRETTIER, WORD_FLASH)
                for i in active
            ])

            anims = []
            for i in active:
                p = panels[i]
                n = p.cfg["line_map"][k]
                new = slice(placed[i], placed[i] + n)
                placed[i] += n
                anims += [
                    TransformMatchingShapes(p.messy.lines[k], VGroup(*p.formatted.lines[new])),
                    FadeOut(p.messy.gutter[k]),
                    *[FadeIn(g) for g in p.formatted.gutter[new]],
                ]
                if n > 1:
                    offset = (n - 1) * p.formatted.line_h * DOWN
                    rest = [*p.messy.lines[k + 1:], *p.messy.gutter[k + 1:]]
                    anims += [m.animate.shift(offset) for m in rest]
            self.play(*anims, run_time=LINE_SNAP)

        badges = []
        for p in panels:
            badge = Text("✔ formaté", font=UI_FONT, font_size=16)
            badge.set_color(OK_GREEN)
            badge.next_to(p.tag, LEFT, buff=0.3)
            badges.append(badge)
        self.play(*[FadeIn(b, scale=0.7) for b in badges])
        self.wait(1.2)

        # ---------------- 2. Passe ESLint ----------------
        chip2 = make_chip("2 · ESLint", "$ eslint .", ESLINT)
        self.play(FadeTransform(chip, chip2))
        chip = chip2

        self.play(
            *[ShowCreation(p.problems_sep) for p in panels],
            *[FadeIn(VGroup(p.problems_header, p.count)) for p in panels],
            run_time=0.6,
        )

        # Le curseur flashe ligne par ligne sans toucher au code ; quand une
        # ligne pose problème, sa sortie part dans la console.
        formatted_text = [p.cfg["formatted"].split("\n") for p in panels]
        counts = [0 for _ in panels]

        for ln in range(1, max(len(t) for t in formatted_text) + 1):
            self.play(*[
                flash([p.formatted.line_box(ln, t[ln - 1])], ESLINT, LINE_FLASH)
                for p, t in zip(panels, formatted_text)
                if ln <= len(t)
            ])

            anims = []
            for idx, p in enumerate(panels):
                found = [k for k, issue in enumerate(p.cfg["issues"]) if issue["line"] == ln]
                if not found:
                    continue
                anims += self.mark_line(p, ln, p.cfg["issues"][found[0]]["sev"])
                for k in found:
                    anims.append(self.squiggle_issue(p, p.cfg["issues"][k]))
                    anims.append(FadeIn(problem_items[idx][k], shift=0.2 * RIGHT))
                counts[idx] += len(found)
                new_count = p.make_count(counts[idx])
                anims.append(FadeTransform(p.count, new_count))
                p.count = new_count
            if anims:
                self.play(*anims, run_time=0.8)
                self.wait(0.4)

        self.wait(4)

    def mark_line(self, p, ln, sev):
        """Bande de couleur derrière la ligne fautive + pastille dans la marge."""
        view = p.formatted
        _, color = SEVERITY[sev]
        y = view.line_y(ln)
        band = Rectangle(width=p.code_w + 0.2, height=view.line_h)
        band.set_fill(color, 0.14).set_stroke(width=0)
        band.move_to([(p.code_left + p.code_right) / 2, y, 0])
        self.add(band)
        self.bring_to_front(view.group)
        dot = Dot(radius=0.045).set_fill(color, 1)
        dot.move_to([view.gutter_x() - 0.13, y, 0])
        return [FadeIn(band), FadeIn(dot, scale=0.4)]

    def squiggle_issue(self, p, issue):
        view = p.formatted
        _, color = SEVERITY[issue["sev"]]
        ln = issue["line"]
        x0 = view.col_x(ln, issue_column(p.cfg["formatted"], issue))
        x1 = x0 + len(issue["token"]) * view.adv
        wave = squiggle(
            x0, x1, view.line_y(ln) - 0.47 * view.block_h, color,
            amp=0.022, period=view.adv * 1.4,
        )
        return ShowCreation(wave)
