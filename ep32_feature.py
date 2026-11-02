"""
Épisode 32 — `npm run feature ramassages` : la tranche verticale

Bloc F : une fonctionnalité de bout en bout.
  1. Une commande : le nom donne tous les autres (Ramassages, Ramassage,
     listerRamassages, creerRamassage, EXG-RAM).
  2. Dix fichiers : 3 schémas, 1 path, la migration, le service, le
     contrôleur, les routes, le test (5 tests), la spécification.
  3. Les trois fichiers-listes (contract/openapi.yaml, server/start/routes.ts,
     sdk/src/msw.ts) reçoivent leurs lignes à leur place ALPHABÉTIQUE ;
     puis `node ace codegen` régénère l'index des contrôleurs.
  4. A/B : brigades + sorties tombent à deux places séparées par session
     (git fusionne seul) ; brigades + ramassages tombent au même endroit
     (conflit, résolu en gardant les deux). L'alphabétique réduit les
     conflits, sans les supprimer.
  5. Encart : utilisateurs n'est pas le gabarit (gen_random_uuid(), ni
     supprime_le, ni occurred_at).
  6. « Et maintenant, dans cet ordre » (les 7 étapes affichées par le
     script), puis un verifier vert : 34 tests (29 existants + 5 générés).

Lignes de console reconstituées depuis scripts/feature.mjs (et lib.mjs) ;
l'horodatage de la migration est un exemple (Date.now()). Les extraits des
fichiers-listes sont les fichiers réels, avec les lignes que le script insère.
Les branches brigades / sorties sont des exemples.

Sources : scripts/feature.mjs (FICHIERS, INSERTIONS, insererAlphabetiquement,
messages), contract/openapi.yaml, server/start/routes.ts, sdk/src/msw.ts,
server/database/migrations/1761885935168_create_users_table.ts, README.md
(Créer une fonctionnalité, Les cinq fichiers partagés), server/tests/**.

Rendu vidéo :  manimgl ep32_feature.py Ep32Feature -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


MIGRATION = "server/database/migrations/1793178123456_create_ramassages_table.ts"   # Date.now() : exemple

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
# Briques locales : l'arborescence du poste, qui se remplit
# ---------------------------------------------------------------------------

class Tree:
    """Des lignes d'arborescence ; en révéler une décale celles du dessous."""

    def __init__(self, entries, left, top, right, lh=0.285, size=15):
        self.left, self.top, self.right, self.lh, self.size = left, top, right, lh, size
        self.order = [e["key"] for e in entries]
        self.entries = {}
        self.visible = []
        for e in entries:
            mob = self._row(e["text"], e["level"], e["color"], e.get("tag"), e.get("tag_color", DIM))
            self.entries[e["key"]] = dict(e, mob=mob, y=0.0)
            if e.get("visible"):
                self.visible.append(e["key"])
        for k, y in self._layout(self.visible).items():
            self.entries[k]["mob"].shift(y * UP)
            self.entries[k]["y"] = y

    def _row(self, text, level, color, tag, tag_color):
        name = label(text, self.size, color, font=MONO_FONT, bold=(level == 0))
        name.move_to([self.left + 0.38 * level + name.get_width() / 2, 0, 0])
        group = VGroup(name)
        if tag:
            t = label(tag, 13, tag_color)
            t.move_to([self.right - t.get_width() / 2, 0, 0])
            group.add(t)
        return group

    def _layout(self, keys):
        ordered = [k for k in self.order if k in keys]
        return {k: self.top - i * self.lh for i, k in enumerate(ordered)}

    def initial(self):
        return VGroup(*[self.entries[k]["mob"] for k in self.visible])

    def box(self, key):
        mob = self.entries[key]["mob"]
        return (np.array([(self.left + self.right) / 2 - 0.05, self.entries[key]["y"], 0]),
                self.right - self.left + 0.3, self.lh * 0.92)

    def reveal(self, *keys):
        """Animations : les lignes existantes glissent, les nouvelles apparaissent."""
        new_visible = self.visible + [k for k in keys if k not in self.visible]
        layout = self._layout(new_visible)
        anims = []
        for k in self.visible:
            e = self.entries[k]
            dy = layout[k] - e["y"]
            if abs(dy) > 1e-6:
                anims.append(e["mob"].animate.shift(dy * UP))
                e["y"] = layout[k]
        for k in keys:
            if k in self.visible:
                continue
            e = self.entries[k]
            e["mob"].shift((layout[k] - e["y"]) * UP)   # pas encore à l'écran : on déplace sans animer
            e["y"] = layout[k]
            anims.append(FadeIn(e["mob"], shift=0.12 * RIGHT))
        self.visible = new_visible
        return anims

    def retag(self, key, tag, color):
        e = self.entries[key]
        old = e["mob"][1] if len(e["mob"]) > 1 else None
        t = label(tag, 13, color)
        t.move_to([self.right - t.get_width() / 2, e["y"], 0])
        if old is None:
            e["mob"].add(t)
            return [FadeIn(t)]
        e["mob"].remove(old)
        e["mob"].add(t)
        return [FadeTransform(old, t)]


# ---------------------------------------------------------------------------
# Brique locale : un extrait de fichier qui reçoit des lignes
# ---------------------------------------------------------------------------

def insertion_view(panel, after_src, inserted, lexer, max_scale=0.9):
    """CodeView de l'état final ; les lignes `inserted` (base 1) sont cachées et
    les autres remontées à leur place d'avant. Rend (vue, animations d'insertion)."""
    view = panel.fit_code(CodeView(after_src, [lexer], gutter=False), max_scale=max_scale)
    before_shift = {}
    for i in range(1, len(view.lines) + 1):
        if i in inserted:
            continue
        above = sum(1 for k in inserted if k < i)
        before_shift[i] = above
        view.lines[i - 1].shift(above * view.line_h * UP)
    shown = VGroup(*[view.lines[i - 1] for i in before_shift])
    rects = VGroup(*[highlight_rect(view.line_box(k), OK_GREEN, 0.16) for k in inserted])
    anims = [view.lines[i - 1].animate.shift(n * view.line_h * DOWN) for i, n in before_shift.items() if n]
    new_lines = [view.lines[k - 1] for k in inserted]
    return view, shown, anims, new_lines, rects


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep32Feature(EpisodeScene):
    EPISODE = "32"
    TITLE = "npm run feature : la tranche verticale"

    def construct(self):
        self.une_commande()
        self.dix_fichiers()
        self.fichiers_listes()
        self.conflits()
        self.pas_utilisateurs()
        self.et_maintenant()

    # --- 1. Une commande ------------------------------------------------------------

    def une_commande(self):
        self.show_chip("Une commande, une tranche complète", VIOLET)
        cmd = markup(seg("$ ", DIM) + seg("npm run feature ", TXT, bold=True)
                     + seg("ramassages", VIOLET, bold=True), size=34, font=MONO_FONT)
        cmd.move_to([0, 1.85, 0])
        rule = label("au pluriel, en minuscules, sans accent", 16, DIM).next_to(cmd, DOWN, buff=0.2)
        self.play(FadeIn(cmd, shift=0.1 * DOWN), run_time=0.7)
        self.play(FadeIn(rule), run_time=0.4)

        rows = [
            ("Pluriel", "Ramassages", "tags, contrôleur, service"),
            ("Singulier", "Ramassage", "le « s » final retiré : à relire"),
            ("opérations", "listerRamassages · creerRamassage", "GET et POST /ramassages"),
            ("exigences", "EXG-RAM-001, EXG-RAM-002", "trois premières lettres"),
        ]
        table = VGroup()
        for k, v, note in rows:
            a = label(k, 17, DIM)
            b = label(v, 19, VIOLET, font=MONO_FONT, bold=True)
            c = label(note, 15, DIM)
            table.add(VGroup(a, b, c))
        for r in table:
            r[0].move_to([-5.0 + r[0].get_width() / 2, 0, 0])
            r[1].move_to([-3.0 + r[1].get_width() / 2, 0, 0])
            r[2].move_to([2.6 + r[2].get_width() / 2, 0, 0])
        for i, r in enumerate(table):
            r.shift((0.35 - i * 0.62) * UP)
        arrows = VGroup(*[Arrow(cmd[-1].get_bottom() + 0.05 * DOWN, r[1].get_left() + 0.1 * LEFT, buff=0.1,
                                thickness=1.4).set_color(PANEL_STROKE) for r in table])
        self.play(LaggedStart(*[FadeIn(r, shift=0.1 * RIGHT) for r in table], lag_ratio=0.3), run_time=1.8)
        note = label("Une seule opération, lister + créer, qui traverse toute la pile : on la renomme, on la "
                     "duplique.", 16, TXT).move_to([0, -2.6, 0])
        fit_x(note)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(3.2)
        self.clear_stage()

    # --- 2. Dix fichiers ----------------------------------------------------------------

    def dix_fichiers(self):
        self.show_chip("Dix fichiers créés", VIOLET)
        con = Console("terminal", np.array([-3.25, -0.6, 0]), 7.3, 6.3, size=14)
        self.con = con
        panel = EditorPanel("la tranche", np.array([3.8, -0.6, 0]), 6.4, 6.3, tag="ramassages", tag_color=VIOLET)
        left = panel.code_left + 0.02
        right = panel.box.get_right()[0] - 0.3
        top = panel.code_top - 0.1
        entries = [
            dict(key="h_contract", text="contract/features/ramassages/", level=0, color=ACCENT),
            dict(key="f0", text="schemas/Ramassage.yaml", level=1, color=TXT, tag="schéma"),
            dict(key="f1", text="schemas/ListeRamassages.yaml", level=1, color=TXT, tag="schéma"),
            dict(key="f2", text="schemas/CreationRamassage.yaml", level=1, color=TXT, tag="schéma"),
            dict(key="f3", text="paths/ramassages.yaml", level=1, color=TXT, tag="GET + POST"),
            dict(key="h_server", text="server/", level=0, color=VIOLET),
            dict(key="f4", text="database/migrations/…_ramassages_table.ts", level=1, color=TXT,
                 tag="migration"),
            dict(key="f5", text="app/services/ramassages_service.ts", level=1, color=TXT, tag="métier"),
            dict(key="f6", text="app/controllers/ramassages_controller.ts", level=1, color=TXT, tag="HTTP"),
            dict(key="f7", text="start/routes/ramassages.ts", level=1, color=TXT, tag="routes"),
            dict(key="f8", text="tests/functional/ramassages.spec.ts", level=1, color=TXT, tag="5 tests"),
            dict(key="h_docs", text="docs/specs/", level=0, color=DIM),
            dict(key="f9", text="ramassages.md", level=1, color=TXT, tag="exigences"),
        ]
        tree = Tree(entries, left, top, right, lh=0.36, size=14)
        self.play(FadeIn(con.chrome), FadeIn(panel.chrome), run_time=0.6)

        con.add(self, c_prompt("npm run feature ramassages"), run_time=0.4)
        con.add(self, c_titre("Nouvelle fonctionnalité : ramassages"), space=0.4, run_time=0.3)
        con.add(self, c_section("Fichiers créés"), space=0.4, run_time=0.3)
        files = [
            ("contract/features/ramassages/schemas/Ramassage.yaml", ["h_contract", "f0"]),
            ("contract/features/ramassages/schemas/ListeRamassages.yaml", ["f1"]),
            ("contract/features/ramassages/schemas/CreationRamassage.yaml", ["f2"]),
            ("contract/features/ramassages/paths/ramassages.yaml", ["f3"]),
            (MIGRATION, ["h_server", "f4"]),
            ("server/app/services/ramassages_service.ts", ["f5"]),
            ("server/app/controllers/ramassages_controller.ts", ["f6"]),
            ("server/start/routes/ramassages.ts", ["f7"]),
            ("server/tests/functional/ramassages.spec.ts", ["f8"]),
            ("docs/specs/ramassages.md", ["h_docs", "f9"]),
        ]
        for path, keys in files:
            con.add(self, c_ligne("ok", path), run_time=0.45, extra=tree.reveal(*keys))
            self.wait(0.15)

        count = label("10", 40, VIOLET, bold=True)
        count_lbl = label("fichiers · 4 contrat · 5 serveur · 1 doc", 16, TXT)
        grp = VGroup(count, count_lbl).arrange(RIGHT, buff=0.2)
        grp.move_to([panel.box.get_center()[0], panel.box.get_bottom()[1] + 0.55, 0])
        self.play(FadeIn(grp, scale=1.2), run_time=0.6)
        self.wait(2.8)
        self.play(FadeOut(grp), FadeOut(panel.chrome), *[FadeOut(tree.entries[k]["mob"]) for k in tree.visible],
                  run_time=0.5)
        self.clear_stage()

    # --- 3. Les trois fichiers-listes ---------------------------------------------------

    def fichiers_listes(self):
        self.show_chip("Trois fichiers-listes : une ligne à sa place alphabétique", VIOLET)
        con = Console("terminal", np.array([0, -2.85, 0]), 13.6, 1.75, size=14)
        self.play(FadeIn(con.chrome), run_time=0.4)
        con.add(self, c_section("Fichiers-listes"), run_time=0.3)

        files = [
            ("contract/openapi.yaml", "yaml",
             "tags:\n"
             "  - name: Ramassages\n"
             "    description: TODO\n"
             "  - name: Session\n"
             "    description: Ouverture et fermeture de session\n"
             "  - name: Utilisateurs\n"
             "    description: Gestion des utilisateurs\n"
             "…\n"
             "paths:\n"
             "  /ramassages:\n"
             "    $ref: './features/ramassages/paths/ramassages.yaml'\n"
             "  /session/connexion:\n"
             "    $ref: './features/session/paths/connexion.yaml'\n"
             "  …",
             [2, 3, 10, 11],
             [("contract/openapi.yaml — tags", None), ("contract/openapi.yaml — paths", None)]),
            ("server/start/routes.ts", "typescript",
             "import routesDeRamassages from './routes/ramassages.js'\n"
             "import routesDeSession from './routes/session.js'\n"
             "import routesDUtilisateurs from './routes/utilisateurs.js'\n"
             "\n"
             "router\n"
             "  .group(() => {\n"
             "    routesDeRamassages()\n"
             "    routesDeSession()\n"
             "    routesDUtilisateurs()\n"
             "  })\n"
             "  .prefix(PREFIXE_API)",
             [1, 7],
             [("server/start/routes.ts — l'index des routes", None)]),
            ("sdk/src/msw.ts", "typescript",
             "export * from './generated/endpoints/ramassages/ramassages.msw';\n"
             "export * from './generated/endpoints/session/session.msw';\n"
             "export * from './generated/endpoints/utilisateurs/utilisateurs.msw';\n"
             "\n"
             "import { getRamassagesMock } from './generated/endpoints/ramassages/ramassages.msw';\n"
             "import { getSessionMock } from './generated/endpoints/session/session.msw';\n"
             "…\n"
             "export const handlers = [\n"
             "  ...getRamassagesMock(),\n"
             "  ...getSessionMock(),\n"
             "  ...getUtilisateursMock(),\n"
             "];",
             [1, 5, 9],
             [("sdk/src/msw.ts — les mocks", None)]),
        ]
        prev = None
        for name, lexer, src, inserted, lines in files:
            panel = EditorPanel(name, np.array([0, 0.55, 0]), 13.0, 4.2, tag="extrait réel + lignes insérées",
                                tag_color=OK_GREEN)
            view, shown, anims, new_lines, rects = insertion_view(panel, src, inserted, lexer, max_scale=0.78)
            if prev is None:
                self.play(FadeIn(panel.chrome), FadeIn(shown), run_time=0.6)
            else:
                self.play(FadeOut(prev), FadeIn(panel.chrome), FadeIn(shown), run_time=0.6)
            self.wait(0.6)
            self.play(*anims, run_time=0.6)
            self.play(LaggedStart(*[FadeIn(l, shift=0.1 * RIGHT) for l in new_lines], lag_ratio=0.2),
                      LaggedStart(*[FadeIn(r) for r in rects], lag_ratio=0.2), run_time=0.8)
            for text, _ in lines:
                con.add(self, c_ligne("ok", text), run_time=0.35)
            why = label("R < S : avant session, loin de la ligne d'un autre", 15, OK_GREEN)
            why.next_to(panel.box, DOWN, buff=0.1).align_to(panel.box, RIGHT)
            self.play(FadeIn(why), run_time=0.3)
            self.wait(2.6)
            prev = VGroup(panel.chrome, view.group, rects, why)

        con.add(self, c_section("Index du cadre technique"), c_ligne("ok", ".adonisjs/controllers.ts", "régénéré"),
                space=0.3, run_time=0.5)
        cg = label("node ace codegen : sans lui, controllers.Ramassages n'existe pas", 15, GOLD)
        cg.next_to(prev[0][0], DOWN, buff=0.1).align_to(prev[0][0], LEFT)
        self.play(FadeOut(prev[3]), FadeIn(cg), run_time=0.4)
        self.wait(2.8)
        self.clear_stage()

    # --- 4. A/B : quand git fusionne seul, quand il bloque ------------------------------

    def conflits(self):
        self.show_chip("Deux branches en parallèle : fusion ou conflit ?", WARN)

        left_src = ("paths:\n"
                    "  /brigades:\n"
                    "    $ref: './features/brigades/…'\n"
                    "  /session/connexion:\n"
                    "    …\n"
                    "  /moi:\n"
                    "    …\n"
                    "  /sorties:\n"
                    "    $ref: './features/sorties/…'\n"
                    "  /utilisateurs:\n"
                    "    …")
        right_src = ("paths:\n"
                     "<<<<<<< feature/brigades\n"
                     "  /brigades:\n"
                     "    $ref: './features/brigades/…'\n"
                     "=======\n"
                     "  /ramassages:\n"
                     "    $ref: './features/ramassages/…'\n"
                     ">>>>>>> feature/ramassages\n"
                     "  /session/connexion:\n"
                     "    …")
        fixed_src = ("paths:\n"
                     "  /brigades:\n"
                     "    $ref: './features/brigades/…'\n"
                     "  /ramassages:\n"
                     "    $ref: './features/ramassages/…'\n"
                     "  /session/connexion:\n"
                     "    …")
        lp = EditorPanel("brigades + sorties", np.array([-3.55, 0.05, 0]), 6.7, 4.6, tag="openapi.yaml",
                         tag_color=DIM)
        rp = EditorPanel("brigades + ramassages", np.array([3.55, 0.05, 0]), 6.7, 4.6, tag="openapi.yaml",
                         tag_color=DIM)
        lv = lp.fit_code(CodeView(left_src, ["yaml"], gutter=False), max_scale=0.68)
        rv = rp.fit_code(CodeView(right_src, ["yaml"], gutter=False), max_scale=0.68)

        # Cas A : deux places séparées par session
        self.play(FadeIn(lp.chrome), FadeIn(lv.group), run_time=0.6)
        a_rects = VGroup(*[highlight_rect(lv.line_box(i), VIOLET, 0.16) for i in (2, 3)],
                         *[highlight_rect(lv.line_box(i), BLUE, 0.16) for i in (8, 9)])
        sep = highlight_rect(lv.span_box(4, 2, 18), DIM, 0.08)
        self.play(LaggedStart(*[FadeIn(r) for r in a_rects], lag_ratio=0.2), run_time=0.8)
        self.play(FadeIn(sep), run_time=0.3)
        cap_a = label("séparées par session : git fusionne seul  ✓", 17, OK_GREEN, bold=True)
        cap_a.next_to(lp.box, DOWN, buff=0.2)
        self.play(FadeIn(cap_a), run_time=0.5)
        self.wait(2.4)

        # Cas B : le même endroit, avant session
        self.play(FadeIn(rp.chrome), FadeIn(rv.group), run_time=0.6)
        b_rects = VGroup(*[highlight_rect(rv.line_box(i), ERROR, 0.14) for i in (2, 5, 8)])
        self.play(LaggedStart(*[FadeIn(r) for r in b_rects], lag_ratio=0.2), run_time=0.7)
        cap_b = label("même endroit, avant session : conflit", 17, ERROR, bold=True)
        cap_b.next_to(rp.box, DOWN, buff=0.2)
        self.play(FadeIn(cap_b), run_time=0.5)
        self.wait(2.4)

        # Résolution : garder les deux, jamais choisir
        fv = CodeView(fixed_src, ["yaml"], gutter=False)
        fv.fit(rv.line_h / fv.line_h, rv.group.get_corner(UL))
        f_rects = VGroup(highlight_rect(fv.line_box(2), VIOLET, 0.16), highlight_rect(fv.line_box(3), VIOLET, 0.16),
                         highlight_rect(fv.line_box(4), BLUE, 0.16), highlight_rect(fv.line_box(5), BLUE, 0.16))
        cap_c = label("on garde les deux, puis on reclasse — jamais en choisissant", 16, OK_GREEN, bold=True)
        cap_c.move_to(cap_b)
        fit_x(cap_c)
        self.play(FadeOut(b_rects), FadeTransform(rv.group, fv.group), FadeTransform(cap_b, cap_c), run_time=0.9)
        self.play(FadeIn(f_rects), run_time=0.4)
        self.wait(1.2)
        msg = label("l'ordre alphabétique réduit les conflits, il ne les supprime pas", 19, TXT, bold=True)
        msg.move_to([0, -3.5, 0])
        self.play(FadeIn(msg, shift=0.1 * UP), run_time=0.5)
        self.wait(3.0)
        self.clear_stage()

    # --- 5. utilisateurs n'est pas le gabarit ------------------------------------------

    def pas_utilisateurs(self):
        self.show_chip("Ne copie pas utilisateurs : pars du gabarit", ERROR)
        lp = EditorPanel("…/1761885935168_create_users_table.ts", np.array([-3.55, 1.35, 0]), 6.7, 1.9,
                         tag="utilisateurs", tag_color=DIM)
        rp = EditorPanel("…_create_ramassages_table.ts", np.array([3.55, 1.35, 0]), 6.7, 1.9,
                         tag="généré", tag_color=VIOLET)
        lv = lp.fit_code(CodeView("table.uuid('id').primary().defaultTo(this.raw('gen_random_uuid()'))",
                                  ["typescript"], gutter=False), max_scale=0.62)
        rv = rp.fit_code(CodeView("table.uuid('id').primary()\n"
                                  "table.timestamp('supprime_le').nullable()\n"
                                  "table.timestamp('occurred_at').nullable()",
                                  ["typescript"], gutter=False), max_scale=0.62)
        self.play(FadeIn(lp.chrome), FadeIn(lv.group), FadeIn(rp.chrome), FadeIn(rv.group), run_time=0.7)
        self.play(FadeIn(highlight_rect(lv.token_box(1, "gen_random_uuid()"), ERROR, 0.16)), run_time=0.4)

        rows = [
            ("id fourni par le client, en UUIDv7", "ADR 0012"),
            ("suppression douce : supprime_le", "ADR 0013"),
            ("occurred_at : l'heure de l'action", "ADR 0006"),
        ]
        table = VGroup()
        for i, (text, adr) in enumerate(rows):
            y = -0.55 - i * 0.62
            t = label(text, 18, TXT).move_to([-0.6, y, 0])
            a = label(adr, 14, DIM).next_to(t, DOWN, buff=0.06)
            ko = label("✗", 24, ERROR, bold=True).move_to([-5.0, y, 0])
            ok = label("✓", 24, OK_GREEN, bold=True).move_to([5.0, y, 0])
            table.add(VGroup(ko, t, a, ok))
        heads = VGroup(label("utilisateurs", 15, DIM).move_to([-5.0, 0.0, 0]),
                       label("gabarit", 15, VIOLET).move_to([5.0, 0.0, 0]))
        self.play(FadeIn(heads), LaggedStart(*[FadeIn(r) for r in table], lag_ratio=0.3), run_time=1.5)
        note = label("utilisateurs est une table créée côté serveur. Une ressource saisie hors réseau part "
                     "du gabarit.", 16, TXT).move_to([0, -2.95, 0])
        fit_x(note)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(3.6)
        self.clear_stage()

    # --- 6. Et maintenant, dans cet ordre ---------------------------------------------

    def et_maintenant(self):
        self.show_chip("Et maintenant, dans cet ordre", VIOLET)
        con = Console("terminal", np.array([0, -0.4, 0]), 13.6, 5.9, size=14)
        self.play(FadeIn(con.chrome), run_time=0.4)

        def step(n, path, rest):
            return "    " + seg(f"{n}. ", TXT) + seg(path, TXT, bold=True) + seg(rest, TXT)

        con.add(self, "  " + seg("Fait.", OK_GREEN, bold=True) + " " + seg("Et maintenant, dans cet ordre :", DIM),
                run_time=0.4)
        lines = [
            step(1, "docs/specs/ramassages.md", "        écrire les exigences et leurs identifiants"),
            step(2, "contract/features/ramassages/", "   décrire les vraies opérations et schémas"),
            step(3, "npm run sync", "                       régénérer le SDK et les types"),
            step(4, MIGRATION, ""),
            "       " + seg("les colonnes métier, puis ", TXT) + seg("node ace migration:run", TXT, bold=True),
            step(5, "server/app/services/ramassages_service.ts", "   le métier"),
            step(6, "server/tests/functional/ramassages.spec.ts", "  un test par exigence"),
            step(7, "npm run verifier", "                   avant de pousser"),
        ]
        mobs = con.add(self, *lines, space=0.5, run_time=2.4, lag=0.3)
        con.add(self, "  " + seg("Les libellés « TODO-EXG » du test sont à remplacer par les vrais", DIM),
                "  " + seg("identifiants : `grep -r TODO-EXG` liste ce qui reste à faire.", DIM),
                space=0.5, run_time=0.6)
        self.wait(2.8)

        # La garantie : juste après la génération, verifier est vert
        con.add(self, c_prompt("npm run verifier"), space=0.6, run_time=0.4)
        con.add(self, seg("    …", DIM), c_ligne("ok", "tests serveur", "34 tests · 15,1 s"),
                "  " + seg("Tout est vert", OK_GREEN, bold=True) + " " + seg("— 61,3 s", DIM),
                run_time=0.9, lag=0.3)
        count = label("29 tests existants + 5 générés", 15, OK_GREEN)
        count.move_to([con.panel.box.get_right()[0] - 0.4 - count.get_width() / 2,
                       con.row_y(con.lines[-2][1]), 0])
        self.play(FadeIn(count), run_time=0.4)
        self.wait(1.4)
        warn = label("vert ne veut pas dire fini : lister() renvoie une liste vide, conforme au contrat ; "
                     "le whereNull('supprime_le') reste un TODO", 15, WARN)
        warn.move_to([0, -3.75, 0])
        fit_x(warn)
        self.play(FadeIn(warn), run_time=0.5)
        self.wait(3.2)
        next_ep = label("fin de la saison 1  ·  merci !", 16, DIM)
        next_ep.to_corner(UR, buff=0.3).shift(0.15 * DOWN)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(1.5)
