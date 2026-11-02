"""
Épisode 16 — Les tests Japa : traçabilité EXG et stratégie

Écrire un test qui porte son exigence et ne pollue pas la base, et connaître la stratégie.
  1. Un test porte son exigence : EXG-AUTH-004 dans la spec, puis LITTÉRALEMENT dans le libellé.
  2. Un test, de BEGIN à ROLLBACK : withGlobalTransaction, creerUtilisateur (en base, sans l'API),
     deux requêtes HTTP sur le serveur de test (port 3334), assertions, rollback.
  3. Lancer un seul fichier (--files=session) ou un seul test (--tests="titre exact").
  4. La stratégie : unitaires (7) / fonctionnels (3 + 7 + 12) = 29 tests ; « un invariant métier a
     droit aux deux » ; 70 % exigé mais non mesuré ; TODO-EXG ; zéro test côté sdk et web.

Sources : server/tests/functional/session.spec.ts (l. 25-26, 114-144), server/tests/helpers.ts,
server/tests/bootstrap.ts, server/.env.test (PORT=3334), server/adonisrc.ts (suites),
docs/specs/session.md, docs/tmp/plan-boilerplate-speedcoding.md (« Le découpage des tests »),
scripts/feature.mjs (TODO-EXG), scripts/verifier.mjs (étape « tests serveur »), sdk/package.json.
Filtres Japa vérifiés dans le code source de Japa : --tests compare le titre exact
(@japa/core, refiner : `filters.tests.includes(test.title)`), --files accepte une fin de chemin.

Rendu vidéo :  manimgl ep16_tests_japa.py Ep16TestsJapa -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


# ---------------------------------------------------------------------------
# Briques propres à cet épisode
# ---------------------------------------------------------------------------

class Excerpt(CodeView):
    """Un CodeView dont la numérotation commence à `first` (extrait d'un vrai fichier)."""

    def __init__(self, source, lexer_names, first=1, font_size=BASE_FS):
        spans = highlight_lines(source, lexer_names)
        cal = MarkupText(STRUT * 20, font=CODE_FONT, font_size=font_size)
        self.adv = cal.get_width() / 20
        self.block_h = cal.get_height()
        self.line_h = self.block_h * LINE_SPACING
        self.text = source.split("\n")
        cols = max(2, len(str(first + len(spans) - 1)))
        self.gutter, self.lines = VGroup(), VGroup()
        self.gutter_struts, self.code_struts = [], []
        code_x = (cols + GUTTER_GAP) * self.adv
        for i, line_markup in enumerate(spans):
            y = -i * self.line_h
            num, num_strut = make_line(f'<span foreground="{DIM}">{first + i:>{cols}}</span>', font_size)
            place(num, num_strut, 0, y)
            self.gutter.add(num)
            self.gutter_struts.append(num_strut)
            code, code_strut = make_line(line_markup, font_size)
            place(code, code_strut, code_x, y)
            self.lines.add(code)
            self.code_struts.append(code_strut)
        self.group = VGroup(self.gutter, self.lines)


def code_panel(filename, source, lexer, x, top, width, height=None, first=1, tag=None,
               tag_color=DIM, max_scale=0.8, gutter=True):
    """Une fenêtre d'éditeur, haut en `top`, centrée en `x`, et son code.

    Sans `height`, la fenêtre prend la hauteur de son code. `gutter=False` masque les
    numéros de ligne : pour un extrait raccourci, de vrais numéros mentiraient.
    Renvoie (panneau, vue, groupe affichable)."""
    view = Excerpt(source, [lexer], first)
    gutter_w = view.code_struts[0].get_left()[0] - view.gutter_struts[0].get_left()[0]
    w, h = view.size
    if not gutter:
        w -= gutter_w
    code_w = width - 0.64
    if height is None:
        height = h * min(max_scale, code_w / w) + 1.1
    panel = EditorPanel(filename, [x, top - height / 2, 0], width, height, tag, tag_color)
    scale = min(max_scale, panel.code_w / w, panel.code_h / h)
    if scale < 0.58:
        print(f"[code_panel] {filename} : code petit (échelle {scale:.2f})", file=sys.stderr)
    view.fit(scale, panel.code_top_left())
    if not gutter:
        view.gutter.set_opacity(0)
        view.lines.shift(gutter_w * scale * LEFT)
    return panel, view, VGroup(panel.chrome, view.group)


def http_pill(method, path, color=BLUE, size=18):
    m = label(method, size, BG, font=MONO_FONT, bold=True)
    m_bg = RoundedRectangle(width=m.get_width() + 0.24, height=0.36, corner_radius=0.08)
    m_bg.set_fill(color, 1).set_stroke(width=0)
    m.move_to(m_bg)
    p = label(path, size, TXT, font=MONO_FONT)
    row = VGroup(VGroup(m_bg, m), p).arrange(RIGHT, buff=0.2)
    bg = RoundedRectangle(width=row.get_width() + 0.3, height=0.56, corner_radius=0.12)
    bg.set_fill(PANEL_BG, 1).set_stroke(color, 1.5).move_to(row)
    return VGroup(bg, row)


def badge(text, color, size=18):
    t = label(text, size, color, font=MONO_FONT, bold=True)
    bg = RoundedRectangle(width=t.get_width() + 0.4, height=t.get_height() + 0.26, corner_radius=0.1)
    bg.set_fill(color, 0.15).set_stroke(color, 1.5)
    t.move_to(bg)
    return VGroup(bg, t)


def caption(text, point, color=DIM, size=16):
    return fit_x(label(text, size, color).move_to(point))


def cross_at(point, size=30):
    return label("✖", size, ERROR, bold=True).move_to(point)


def db_row(text, color=TXT):
    t = label(text, 15, color, font=MONO_FONT)
    bg = Rectangle(width=3.2, height=0.36).set_fill(color, 0.08).set_stroke(PANEL_STROKE, 1)
    t.move_to(bg)
    return VGroup(bg, t)


def cylinder(width=0.55, height=0.6, color=DIM):
    body = Rectangle(width=width, height=height).set_fill(PANEL_BG, 1).set_stroke(width=0)
    top = Ellipse(width=width, height=0.2).set_fill(PANEL_BG, 1).set_stroke(color, 1.5)
    top.move_to(body.get_top())
    bottom = Ellipse(width=width, height=0.2).set_stroke(color, 1.5).move_to(body.get_bottom())
    sides = VGroup(Line(body.get_corner(UL), body.get_corner(DL)), Line(body.get_corner(UR), body.get_corner(DR)))
    sides.set_stroke(color, 1.5)
    return VGroup(body, bottom, sides, top)


# ---------------------------------------------------------------------------
# Extraits (copiés du dépôt, raccourcis par « … »)
# ---------------------------------------------------------------------------

TEST_SESSION = """\
test.group('Session', (group) => {
  group.each.setup(() => testUtils.db().withGlobalTransaction())
  …
  test('EXG-AUTH-004 — email inconnu et mot de passe erroné sont indiscernables', …
    await creerUtilisateur({ email: 'claire@calanques.fr' })

    const mauvaisMotDePasse = await client
      .post('/api/v1/session/connexion')
      .json({ email: 'claire@calanques.fr', password: 'cenestpaslebon' })

    const emailInconnu = await client
      .post('/api/v1/session/connexion')
      .json({ email: 'personne@calanques.fr', password: 'cenestpaslebon' })

    mauvaisMotDePasse.assertStatus(401)
    emailInconnu.assertStatus(401)
    assert.deepEqual(mauvaisMotDePasse.body(), emailInconnu.body())
  })
})"""

CONSOLE = """\
$ cd server
$ npm test -- --files=session
$ npm test -- --tests="EXG-AUTH-004 — email inconnu et mot de passe erroné sont indiscernables\""""


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep16TestsJapa(EpisodeScene):
    EPISODE = "16"
    TITLE = "Les tests Japa"

    def construct(self):
        self.tracabilite()
        self.deroule()
        self.lancer()
        self.strategie()

    # --- 1. Un test porte son EXG ----------------------------------------------------

    def tracabilite(self):
        self.show_chip("Un test porte son exigence")

        spec_box = RoundedRectangle(width=6.6, height=1.5, corner_radius=0.14)
        spec_box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5).move_to([-3.5, 1.2, 0])
        spec = VGroup(
            label("docs/specs/session.md", 17, DIM, font=MONO_FONT),
            markup(f'<span foreground="{GOLD}"><b>EXG-AUTH-004</b></span>'
                   f'<span foreground="{TXT}">  Ne jamais révéler si un email existe</span>', 21),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to(spec_box)

        test_box = RoundedRectangle(width=7.4, height=1.75, corner_radius=0.14)
        test_box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5).move_to([3.0, -0.9, 0])
        test = VGroup(
            label("server/tests/functional/session.spec.ts", 17, DIM, font=MONO_FONT),
            markup(f'<span foreground="{TXT}">test(\'</span><span foreground="{GOLD}"><b>EXG-AUTH-004</b></span>'
                   f'<span foreground="{TXT}"> — email inconnu et mot de passe</span>', 19, font=MONO_FONT),
            label("erroné sont indiscernables', …", 19, TXT, font=MONO_FONT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).move_to(test_box)

        self.play(FadeIn(spec_box), FadeIn(spec), run_time=0.7)
        self.play(FadeIn(test_box), FadeIn(test), run_time=0.7)
        exg_spec = spec[1][:12]
        exg_test = test[1][6:18]
        end = np.array([exg_test.get_x(), test_box.get_top()[1] + 0.04, 0])
        thread = CubicBezier(
            exg_spec.get_bottom() + 0.1 * DOWN,
            exg_spec.get_bottom() + 1.4 * DOWN,
            end + 1.4 * UP,
            end,
        ).set_stroke(GOLD, 2.5)
        self.play(ShowCreation(thread), run_time=0.9)
        self.play(FadeIn(SurroundingRectangle(exg_spec, buff=0.06).set_stroke(GOLD, 1.5)),
                  FadeIn(SurroundingRectangle(exg_test, buff=0.06).set_stroke(GOLD, 1.5)), run_time=0.5)
        note = VGroup(
            label("l'identifiant figure LITTÉRALEMENT dans le libellé du test :", 18, TXT),
            label("la matrice de traçabilité se vérifie par une simple recherche", 18, DIM),
        ).arrange(DOWN, buff=0.12).move_to([0, -2.7, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.wait(3.4)
        self.clear_stage()

    # --- 2. Un test, de BEGIN à ROLLBACK ------------------------------------------------

    def deroule(self):
        self.show_chip("Un test, de BEGIN à ROLLBACK", VIOLET)

        _, cv, code = code_panel(
            "server/tests/functional/session.spec.ts", TEST_SESSION, "typescript",
            -2.3, 2.5, 9.3, max_scale=0.7, gutter=False,
        )
        self.play(FadeIn(code), run_time=0.7)

        steps_data = [
            ("BEGIN", "une transaction par test", ACCENT, [2]),
            ("INSERT", "creerUtilisateur : en base, sans l'API", GOLD, [5]),
            ("HTTP", "vraies requêtes, serveur de test :3334", BLUE, [7, 8, 9, 11, 12, 13]),
            ("assert", "401, 401, et corps identiques", VIOLET, [15, 16, 17]),
            ("ROLLBACK", "rien n'est écrit pour de bon", ERROR, [18]),
        ]
        x0 = 4.75
        steps = VGroup()
        for k, (tag, desc, color, _) in enumerate(steps_data):
            t = label(tag, 18, color, font=MONO_FONT, bold=True)
            d = label(desc, 15, TXT)
            card = VGroup(t, d).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
            box = RoundedRectangle(width=4.4, height=0.7, corner_radius=0.1)
            box.set_fill(color, 0.07).set_stroke(color, 1.3)
            card.move_to(box).align_to(box, LEFT).shift(0.15 * RIGHT)
            steps.add(VGroup(box, card).move_to([x0, 2.15 - k * 0.8, 0]))

        # La base de test
        db = cylinder().move_to([3.15, -2.65, 0])
        db_lbl = label("base de test", 14, DIM).next_to(db, DOWN, buff=0.12)
        row = db_row("claire@calanques.fr").move_to([5.3, -2.55, 0])
        self.play(FadeIn(db), FadeIn(db_lbl), run_time=0.5)

        hls = VGroup()
        for k, (tag, desc, color, lines) in enumerate(steps_data):
            new_hls = VGroup(*[highlight_rect(cv.line_box(i), color, 0.14) for i in lines])
            anims = [FadeIn(steps[k], shift=0.1 * LEFT), FadeOut(hls), FadeIn(new_hls)]
            if tag == "INSERT":
                anims.append(FadeIn(row, shift=0.2 * LEFT))
            if tag == "ROLLBACK":
                anims.append(FadeOut(row, shift=0.2 * RIGHT))
            self.play(*anims, run_time=0.7)
            if tag == "HTTP":
                pk = packet(BLUE, 0.08).move_to(steps[k].get_left() + 0.1 * LEFT)
                self.add(pk)
                self.play(pk.animate.move_to(db.get_top()), run_time=0.6)
                self.remove(pk)
            hls = new_hls
            self.wait(2.1 if tag != "ROLLBACK" else 1.2)
        note = caption("la base locale ressort intacte : tes comptes de développement survivent à npm test",
                       [0, -3.65, 0], TXT, 16)
        self.play(FadeOut(hls), FadeIn(note), run_time=0.6)
        self.wait(3.0)
        self.clear_stage()

    # --- 3. Lancer un seul fichier, ou un seul test ---------------------------------------

    def lancer(self):
        self.show_chip("Lancer un seul fichier, ou un seul test", BLUE)
        _, cv, console = code_panel("terminal", CONSOLE, "bash", 0, 2.3, 13.2, max_scale=0.8,
                                    gutter=False)
        self.play(FadeIn(console.submobjects[0]), run_time=0.5)
        self.play(FadeIn(cv.lines[0]), run_time=0.4)
        self.play(FadeIn(cv.lines[1]), run_time=0.6)
        files_note = VGroup(
            markup(f'<span foreground="{ACCENT}"><b>--files</b></span>'
                   f'<span foreground="{TXT}">  la fin du chemin suffit : session → '
                   f'tests/functional/session.spec.ts</span>', 18),
        ).move_to([0, -0.15, 0])
        fit_x(files_note)
        self.play(FadeIn(files_note), run_time=0.5)
        self.wait(0.8)
        self.wait(2.2)
        self.play(FadeIn(cv.lines[2]), run_time=0.7)
        tests_note = VGroup(
            markup(f'<span foreground="{WARN}"><b>--tests</b></span>'
                   f'<span foreground="{TXT}">  compare le titre EXACT, en entier</span>', 18),
            label("--tests=\"EXG-AUTH-004\" seul ne trouve rien", 17, DIM, font=MONO_FONT),
        ).arrange(DOWN, buff=0.15).move_to([0, -1.2, 0])
        self.play(FadeIn(tests_note), run_time=0.6)
        self.wait(2.6)
        ci = markup(f'<span foreground="{DIM}">et tous les tests tournent dans </span>'
                    f'<span foreground="{ACCENT}">npm run verifier</span>'
                    f'<span foreground="{DIM}">, étape « tests serveur » : la CI est locale</span>', 17)
        ci.move_to([0, -2.6, 0])
        fit_x(ci)
        self.play(FadeIn(ci), run_time=0.6)
        self.wait(3.0)
        self.clear_stage()

    # --- 4. La stratégie --------------------------------------------------------------------

    def strategie(self):
        self.show_chip("La stratégie", GOLD)

        def column(title, path, desc, files, color, x):
            head = label(title, 24, color, bold=True)
            p = label(path, 15, DIM, font=MONO_FONT)
            d = label(desc, 16, DIM)
            rows = VGroup(*[
                VGroup(label(f, 17, TXT, font=MONO_FONT), label(str(n), 19, color, bold=True))
                for f, n in files
            ])
            rows.arrange(DOWN, buff=0.14, aligned_edge=LEFT)
            num_x = max(r[0].get_right()[0] for r in rows) + 0.5
            for r in rows:
                r[1].move_to([num_x, r[0].get_y(), 0])
            g = VGroup(head, p, d, rows).arrange(DOWN, buff=0.16)
            box = RoundedRectangle(width=5.6, height=2.7, corner_radius=0.15)
            box.set_fill(color, 0.05).set_stroke(color, 1.5)
            box.move_to([x, 0.95, 0])
            g.move_to(box)
            return VGroup(box, g), rows

        unit, unit_rows = column("unitaires", "tests/unit/", "fonctions pures, sans base, en millisecondes",
                                 [("horodatage.spec.ts", 7)], ACCENT, -3.2)
        func, func_rows = column("fonctionnels", "tests/functional/",
                                 "HTTP réel, middleware de contrat actif",
                                 [("contract.spec.ts", 3), ("session.spec.ts", 7),
                                  ("utilisateurs.spec.ts", 12)], VIOLET, 3.2)
        self.play(FadeIn(unit, shift=0.1 * UP), FadeIn(func, shift=0.1 * UP), run_time=0.9)
        self.wait(1.5)
        total = markup(f'<span foreground="{TXT}"><b>29 tests</b></span>'
                       f'<span foreground="{DIM}">  au total, tous côté serveur</span>', 20)
        total.move_to([0, -0.75, 0])
        self.play(FadeIn(total), run_time=0.5)
        rule = label("Un invariant métier a droit aux deux : la règle pure en unitaire, "
                     "le 403 ou le 409 prouvé en fonctionnel.", 17, GOLD)
        rule.move_to([0, -1.35, 0])
        fit_x(rule)
        if rule.get_width() > 13.6:
            rule.set_width(13.6)
        self.play(FadeIn(rule), run_time=0.6)
        self.wait(2.8)

        cards_data = [
            ("≥ 70 %", "de couverture exigés,", "non mesurés : pas de c8", WARN),
            ("TODO-EXG", "libellés générés par npm run feature,", "à remplacer par le vrai EXG", GOLD),
            ("0 test", "côté sdk et web :", "aucun runner installé", ERROR),
        ]
        cards = VGroup()
        for big, l1, l2, color in cards_data:
            box = RoundedRectangle(width=4.3, height=1.45, corner_radius=0.14)
            box.set_fill(PANEL_BG, 1).set_stroke(color, 1.5)
            g = VGroup(label(big, 24, color, bold=True), label(l1, 16, TXT), label(l2, 16, DIM))
            g.arrange(DOWN, buff=0.08).move_to(box)
            cards.add(VGroup(box, g))
        cards.arrange(RIGHT, buff=0.3).move_to([0, -2.9, 0])
        self.play(LaggedStartMap(FadeIn, cards, shift=0.15 * UP, lag_ratio=0.3), run_time=1.2)
        self.wait(4.5)
