"""
Épisode 4 — Les cinq commandes, puis `npm run setup`

Bloc B : le dépôt au quotidien. La carte des outils, puis le premier jour.
  1. Les cinq commandes de la racine, chacune avec son moment
     (setup, sync, feature, diagnostic, verifier).
  2. Premier jour : à gauche la console de `npm run setup`, à droite le poste
     qui se remplit au même rythme (.env, node_modules ×4 dans l'ordre,
     PostgreSQL attendu par pg_isready, code généré, migrations, aucun
     seeder) ; fin sur « Prêt à coder. », devant une base vide.
  3. Encart : les deux .env qui doivent rester d'accord (ce que vérifie
     `npm run diagnostic`).

Les lignes de console sont reconstituées à partir du code des scripts (mêmes
textes, mêmes puces ✓ · ! ✗, même ordre). Seuls les numéros de version et les
durées sont inventés.

Sources : package.json (racine, champ "//" et scripts), CLAUDE.md (Commandes),
README.md (Installer, Le réflexe quotidien), scripts/setup.mjs, scripts/lib.mjs,
scripts/diagnostic.mjs, .env.example, server/.env.example.

Rendu vidéo :  manimgl ep04_setup.py Ep04Setup -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


POSTGRES = "#5B9BD5"


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
# La scène
# ---------------------------------------------------------------------------

class Ep04Setup(EpisodeScene):
    EPISODE = "04"
    TITLE = "Les cinq commandes, puis npm run setup"

    def construct(self):
        self.cinq_commandes()
        self.premier_jour()
        self.deux_env()

    # --- 1. Les cinq commandes ----------------------------------------------

    def cinq_commandes(self):
        self.show_chip("Les cinq commandes de la racine")

        rows = [
            ("npm run setup", ACCENT, "le premier jour", "à relancer sans risque : idempotent"),
            ("npm run sync", GOLD, "après chaque git pull", "régénère le SDK et les types (épisode 7)"),
            ("npm run feature <nom>", VIOLET, "pour une nouvelle fonctionnalité",
             "la tranche complète, prête et verte (épisode 32)"),
            ("npm run diagnostic", BLUE, "« est-ce que je peux coder, là ? »",
             "ne modifie rien, dit quelle commande lancer"),
            ("npm run verifier", WARN, "avant de pousser",
             "la CI est locale : c'est elle (épisode 30)"),
        ]
        group = VGroup()
        for i, (cmd, color, moment, detail) in enumerate(rows):
            y = 1.95 - i * 0.92
            bar = RoundedRectangle(width=0.08, height=0.62, corner_radius=0.04)
            bar.set_fill(color, 1).set_stroke(width=0).move_to([-6.3, y, 0])
            c = label(cmd, 23, color, font=MONO_FONT, bold=True)
            c.move_to([-6.05 + c.get_width() / 2, y, 0])
            m = label(moment, 21, TXT)
            m.move_to([-1.75 + m.get_width() / 2, y + 0.15, 0])
            d = label(detail, 15, DIM)
            d.move_to([-1.75 + d.get_width() / 2, y - 0.2, 0])
            group.add(VGroup(bar, c, m, d))
        self.play(LaggedStartMap(FadeIn, group, shift=0.15 * RIGHT, lag_ratio=0.35), run_time=3.0)
        self.wait(2.8)

        note = VGroup(
            label("scripts/*.mjs : du Node pur, sans aucune dépendance", 17, TXT),
            label("setup tourne AVANT le premier npm install (champ \"//\" du package.json racine)",
                  15, DIM),
        ).arrange(DOWN, buff=0.12).move_to([0, -2.85, 0])
        self.play(FadeIn(note, shift=0.1 * UP), run_time=0.6)
        self.wait(2.2)

        # On garde setup, le reste s'efface
        self.play(Indicate(group[0][1], color=ACCENT, scale_factor=1.08), run_time=0.8)
        self.clear_stage()

    # --- 2. Premier jour : npm run setup ----------------------------------------

    def premier_jour(self):
        self.show_chip("Premier jour : npm run setup")

        con = Console("terminal", np.array([-2.85, -0.62, 0]), 8.1, 6.3, size=15)
        self.con = con

        panel = EditorPanel("cmc-archi/", np.array([4.2, -0.62, 0]), 5.5, 6.3,
                            tag="ton poste", tag_color=DIM)
        left = panel.code_left + 0.02
        right = panel.box.get_right()[0] - 0.3
        top = panel.code_top - 0.1
        GEN = GOLD
        entries = [
            dict(key="env", text=".env", level=0, color=WARN, tag="copié"),
            dict(key="contract", text="contract/", level=0, color=TXT, visible=True),
            dict(key="c_nm", text="node_modules/", level=1, color=DIM, tag="npm ci"),
            dict(key="c_dist", text="dist/openapi.json", level=1, color=GEN, tag="généré"),
            dict(key="sdk", text="sdk/", level=0, color=TXT, visible=True),
            dict(key="s_nm", text="node_modules/", level=1, color=DIM, tag="npm ci"),
            dict(key="s_gen", text="src/generated/", level=1, color=GEN, tag="généré"),
            dict(key="s_dist", text="dist/", level=1, color=GEN, tag="compilé"),
            dict(key="server", text="server/", level=0, color=TXT, visible=True),
            dict(key="v_env", text=".env", level=1, color=WARN, tag="copié"),
            dict(key="v_nm", text="node_modules/", level=1, color=DIM, tag="npm ci"),
            dict(key="v_contract", text="app/contract/", level=1, color=GEN, tag="généré"),
            dict(key="v_adonis", text=".adonisjs/", level=1, color=GEN, tag="généré"),
            dict(key="v_schema", text="database/schema.ts", level=1, color=VIOLET,
                 tag="versionné", visible=True),
            dict(key="web", text="clients/web/", level=0, color=TXT, visible=True),
            dict(key="w_env", text=".env.local", level=1, color=WARN, tag="copié"),
            dict(key="w_nm", text="node_modules/", level=1, color=DIM, tag="npm ci"),
        ]
        tree = Tree(entries, left, top, right)

        # La base : un conteneur, en bas du panneau
        db_box = RoundedRectangle(width=5.0, height=0.5, corner_radius=0.12)
        db_box.set_fill(POSTGRES, 0.06).set_stroke(POSTGRES, 1.5)
        db_box.move_to([panel.box.get_center()[0], panel.box.get_bottom()[1] + 0.42, 0])
        db_name = label("PostgreSQL 16", 16, POSTGRES, font=MONO_FONT, bold=True)
        db_name.move_to([db_box.get_left()[0] + 0.2 + db_name.get_width() / 2, db_box.get_center()[1], 0])
        db_state = label("conteneur arrêté", 14, DIM)
        db_state.move_to([db_box.get_right()[0] - 0.2 - db_state.get_width() / 2, db_box.get_center()[1], 0])
        db_box.set_stroke(POSTGRES, 1.5, opacity=0.4)
        db_name.set_opacity(0.45)
        db = VGroup(db_box, db_name)
        self.db_state = db_state

        def set_db(text, color, full=True):
            new = label(text, 14, color, bold=full)
            new.move_to([db_box.get_right()[0] - 0.2 - new.get_width() / 2, db_box.get_center()[1], 0])
            old = self.db_state
            self.db_state = new
            anims = [FadeTransform(old, new)]
            if full:
                anims.append(db_box.animate.set_stroke(POSTGRES, 1.5, opacity=1).set_fill(POSTGRES, 0.12))
                anims.append(db_name.animate.set_opacity(1))
            return anims

        self.play(FadeIn(con.chrome), FadeIn(panel.chrome), FadeIn(tree.initial()),
                  FadeIn(db), FadeIn(db_state), run_time=0.8)

        def flash_rows(*keys, color=ACCENT):
            return flash([tree.box(k) for k in keys], color, per_box=0.35)

        # $ npm run setup
        con.add(self, c_prompt("npm run setup"), run_time=0.4)
        con.add(self, c_titre("Clean My Calanques — installation"), space=0.4)

        # 1. Prérequis
        con.add(self, c_section("Prérequis"), space=0.4)
        con.add(self, c_ligne("ok", "Node", "v24.11.0"), c_ligne("ok", "Docker Compose", "2.39.4"),
                run_time=0.5)

        # 2. Fichiers d'environnement
        con.add(self, c_section("Fichiers d'environnement"), space=0.4)
        con.add(self, c_ligne("ok", ".env (racine, lu par docker-compose)", "créé depuis .env.example"),
                extra=tree.reveal("env"))
        con.add(self, c_ligne("ok", "server/.env", "créé depuis server/.env.example"),
                extra=tree.reveal("v_env"))
        con.add(self, c_ligne("ok", "clients/web/.env.local", "créé depuis clients/web/.env.example"),
                extra=tree.reveal("w_env"))
        con.add(self, c_ligne("ok", "APP_KEY", "générée"),
                extra=tree.retag("v_env", "copié · APP_KEY", WARN))
        self.wait(0.6)

        # 3. Dépendances, dans l'ordre de PAQUETS
        con.add(self, c_section("Dépendances"), space=0.4)
        for nom, key, ms in (("contract", "c_nm", "6,8 s"), ("sdk", "s_nm", "11,2 s"),
                             ("server", "v_nm", "24,6 s"), ("clients/web", "w_nm", "17,3 s")):
            pending = con.add(self, c_en_cours(nom, "(npm ci)"), run_time=0.25)
            self.wait(0.35)
            con.resolve(self, pending, c_ligne("ok", nom, ms, gris_apres="(npm ci)"),
                        extra=tree.reveal(key))
        order = label("l'ordre compte : contract → sdk → server → clients/web", 14, GOLD)
        order.move_to([con.panel.box.get_right()[0] - 0.25 - order.get_width() / 2,
                       con.row_y(con.lines[-1][1]) + 0.02, 0])
        self.play(FadeIn(order), run_time=0.4)
        self.wait(1.2)
        self.play(FadeOut(order), run_time=0.3)

        # 4. PostgreSQL : démarré n'est pas prêt
        con.add(self, c_section("PostgreSQL"), space=0.4)
        con.add(self, c_ligne("ok", "conteneur postgres", "démarré"),
                extra=set_db("démarré", POSTGRES, full=True))
        pending = con.add(self, c_en_cours("base de données"), run_time=0.25)
        y = con.row_y(pending)
        glass = hourglass(0.3).move_to([pending.get_right()[0] + 0.35, y, 0])
        wait_note = label("pg_isready, une fois par seconde · 60 s au plus", 14, GOLD)
        wait_note.next_to(glass, RIGHT, buff=0.2)
        self.play(FadeIn(glass), FadeIn(wait_note), run_time=0.4)
        self.play(Rotate(glass, PI), run_time=0.8)
        self.play(Rotate(glass, PI), run_time=0.8)
        self.play(FadeOut(glass), FadeOut(wait_note), run_time=0.3)
        con.resolve(self, pending, c_ligne("ok", "base de données", "prête"),
                    extra=set_db("prête", POSTGRES))

        # 5. Contrat → SDK et types (npm run sync), puis les index d'AdonisJS
        con.add(self, c_section("Contrat"), space=0.4)
        pending = con.add(self, c_en_cours("bundle, SDK et types du serveur"), run_time=0.25)
        sync_note = label("= npm run sync", 14, GOLD)
        sync_note.move_to([con.panel.box.get_right()[0] - 0.25 - sync_note.get_width() / 2,
                           con.row_y(pending), 0])
        self.play(FadeIn(sync_note), run_time=0.3)
        self.wait(0.5)
        con.resolve(self, pending, c_ligne("ok", "bundle, SDK et types du serveur", "19,7 s"),
                    extra=[FadeOut(sync_note), *tree.reveal("c_dist", "s_gen", "s_dist", "v_contract")],
                    run_time=0.6)
        pending = con.add(self, c_en_cours("index des contrôleurs (.adonisjs)"), run_time=0.25)
        self.wait(0.3)
        con.resolve(self, pending, c_ligne("ok", "index des contrôleurs (.adonisjs)"),
                    extra=tree.reveal("v_adonis"))
        self.play(flash_rows("c_dist", "s_gen", "s_dist", "v_contract", "v_adonis", color=GOLD))
        gen_note = label("en doré : généré, et gitignoré", 14, GOLD)
        gen_note.move_to([con.panel.box.get_right()[0] - 0.25 - gen_note.get_width() / 2,
                          con.row_y(con.lines[-1][1]), 0])
        self.play(FadeIn(gen_note), run_time=0.4)
        self.wait(1.8)
        self.play(FadeOut(gen_note), run_time=0.3)

        # 6. Migrations, puis aucun seeder
        con.add(self, c_section("Base de données"), space=0.4)
        pending = con.add(self, c_en_cours("migrations"), run_time=0.25)
        self.wait(0.4)
        con.resolve(self, pending, c_ligne("ok", "migrations", "schéma des modèles régénéré"),
                    extra=[*tree.retag("v_schema", "régénéré", VIOLET), *set_db("migrée", POSTGRES)])
        self.play(flash_rows("v_schema", color=VIOLET))
        con.add(self, c_ligne("info", "données de démonstration", "aucun seeder pour l’instant"),
                extra=set_db("migrée · vide", POSTGRES))
        self.wait(1.2)

        # 7. Le diagnostic conclut (même code que npm run diagnostic)
        con.add(self, c_titre("Diagnostic"), space=0.5)
        groups = [
            ("Prérequis", [("ok", "Node", "v24.11.0"), ("ok", "Docker Compose", "2.39.4")]),
            ("Environnement", [("ok", ".env (racine)", None), ("ok", "server/.env", "APP_KEY renseignée"),
                               ("ok", "clients/web/.env.local", None),
                               ("ok", "identifiants de base cohérents", None)]),
            ("Dépendances", [("ok", n, None) for n in ("contract", "sdk", "server", "clients/web")]),
            ("Chaîne du contrat", [("ok", "contract/dist/openapi.json", None),
                                   ("ok", "sdk généré et construit", None),
                                   ("ok", "server/app/contract/types.ts", None),
                                   ("ok", "index Adonis (.adonisjs)", None)]),
            ("Base de données", [("ok", "conteneur postgres", "accepte les connexions"),
                                 ("ok", "migrations à jour", None)]),
            ("Bon à savoir", [("ok", "port 3333 (serveur)", "libre"),
                              ("attention", "jeux de données de démonstration",
                               "aucun seeder pour l'instant")]),
        ]
        for name, items in groups:
            con.add(self, c_section(name), *[c_ligne(e, t, d) for e, t, d in items],
                    space=0.3, run_time=0.5, lag=0.08)
        ready = con.add(
            self,
            "  " + seg("Prêt à coder.", OK_GREEN, bold=True),
            "  " + seg("1 avertissement(s)", WARN) + " " + seg("— sans conséquence pour coder.", DIM),
            space=0.5, run_time=0.6,
        )
        self.play(Indicate(ready[0], color=OK_GREEN, scale_factor=1.12), run_time=0.8)
        self.play(flash([(db_box.get_center(), db_box.get_width(), db_box.get_height())], POSTGRES, 0.8))
        self.wait(2.2)
        self.clear_stage()

    # --- 3. Encart : les deux .env à accorder -----------------------------------

    def deux_env(self):
        self.show_chip("Deux .env à garder d'accord", WARN)

        root_src = "POSTGRES_DB=clean_calanques\nPOSTGRES_USER=calanques_user\nPOSTGRES_PASSWORD=calanques_secret"
        srv_src = ("DB_HOST=127.0.0.1\nDB_PORT=5432\nDB_USER=calanques_user\n"
                   "DB_PASSWORD=calanques_secret\nDB_DATABASE=clean_calanques")
        left = EditorPanel(".env", np.array([-3.65, 0.95, 0]), 6.6, 2.75,
                           tag="lu par docker-compose", tag_color=DIM)
        right = EditorPanel("server/.env", np.array([3.65, 0.95, 0]), 6.6, 2.75,
                            tag="lu par le serveur", tag_color=DIM)
        lv = left.fit_code(CodeView(root_src, ["bash"], gutter=False), max_scale=0.82)
        rv = right.fit_code(CodeView(srv_src, ["bash"], gutter=False), max_scale=0.82)
        cap_l = label("crée le conteneur PostgreSQL", 16, DIM).next_to(left.box, DOWN, buff=0.18)
        cap_r = label("le serveur s'y connecte", 16, DIM).next_to(right.box, DOWN, buff=0.18)
        self.play(FadeIn(left.chrome), FadeIn(lv.group), FadeIn(right.chrome), FadeIn(rv.group),
                  run_time=0.8)
        self.play(FadeIn(cap_l), FadeIn(cap_r), run_time=0.5)

        pairs = [(1, "POSTGRES_DB", 5, "DB_DATABASE"), (2, "POSTGRES_USER", 3, "DB_USER"),
                 (3, "POSTGRES_PASSWORD", 4, "DB_PASSWORD")]
        links, rects = VGroup(), VGroup()
        for ll, lt, rl, rt in pairs:
            lb, rb = lv.token_box(ll, lt), rv.token_box(rl, rt)
            rects.add(highlight_rect(lb, WARN, 0.15), highlight_rect(rb, WARN, 0.15))
            start = lv.col_x(ll, len(lv.text[ll - 1]) + 1) + 0.15
            p0 = np.array([start, lb[0][1], 0])
            p1 = np.array([rb[0][0] - rb[1] / 2 - 0.08, rb[0][1], 0])
            links.add(Line(p0, p1).set_stroke(WARN, 1.8, opacity=0.85))
        self.play(LaggedStart(*[FadeIn(r) for r in rects], lag_ratio=0.15),
                  LaggedStart(*[ShowCreation(l) for l in links], lag_ratio=0.3), run_time=1.4)
        self.wait(1.0)

        # La vérification du diagnostic
        diag = Console("npm run diagnostic", np.array([0, -2.45, 0]), 13.4, 1.75, size=15)
        self.play(FadeIn(diag.chrome), run_time=0.4)
        diag.add(self, c_section("Environnement"), run_time=0.3)
        ok_line = diag.add(self, c_ligne("ok", "identifiants de base cohérents"), run_time=0.4)
        self.wait(1.8)

        # Un mot de passe modifié d'un seul côté (exemple) : le diagnostic le voit
        original = lv.lines[2].copy()
        changed = CodeView(root_src.replace("calanques_secret", "nouveau_secret"), ["bash"], gutter=False)
        changed.fit(lv.line_h / changed.line_h, lv.group.get_corner(UL))
        bad = links[2]
        self.play(Transform(lv.lines[2], changed.lines[2]), bad.animate.set_stroke(ERROR, 2.4),
                  rects[4].animate.set_stroke(ERROR).set_fill(ERROR, 0.2),
                  rects[5].animate.set_stroke(ERROR).set_fill(ERROR, 0.2), run_time=0.7)
        ko_line = diag.resolve(self, ok_line, c_ligne("ko", "identifiants de base cohérents",
                                                      "le .env racine et server/.env divergent"))
        remede = diag.add(self, "      " + seg("→", WARN) + " " + seg(
            "Le conteneur est créé avec le .env racine, le serveur se connecte avec server/.env : "
            "aligne les deux …", DIM), run_time=0.4)
        self.wait(2.8)

        # On réaligne : tout redevient vert
        self.play(Transform(lv.lines[2], original), bad.animate.set_stroke(WARN, 1.8),
                  rects[4].animate.set_stroke(WARN).set_fill(WARN, 0.15),
                  rects[5].animate.set_stroke(WARN).set_fill(WARN, 0.15), FadeOut(remede), run_time=0.7)
        diag.resolve(self, ko_line, c_ligne("ok", "identifiants de base cohérents"))
        self.wait(1.8)

        next_ep = label("épisode suivant : un YAML, quatre consommateurs  →", 16, DIM)
        next_ep.to_corner(DR, buff=0.3)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(2)
