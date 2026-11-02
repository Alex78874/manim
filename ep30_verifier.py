"""
Épisode 30 — `npm run verifier` : la barrière

Bloc F : une fonctionnalité de bout en bout. La CI est locale, par décision :
`npm run verifier` EST la CI, lancée sur le poste avant chaque push.
  1. La CI est locale : ton poste → npm run verifier → git push.
  2. Un pré-vol (node ace migration:status, silencieux s'il passe), puis sept
     étapes par coût croissant, chacune avec ✓ et sa durée ; « Tout est vert ».
  3. Un $ref cassé arrête tout à l'étape 1 : la sortie complète, puis le
     remède « → cd contract && npm run validate ».
  4. Ce que garantit le vert.

Les lignes de console sont reconstituées depuis scripts/verifier.mjs et
scripts/lib.mjs (libellés, puces, « — échec », « │ », « → », « Tout est
vert »). Durées inventées. Le nombre de tests est compté dans server/tests :
29 (unit 7 ; functional 22 = contrat 3, session 7, utilisateurs 12) — le
commentaire « Tests 22 passed » de verifier.mjs est périmé. Le $ref cassé est
un exemple, et la sortie de redocly n'est pas recopiée (annotation dorée).

Sources : scripts/verifier.mjs, scripts/lib.mjs, package.json (racine),
contract/package.json, server/package.json, clients/web/package.json,
server/tests/**, README.md (Le réflexe quotidien), décision « pas de CI
distante, tout en local » (docs/tmp/plan-boilerplate-speedcoding.md, rang 5).

Rendu vidéo :  manimgl ep30_verifier.py Ep30Verifier -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


# ---------------------------------------------------------------------------
# Briques locales : une console qui imite scripts/lib.mjs
# ---------------------------------------------------------------------------

def seg(text, color=TXT, bold=False):
    """Un morceau de ligne de console, en markup Pango."""
    t = escape(text, quote=False)
    if bold:
        t = f"<b>{t}</b>"
    return f'<span foreground="{color}">{t}</span>'


# Les puces de scripts/lib.mjs : ok ✓ vert, ko ✗ rouge, info · gris, attention ! jaune
PUCES = {"ok": ("✓", OK_GREEN), "ko": ("✗", ERROR), "info": ("·", DIM), "attention": ("!", WARN)}


def c_ligne(etat, texte, detail=None, gris_apres=None):
    """ligne(etat, texte, detail) : quatre espaces, la puce, le texte, le détail en gris."""
    puce, couleur = PUCES[etat]
    s = "    " + seg(puce, couleur) + " " + seg(texte)
    if gris_apres:
        s += " " + seg(gris_apres, DIM)
    if detail:
        s += " " + seg(detail, DIM)
    return s


def c_en_cours(texte, gris_apres=None):
    """enCours(texte) : la ligne grise qui attend sa conclusion."""
    s = "    " + seg("·", DIM) + " " + seg(texte)
    if gris_apres:
        s += " " + seg(gris_apres, DIM)
    return s + " " + seg("…", DIM)


def c_section(texte):
    return "  " + seg(texte, TXT, bold=True)


def c_titre(texte):
    return seg(texte, TXT, bold=True)


def c_prompt(commande):
    return seg("$ ", DIM) + seg(commande, ACCENT, bold=True)


class Console:
    """Un terminal : les lignes s'ajoutent en bas, et l'ensemble défile."""

    def __init__(self, title, center, width, height, size=15, tag=None, tag_color=DIM):
        self.panel = EditorPanel(title, center, width, height, tag=tag, tag_color=tag_color)
        self.chrome = self.panel.chrome
        cal = MarkupText(STRUT * 10, font=MONO_FONT, font_size=size)
        self.adv = cal.get_width() / 10
        self.block_h = cal.get_height()
        self.lh = self.block_h * 1.42
        self.size = size
        self.x = self.panel.code_left
        self.y0 = self.panel.code_top - self.block_h / 2
        self.rows = int(self.panel.code_h / self.lh)
        self.lines = []          # [(rang, mobject)]
        self.next_row = 0.0
        self.offset = 0.0

    def _make(self, mk, row):
        mob, strut = make_line(mk, self.size)
        place(mob, strut, self.x, self.y0 - (row - self.offset) * self.lh)
        if mob.get_width() > self.panel.code_w + 0.05:
            print(f"[console] ligne trop longue ({mob.get_width():.2f} > {self.panel.code_w:.2f})")
        return mob

    def row_y(self, mob):
        for row, m in self.lines:
            if m is mob:
                return self.y0 - (row - self.offset) * self.lh
        raise ValueError("ligne inconnue")

    def _scroll(self, scene, n, run_time=0.25):
        self.offset += n
        dy = n * self.lh
        anims, kept = [], []
        for row, m in self.lines:
            if row - self.offset < -0.01:
                anims.append(FadeOut(m, shift=dy * UP))
            else:
                anims.append(m.animate.shift(dy * UP))
                kept.append((row, m))
        self.lines = kept
        scene.play(*anims, run_time=run_time)

    def add(self, scene, *mks, space=0.0, run_time=0.3, lag=0.12, extra=()):
        """Ajoute des lignes (avec défilement si besoin) ; rend la ou les lignes créées."""
        self.next_row += space
        last = self.next_row + len(mks) - 1
        overflow = last - self.offset - (self.rows - 1)
        if overflow > 0:
            self._scroll(scene, overflow)
        mobs = []
        for mk in mks:
            m = self._make(mk, self.next_row)
            self.lines.append((self.next_row, m))
            self.next_row += 1
            mobs.append(m)
        anims = [LaggedStart(*[FadeIn(m, shift=0.04 * UP) for m in mobs], lag_ratio=lag)]
        scene.play(*anims, *extra, run_time=run_time)
        return mobs[0] if len(mobs) == 1 else mobs

    def resolve(self, scene, old, mk, run_time=0.25, extra=()):
        """Réécrit une ligne sur place (comme `\\r` dans un vrai terminal)."""
        for i, (row, m) in enumerate(self.lines):
            if m is old:
                new = self._make(mk, row)
                self.lines[i] = (row, new)
                scene.play(FadeOut(old), FadeIn(new), *extra, run_time=run_time)
                return new
        raise ValueError("ligne inconnue")


def hourglass(h=0.3, color=WARN):
    """Un sablier (pas de glyphe fiable dans la police mono)."""
    w = h * 0.75
    top = Polygon([-w / 2, h / 2, 0], [w / 2, h / 2, 0], [0, 0, 0])
    bottom = Polygon([-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [0, 0, 0])
    top.set_fill(color, 0.15).set_stroke(color, 1.6)
    bottom.set_fill(color, 0.7).set_stroke(color, 1.6)
    caps = VGroup(
        Line([-w / 2 - 0.03, h / 2, 0], [w / 2 + 0.03, h / 2, 0]),
        Line([-w / 2 - 0.03, -h / 2, 0], [w / 2 + 0.03, -h / 2, 0]),
    ).set_stroke(color, 2.4)
    return VGroup(top, bottom, caps)


# ---------------------------------------------------------------------------
# Les étapes, telles que déclarées dans ETAPES (scripts/verifier.mjs)
# ---------------------------------------------------------------------------

ETAPES = [
    ("contrat (bundle + spectral)", "contract", "npm run validate", "1,9 s"),
    ("génération (contrat → SDK, types)", ".", "npm run sync", "15,8 s"),
    ("typecheck serveur", "server", "npm run typecheck", "6,2 s"),
    ("lint serveur", "server", "npm run lint", "4,9 s"),
    ("build client web (typecheck + vite)", "clients/web", "npm run build", "9,7 s"),
    ("lint client web", "clients/web", "npm run lint", "3,8 s"),
    ("tests serveur", "server", "npm run test", "13,4 s"),
]
TOTAL = "55,7 s"    # somme des sept durées ci-dessus (le pré-vol n'est pas compté)


def gate(title, sub, color=DIM, width=5.0, height=0.5):
    """Une étape de la barrière : une barre avec son numéro, son libellé, son dossier."""
    box = RoundedRectangle(width=width, height=height, corner_radius=0.1)
    box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
    t = label(title, 15, TXT)
    s = label(sub, 13, DIM, font=MONO_FONT)
    t.move_to([box.get_left()[0] + 0.55 + t.get_width() / 2, 0, 0])
    s.move_to([box.get_right()[0] - 0.18 - s.get_width() / 2, 0, 0])
    g = VGroup(box, t, s)
    g.box = box
    return g


class Ep30Verifier(EpisodeScene):
    EPISODE = "30"
    TITLE = "npm run verifier : la barrière"

    def construct(self):
        self.ci_locale()
        self.sept_etapes()
        self.ref_casse()
        self.garantie()

    # --- 1. La CI est locale --------------------------------------------------------

    def ci_locale(self):
        self.show_chip("La CI est locale : npm run verifier", ACCENT)
        poste = node("ton poste", "le code que tu viens d'écrire", BLUE, width=3.0)
        barriere = node("npm run verifier", "la CI, en local", ACCENT, width=3.4)
        push = node("git push", "seulement si tout est vert", VIOLET, width=3.0)
        row = VGroup(poste, barriere, push).arrange(RIGHT, buff=1.0).move_to([0, 0.9, 0])
        a1 = link(poste.get_right(), barriere.get_left(), DIM)
        a2 = link(barriere.get_right(), push.get_left(), ACCENT)
        self.play(FadeIn(poste, shift=0.1 * RIGHT), run_time=0.5)
        self.play(GrowArrow(a1), FadeIn(barriere, shift=0.1 * RIGHT), run_time=0.6)
        self.play(GrowArrow(a2), FadeIn(push, shift=0.1 * RIGHT), run_time=0.6)

        aide = Console("npm run verifier -- --aide", np.array([0, -1.75, 0]), 10.0, 1.75, size=16)
        self.play(FadeIn(aide.chrome), run_time=0.4)
        aide.add(self, "  " + seg("npm run verifier", TXT, bold=True)
                 + seg(" — lance en local tout ce que la CI vérifiera", TXT),
                 "    " + seg("contrat → génération → typecheck → lint → build → tests", TXT),
                 run_time=0.8, lag=0.4)
        note = label("une seule commande, le même ordre à chaque fois, sur la machine de chacun·e", 16, DIM)
        note.move_to([0, -3.2, 0])
        self.play(FadeIn(note), run_time=0.5)
        self.wait(3.6)
        self.clear_stage()

    # --- 2. Pré-vol, puis sept étapes ------------------------------------------------

    def sept_etapes(self):
        self.show_chip("Un pré-vol, puis sept étapes par coût croissant", ACCENT)

        con = Console("terminal", np.array([-3.05, -0.6, 0]), 7.7, 6.1, size=15)

        x_g = 3.95
        pre = gate("pré-vol · la base répond ?", "migration:status", width=5.6)
        pre.move_to([x_g, 2.15, 0])
        gates = VGroup()
        for i, (lab, cwd, cmd, _) in enumerate(ETAPES):
            short = lab.split(" (")[0]
            g = gate(short, "racine" if cwd == "." else cwd, width=5.6)
            num = label(str(i + 1), 15, DIM, font=MONO_FONT, bold=True)
            num.move_to([g.box.get_left()[0] + 0.27, 0, 0])
            g.add(num)
            g.num = num
            g.move_to([x_g, 1.35 - i * 0.66, 0])
            gates.add(g)

        self.play(FadeIn(con.chrome), FadeIn(pre), LaggedStartMap(FadeIn, gates, lag_ratio=0.1),
                  run_time=1.4)

        con.add(self, c_prompt("npm run verifier"), run_time=0.4)
        con.add(self, c_titre("Vérification"), space=0.4, run_time=0.3)
        con.add(self, c_section("Chaîne complète"), space=0.4, run_time=0.3)

        # Le pré-vol : rien n'est affiché s'il passe
        pre_note = label("pré-vol : node ace migration:status, muet s'il passe", 14, GOLD)
        pre_note.move_to([con.panel.box.get_left()[0] + 0.4 + pre_note.get_width() / 2,
                          con.y0 - (con.next_row - con.offset) * con.lh, 0])
        self.play(FadeIn(pre_note), pre.box.animate.set_stroke(OK_GREEN, 2), run_time=0.5)
        self.wait(1.4)
        self.play(FadeOut(pre_note), run_time=0.3)

        for i, (lab, cwd, cmd, ms) in enumerate(ETAPES):
            g = gates[i]
            pending = con.add(self, c_en_cours(lab), run_time=0.25,
                              extra=[g.box.animate.set_stroke(WARN, 2)])
            self.wait(0.55 + 0.08 * i)
            detail = f"29 tests · {ms}" if lab == "tests serveur" else ms
            check = label("✓", 16, OK_GREEN, bold=True).move_to(g.num)
            con.resolve(self, pending, c_ligne("ok", lab, detail),
                        extra=[g.box.animate.set_stroke(OK_GREEN, 2).set_fill(OK_GREEN, 0.07),
                               FadeTransform(g.num, check)])
        con.add(self, "  " + seg("Tout est vert", OK_GREEN, bold=True) + " " + seg(f"— {TOTAL}", DIM),
                space=0.6, run_time=0.5)

        tests = label("29 tests Japa : unit 7 · functional 22", 14, OK_GREEN)
        tests.next_to(gates[-1], DOWN, buff=0.18)
        self.play(FadeIn(tests), run_time=0.5)
        self.wait(3.2)

        # Si la base ne répond pas, on l'apprend tout de suite
        self.play(FadeOut(tests), run_time=0.3)
        alt = VGroup(
            label("si la base ne répond pas, avant toute étape :", 14, DIM),
            markup(seg("✗ Le serveur ne joint pas la base de données", ERROR, bold=True), size=14,
                   font=MONO_FONT),
            markup(seg("→ ", WARN) + seg("docker compose up -d postgres    puis    npm run diagnostic", TXT),
                   size=13, font=MONO_FONT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        alt.next_to(gates[-1], DOWN, buff=0.15).align_to(gates, LEFT)
        fit_x(alt, margin=0.15)
        self.play(FadeIn(alt), Indicate(pre, color=ERROR, scale_factor=1.03), run_time=0.7)
        self.wait(3.2)
        self.clear_stage()

    # --- 3. Un $ref cassé ------------------------------------------------------------

    def ref_casse(self):
        self.show_chip("Un $ref cassé : tout s'arrête à l'étape 1", ERROR)

        src = ("paths:\n"
               "  …\n"
               "  /utilisateurs:\n"
               "    $ref: './features/utilisateurs/paths/utilisateur.yaml'")
        ed = EditorPanel("contract/openapi.yaml", np.array([-2.35, 1.6, 0]), 9.2, 1.95,
                         tag="exemple : un s oublié", tag_color=ERROR)
        view = ed.fit_code(CodeView(src, ["yaml"], gutter=False), max_scale=0.75)
        self.play(FadeIn(ed.chrome), FadeIn(view.group), run_time=0.6)
        bad = highlight_rect(view.token_box(4, "utilisateur.yaml"), ERROR, 0.2)
        self.play(FadeIn(bad), run_time=0.4)

        # La barrière, en miniature
        dots = VGroup()
        for i in range(7):
            c = Circle(radius=0.2).set_stroke(PANEL_STROKE, 1.5).set_fill(PANEL_BG, 1)
            n = label(str(i + 1), 14, DIM, font=MONO_FONT, bold=True).move_to(c)
            dots.add(VGroup(c, n))
        dots.arrange(RIGHT, buff=0.14).move_to([4.75, 1.85, 0])
        dots_lbl = label("les sept étapes", 14, DIM).next_to(dots, DOWN, buff=0.15)
        self.play(FadeIn(dots), FadeIn(dots_lbl), run_time=0.5)

        con = Console("terminal", np.array([0, -1.45, 0]), 13.6, 3.85, size=15)
        self.play(FadeIn(con.chrome), run_time=0.4)
        con.add(self, c_prompt("npm run verifier"), run_time=0.3)
        con.add(self, c_titre("Vérification"), c_section("Chaîne complète"), run_time=0.4)
        pending = con.add(self, c_en_cours("contrat (bundle + spectral)"), run_time=0.25,
                          extra=[dots[0][0].animate.set_stroke(WARN, 2)])
        self.wait(0.5)
        con.resolve(self, pending, c_ligne("ko", "contrat (bundle + spectral)"),
                    extra=[dots[0][0].animate.set_stroke(ERROR, 2.5).set_fill(ERROR, 0.25),
                           *[d.animate.set_opacity(0.3) for d in dots[1:]]])
        skip = label("non lancées", 14, DIM).next_to(dots[1:], DOWN, buff=0.15)
        self.play(FadeTransform(dots_lbl, skip), run_time=0.4)

        con.add(self, "  " + seg("✗ contrat (bundle + spectral) — échec", ERROR, bold=True),
                space=0.4, run_time=0.4)
        bar = seg("│", DIM) + " "
        con.add(self,
                "  " + bar + seg("> contract@1.0.0 validate", TXT),
                "  " + bar + seg("> npm run bundle && npm run lint", TXT),
                "  " + bar + seg("> contract@1.0.0 bundle", TXT),
                "  " + bar + seg("> redocly bundle openapi.yaml -o dist/openapi.json", TXT),
                "  " + bar + seg("… la sortie complète de redocly, qui nomme le $ref introuvable", GOLD),
                space=0.4, run_time=1.0, lag=0.25)
        rem = con.add(self, "  " + seg("→", WARN) + " " + seg("cd contract && npm run validate", TXT, bold=True),
                      space=0.4, run_time=0.4)
        self.play(Indicate(rem, color=WARN, scale_factor=1.06), run_time=0.8)
        why = label("la première étape qui échoue arrête tout : sa sortie complète, puis la commande "
                    "pour corriger", 15, DIM)
        why.move_to([0, -3.65, 0])
        fit_x(why)
        self.play(FadeIn(why), run_time=0.4)
        self.wait(3.8)
        self.clear_stage()

    # --- 4. Ce que garantit le vert -------------------------------------------------

    def garantie(self):
        self.show_chip("Vert : ce que ça garantit", OK_GREEN)
        items = [
            ("le contrat se bundle et passe Spectral", ACCENT),
            ("le SDK et les types sont régénérés, donc frais", GOLD),
            ("le serveur compile et passe ESLint", VIOLET),
            ("le web se construit (tsc + vite) et passe ESLint", BLUE),
            ("les 29 tests du serveur passent, garde-fou du contrat compris", OK_GREEN),
        ]
        rows = VGroup()
        for text, color in items:
            ck = label("✓", 22, color, bold=True)
            t = label(text, 20, TXT)
            rows.add(VGroup(ck, t).arrange(RIGHT, buff=0.25))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([0, 0.55, 0])
        self.play(LaggedStartMap(FadeIn, rows, shift=0.15 * RIGHT, lag_ratio=0.3), run_time=2.2)
        self.wait(2.0)
        rule = VGroup(
            label("La CI est locale : npm run verifier, avant chaque git push.", 22, ACCENT, bold=True),
            label("C'est la barrière de l'équipe — c'est toi qui la lances.", 18, TXT),
        ).arrange(DOWN, buff=0.18).move_to([0, -2.35, 0])
        self.play(FadeIn(rule, shift=0.1 * UP), run_time=0.7)
        self.wait(3.0)
        next_ep = label("épisode suivant : npm run feature, la tranche verticale  →", 16, DIM)
        next_ep.to_corner(DR, buff=0.3)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(2.0)
