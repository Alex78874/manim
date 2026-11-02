"""
Épisode 7 — `npm run sync` : la chaîne de génération, et pourquoi elle n'est pas versionnée

Bloc B : le dépôt au quotidien. Ce que produit la commande à lancer après
chaque `git pull`, et pourquoi un dépôt sans elle ne compile pas.
  1. Le script `sync` du package.json racine : quatre `npm --prefix`, enchaînés.
  2. Quatre stations : contract (redocly bundle, spectral lint) → sdk
     (nettoyer, orval, tsc) → server (sync-contract.mjs, openapi-typescript)
     → server (node ace codegen). Chaque produit porte un cadenas : gitignoré.
  3. Pourquoi pas versionné (ADR 0010) : deux branches régénèrent le même
     index et se marchent dessus ; le commit 30d6d92 sort 29 fichiers de git ;
     le .gitignore utilise des chemins explicites.
  4. Le prix : sans sync, TypeScript ne trouve pas '#contract/types' ;
     `npm run sync` répare.
  5. L'exception (server/database/schema.ts reste versionné) et le piège
     d'Orval qui n'élague pas ses index, d'où le script `nettoyer`.

Le code généré n'est pas dans le clone : on ne montre que des noms de fichiers,
des commandes, et un extrait réel de l'historique (30d6d92^). Les lignes du
conflit sur model/index.ts sont une illustration (noms de modèles inventés).
Les erreurs TS2307 sont le message standard de tsc, positions vérifiées sur les
imports réels.

Sources : package.json (script sync), contract/package.json,
sdk/package.json (generate, nettoyer), sdk/orval.config.ts,
server/package.json (sync:contract, codegen), server/scripts/sync-contract.mjs,
.gitignore, docs/adr/0010-code-genere-non-versionne.md, commit 30d6d92,
README.md (Le réflexe quotidien).

Rendu vidéo :  manimgl ep07_sync.py Ep07Sync -w
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
# Briques locales : cadenas, étiquettes
# ---------------------------------------------------------------------------

def padlock(color=DIM, s=1.0):
    """Un petit cadenas : « gitignoré »."""
    body = RoundedRectangle(width=0.2 * s, height=0.15 * s, corner_radius=0.03 * s)
    body.set_fill(color, 1).set_stroke(width=0)
    shackle = Arc(radius=0.062 * s, start_angle=0, angle=PI).set_stroke(color, 2.2 * s)
    shackle.move_to(body.get_top() + 0.06 * s * UP)
    legs = VGroup(
        Line(shackle.get_corner(DL), shackle.get_corner(DL) + 0.03 * s * DOWN),
        Line(shackle.get_corner(DR), shackle.get_corner(DR) + 0.03 * s * DOWN),
    ).set_stroke(color, 2.2 * s)
    return VGroup(body, shackle, legs)


def locked(text, size=14, color=GOLD):
    """Un produit généré : son chemin, précédé d'un cadenas."""
    t = label(text, size, color, font=MONO_FONT)
    lock = padlock(DIM, 0.9)
    lock.next_to(t, LEFT, buff=0.12)
    return VGroup(lock, t)


def caption(text, point, color=DIM, size=16):
    return label(text, size, color).move_to(point)


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep07Sync(EpisodeScene):
    EPISODE = "07"
    TITLE = "npm run sync : la chaîne de génération"

    def construct(self):
        self.le_script()
        self.stations()
        self.pourquoi()
        self.le_prix()
        self.exceptions()

    # --- 1. Le script -------------------------------------------------------------

    def le_script(self):
        self.show_chip("Après chaque git pull : npm run sync", GOLD)
        src = ('npm --prefix contract run validate \\\n'
               '  && npm --prefix sdk run generate \\\n'
               '  && npm --prefix server run sync:contract \\\n'
               '  && npm --prefix server run codegen')
        panel = EditorPanel("package.json", np.array([0, 0.55, 0]), 10.4, 2.75,
                            tag='script "sync", mis en forme', tag_color=DIM)
        view = panel.fit_code(CodeView(src, ["bash"]), max_scale=0.95)
        self.play(FadeIn(panel.chrome), FadeIn(view.group), run_time=0.8)
        colors = [ACCENT, GOLD, VIOLET, VIOLET]
        targets = ["contract", "sdk", "server", "server"]
        rects = VGroup(*[highlight_rect(view.token_box(i + 1, t), c, 0.16)
                         for i, (t, c) in enumerate(zip(targets, colors))])
        self.play(flash([view.line_box(i + 1) for i in range(4)], GOLD, 0.45))
        self.play(LaggedStart(*[FadeIn(r) for r in rects], lag_ratio=0.3), run_time=1.0)
        cap = VGroup(
            label("quatre paquets, un seul ordre possible : contract → sdk → server", 19, TXT),
            label("chaque && attend la réussite de l'étape précédente", 16, DIM),
        ).arrange(DOWN, buff=0.15).move_to([0, -1.9, 0])
        self.play(FadeIn(cap, shift=0.1 * UP), run_time=0.6)
        self.wait(3.0)
        self.clear_stage()

    # --- 2. Les quatre stations ---------------------------------------------------

    def stations(self):
        self.show_chip("Quatre stations", GOLD)
        xs = [-5.3, -1.77, 1.77, 5.3]
        specs = [
            ("contract/", "npm run validate", ACCENT,
             ["redocly bundle", "spectral lint"],
             ["contract/dist/openapi.json"]),
            ("sdk/", "npm run generate", GOLD,
             ["nettoyer", "orval", "tsc"],
             ["sdk/src/generated/endpoints/", "sdk/src/generated/model/", "sdk/dist/"]),
            ("server/", "npm run sync:contract", VIOLET,
             ["sync-contract.mjs", "openapi-typescript"],
             ["server/app/contract/openapi.json", "server/app/contract/types.ts"]),
            ("server/", "npm run codegen", VIOLET,
             ["node ace codegen"],
             ["server/.adonisjs/"]),
        ]
        notes = [
            "fusionne les YAML en un seul JSON",
            "client, hooks React Query, mocks MSW",
            "copie du contrat, puis ses types",
            "index des contrôleurs",
        ]
        heads, columns = VGroup(), []
        for i, (x, (title, cmd, color, steps, outs)) in enumerate(zip(xs, specs)):
            head = node(f"{i + 1} · {title}", cmd, color, width=2.95, title_size=20, subtitle_size=15)
            head.move_to([x, 1.85, 0])
            heads.add(head)
            step_mobs = VGroup(*[label(s, 16, TXT, font=MONO_FONT) for s in steps])
            step_mobs.arrange(DOWN, buff=0.34).move_to([x, 0.5, 0])
            arrows = VGroup(*[
                Arrow(step_mobs[k].get_bottom(), step_mobs[k + 1].get_top(), buff=0.04,
                      thickness=1.6).set_color(DIM)
                for k in range(len(steps) - 1)
            ])
            out_mobs = VGroup(*[locked(o, 13) for o in outs]).arrange(DOWN, buff=0.16)
            out_mobs.move_to([x, -1.25 - 0.17 * (3 - len(outs)), 0])
            for o in out_mobs:
                if o.get_width() > 3.3:
                    o.set_width(3.3)
            note = label(notes[i], 14, DIM).move_to([x, -2.55, 0])
            if note.get_width() > 3.3:
                note.set_width(3.3)
            columns.append((head, step_mobs, arrows, out_mobs, note, color))

        links = VGroup(*[
            Arrow(heads[k].get_right(), heads[k + 1].get_left(), buff=0.06, thickness=2).set_color(DIM)
            for k in range(3)
        ])
        amp = VGroup(*[label("&&", 15, DIM, font=MONO_FONT).next_to(l, UP, buff=0.05) for l in links])

        for k, (head, steps, arrows, outs, note, color) in enumerate(columns):
            anims = [FadeIn(head, shift=0.1 * DOWN)]
            if k > 0:
                anims += [GrowArrow(links[k - 1]), FadeIn(amp[k - 1])]
            self.play(*anims, run_time=0.6)
            step_anims = [LaggedStart(*[FadeIn(s, shift=0.08 * DOWN) for s in steps], lag_ratio=0.4)]
            if len(arrows):
                step_anims.append(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.4))
            self.play(*step_anims, run_time=0.6 + 0.25 * len(steps))
            self.play(LaggedStart(*[FadeIn(o, shift=0.08 * DOWN) for o in outs], lag_ratio=0.3),
                      FadeIn(note), run_time=0.8)
            self.wait(1.6)

        # sdk et server lisent tous deux le bundle de la station 1
        feed = columns[0][3][0]
        feed_rect = SurroundingRectangle(feed, buff=0.07).set_stroke(ACCENT, 1.8)
        feed_cap = label("lu par sdk ET par server : il doit exister avant eux", 14, ACCENT)
        feed_cap.next_to(feed_rect, DOWN, buff=0.12)
        fit_x(feed_cap)
        self.play(ShowCreation(feed_rect), FadeIn(feed_cap), FadeOut(columns[0][4]), run_time=0.7)
        self.wait(2.0)
        self.play(FadeOut(feed_rect), FadeOut(feed_cap), FadeIn(columns[0][4]), run_time=0.4)

        # Tous les produits sont gitignorés
        locks = [o[0] for col in columns for o in col[3]]
        bar = VGroup(padlock(GOLD, 1.3), label("= gitignoré : jamais versionné, jamais édité à la main", 19,
                                                 TXT)).arrange(RIGHT, buff=0.2).move_to([0, -3.35, 0])
        self.play(*[l.animate.set_color(GOLD) for l in locks], FadeIn(bar), run_time=0.8)
        self.play(LaggedStart(*[Indicate(l, color=GOLD, scale_factor=1.5) for l in locks], lag_ratio=0.08),
                  run_time=1.4)
        self.wait(2.6)
        self.clear_stage()

    # --- 3. Pourquoi pas versionné : ADR 0010 ---------------------------------------

    def pourquoi(self):
        self.show_chip("Pourquoi pas versionné ? ADR 0010", WARN)

        # Deux branches, la même commande, le même fichier régénéré
        y_main = 1.95
        main = Line([-5.95, y_main, 0], [-0.4, y_main, 0]).set_stroke(DIM, 3)
        main_lbl = label("main", 16, DIM, font=MONO_FONT).next_to(main, LEFT, buff=0.12)
        fit_x(main_lbl)
        a_pts = [[-5.4, y_main, 0], [-4.6, 1.15, 0], [-2.4, 1.15, 0]]
        b_pts = [[-5.4, y_main, 0], [-4.6, 0.3, 0], [-2.4, 0.3, 0]]

        def branch(pts, color):
            path = VMobject().set_points_as_corners([np.array(p) for p in pts]).set_stroke(color, 3)
            commit = Dot(pts[-1], radius=0.09).set_fill(color, 1)
            return VGroup(path, commit)

        br_a = branch(a_pts, VIOLET)
        br_b = branch(b_pts, BLUE)
        lab_a = label("feature/brigades", 15, VIOLET, font=MONO_FONT).move_to([-3.55, 1.32, 0])
        lab_b = label("feature/ramassages", 15, BLUE, font=MONO_FONT).move_to([-3.55, 0.5, 0])
        sync_a = label("npm run sync", 13, DIM, font=MONO_FONT).next_to(br_a[1], DOWN, buff=0.1)
        sync_b = label("npm run sync", 13, DIM, font=MONO_FONT).next_to(br_b[1], DOWN, buff=0.1)
        merge_pt = np.array([-0.4, y_main, 0])
        merge_a = Line(a_pts[-1], merge_pt).set_stroke(VIOLET, 2.4)
        merge_b = Line(b_pts[-1], merge_pt).set_stroke(BLUE, 2.4)
        self.play(ShowCreation(main), FadeIn(main_lbl), run_time=0.6)
        self.play(ShowCreation(br_a), ShowCreation(br_b), FadeIn(lab_a), FadeIn(lab_b), run_time=1.0)
        self.play(FadeIn(sync_a), FadeIn(sync_b), run_time=0.4)
        self.play(ShowCreation(merge_a), ShowCreation(merge_b), run_time=0.7)

        # Le conflit, sur un fichier que personne n'écrit
        src = ("export * from './creationUtilisateur';\n"
               "<<<<<<< feature/brigades\n"
               "export * from './listeBrigades';\n"
               "=======\n"
               "export * from './listeRamassages';\n"
               ">>>>>>> feature/ramassages\n"
               "export * from './listeUtilisateurs';")
        panel = EditorPanel("sdk/src/generated/model/index.ts", np.array([3.6, 1.05, 0]), 6.9, 3.1,
                            tag="illustration", tag_color=DIM)
        view = panel.fit_code(CodeView(src, ["typescript"], gutter=False), max_scale=0.74)
        conflict = VGroup(*[highlight_rect(view.line_box(i), ERROR, 0.14) for i in (2, 3, 4, 5, 6)])
        self.play(FadeIn(panel.chrome), FadeIn(view.group), run_time=0.7)
        self.play(LaggedStart(*[FadeIn(r) for r in conflict], lag_ratio=0.15), run_time=1.0)
        stamp = label("conflit sur un fichier que personne n'écrit", 17, ERROR, bold=True)
        stamp.next_to(panel.box, DOWN, buff=0.18)
        self.play(FadeIn(stamp, scale=1.2), Flash(merge_pt, color=ERROR, flash_radius=0.3), run_time=0.6)
        self.wait(2.4)

        # Les chiffres réels du commit 30d6d92
        nums = VGroup(
            label("29", 46, ERROR, bold=True),
            label("fichiers générés étaient suivis par git", 18, TXT),
            label("18 dans sdk/src/generated · 9 dans server/.adonisjs · 2 dans server/app/contract", 15, DIM),
        )
        nums[1].next_to(nums[0], RIGHT, buff=0.3)
        nums[2].next_to(VGroup(nums[0], nums[1]), DOWN, buff=0.15)
        nums.move_to([-3.1, -1.2, 0])
        fit_x(nums)
        times = label("× 14 fonctionnalités en parallèle en mars", 18, WARN).next_to(nums, DOWN, buff=0.3)
        times.align_to(nums, LEFT)
        self.play(FadeIn(nums, shift=0.1 * UP), run_time=0.7)
        self.play(FadeIn(times), run_time=0.5)
        self.wait(2.0)

        decision = VGroup(
            label("Décision (ADR 0010, commit 30d6d92)", 17, ACCENT, bold=True),
            label("le code généré est exclu du dépôt,", 17, TXT),
            label("et régénéré par npm run setup / npm run sync", 17, TXT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        box = SurroundingRectangle(decision, buff=0.22).set_fill(ACCENT, 0.08).set_stroke(ACCENT, 1.8)
        dec = VGroup(box, decision).move_to([3.55, -1.65, 0])
        fit_x(dec)
        self.play(FadeIn(dec, shift=0.1 * UP), run_time=0.7)
        self.wait(3.0)
        self.clear_stage()

        # Le .gitignore : des chemins explicites
        self.show_chip("Le .gitignore : des chemins explicites", WARN)
        gi = ("dist/\n"
              "…\n"
              "# Code généré depuis contract/dist/openapi.json.\n"
              "#\n"
              "# CHEMINS EXPLICITES, et c'est nécessaire : un motif qui contient un \"/\" est\n"
              "# ancré au dossier du .gitignore. `src/generated/` ne matchait donc PAS\n"
              "# `sdk/src/generated/`, et `app/contract/` ne matchait pas\n"
              "# `server/app/contract/`. Ces règles n'ont jamais fonctionné ; les fichiers\n"
              "# étaient suivis par git, ce qui masquait le problème.\n"
              "sdk/src/generated/\n"
              "server/app/contract/\n"
              "server/.adonisjs/")
        panel = EditorPanel(".gitignore", np.array([0, -0.3, 0]), 12.6, 5.0, tag="extrait", tag_color=DIM)
        view = panel.fit_code(CodeView(gi, ["bash"], gutter=False), max_scale=0.82)
        self.play(FadeIn(panel.chrome), FadeIn(view.group), run_time=0.8)
        rects = VGroup(highlight_rect(view.line_box(1), GOLD, 0.15),
                       *[highlight_rect(view.line_box(i), GOLD, 0.15) for i in (10, 11, 12)])
        self.play(flash([view.line_box(i) for i in (5, 6, 7)], WARN, 0.6))
        self.play(LaggedStart(*[FadeIn(r) for r in rects], lag_ratio=0.2), run_time=1.0)
        self.wait(3.8)
        self.clear_stage()

    # --- 4. Le prix : sans sync, rien ne compile ---------------------------------------

    def le_prix(self):
        self.show_chip("Le prix : sans sync, le serveur ne compile pas", ERROR)
        con = Console("terminal · server/", np.array([0, -0.05, 0]), 13.8, 4.8, size=14)
        ctx = label("dépôt récupéré, dépendances installées, pas encore de sync", 15, DIM)
        ctx.move_to([0, 2.65, 0])
        self.play(FadeIn(con.chrome), FadeIn(ctx), run_time=0.6)
        con.add(self, c_prompt("npm run typecheck"), run_time=0.4)
        con.add(self, seg("> @cmc/server@0.0.0 typecheck", DIM), seg("> tsc --noEmit", DIM),
                space=0.3, run_time=0.4)
        msg_t = "error TS2307: Cannot find module '#contract/types' or its corresponding type declarations."
        msg_g = ("error TS2307: Cannot find module '#generated/controllers' or its corresponding "
                 "type declarations.")

        def err(path, pos, msg):
            return seg(path, BLUE) + seg(":" + pos, WARN) + seg(" - ", DIM) + seg(msg, ERROR)

        errs = con.add(
            self,
            err("app/services/contract_validator.ts", "5:33", msg_t),
            err("app/services/utilisateurs_service.ts", "4:33", msg_t),
            err("start/routes/utilisateurs.ts", "3:29", msg_g),
            seg("…", DIM),
            space=0.4, run_time=1.0, lag=0.3,
        )
        self.wait(1.8)
        why = VGroup(
            label("server/app/contract/types.ts et server/.adonisjs/ n'existent pas encore :", 16, TXT),
            label("ils sont générés, donc absents de git", 16, GOLD),
        ).arrange(DOWN, buff=0.1)
        why.move_to([0, -3.15, 0])
        self.play(FadeIn(why), run_time=0.5)
        self.wait(2.6)
        self.play(FadeOut(why), run_time=0.3)

        con.add(self, c_prompt("npm run sync") + seg("   (depuis la racine)", DIM), space=0.5, run_time=0.4)
        con.add(self, seg("…", DIM), seg("  contrat copié  -> app/contract/openapi.json", TXT),
                seg("…", DIM), run_time=0.8, lag=0.3)
        con.add(self, c_prompt("npm run typecheck"), space=0.5, run_time=0.4)
        con.add(self, seg("> @cmc/server@0.0.0 typecheck", DIM), seg("> tsc --noEmit", DIM),
                run_time=0.4)
        ok = label("aucune erreur", 18, OK_GREEN, bold=True)
        ok.move_to([con.panel.box.get_right()[0] - 0.4 - ok.get_width() / 2,
                    con.row_y(con.lines[-1][1]), 0])
        self.play(FadeIn(ok, scale=1.2), *[e.animate.set_opacity(0.35) for e in errs], run_time=0.6)
        self.wait(2.8)
        self.clear_stage()

    # --- 5. L'exception, et le piège d'Orval ---------------------------------------------

    def exceptions(self):
        self.show_chip("Une exception, et un piège", VIOLET)

        # L'exception : schema.ts est versionné
        card_txt = VGroup(
            label("server/database/schema.ts", 19, VIOLET, font=MONO_FONT, bold=True),
            label("généré lui aussi, mais VERSIONNÉ", 17, TXT),
            label("régénéré par node ace migration:run", 15, DIM),
            label("nécessaire au typecheck (épisode 15)", 15, DIM),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        card = SurroundingRectangle(card_txt, buff=0.28).set_fill(VIOLET, 0.07).set_stroke(VIOLET, 1.8)
        exc = VGroup(card, card_txt).move_to([-4.15, 0.9, 0])
        self.play(FadeIn(exc, shift=0.1 * UP), run_time=0.7)

        # Le piège : Orval n'élague pas ses index (extrait réel, historique 30d6d92^)
        src = ("export * from './apiError.js';\n"
               "export * from './apiError';\n"
               "export * from './apiErrorDetailsItem.js';\n"
               "export * from './apiErrorDetailsItem';\n"
               "…")
        panel = EditorPanel("sdk/src/generated/model/index.ts", np.array([2.75, 0.9, 0]), 7.6, 2.75,
                            tag="historique 30d6d92^", tag_color=DIM)
        view = panel.fit_code(CodeView(src, ["typescript"], gutter=False), max_scale=0.75)
        self.play(FadeIn(panel.chrome), FadeIn(view.group), run_time=0.7)
        self.play(flash([view.line_box(1), view.line_box(2), view.line_box(3), view.line_box(4)], WARN, 0.4))
        trap = VGroup(
            label("Orval ajoute à ses index, il n'en retire jamais rien :", 17, TXT),
            label("un tag renommé laisse un export * vers un fichier disparu, et tsc passe au rouge", 16, WARN),
        ).arrange(DOWN, buff=0.12).move_to([0, -1.25, 0])
        self.play(FadeIn(trap, shift=0.1 * UP), run_time=0.6)
        self.wait(3.0)

        fix_panel = EditorPanel("sdk/package.json", np.array([0, -2.85, 0]), 9.6, 1.25,
                                tag="d'où « nettoyer » : ardoise vide", tag_color=ACCENT)
        fix_view = fix_panel.fit_code(CodeView('"generate": "npm run nettoyer && orval && tsc",', ["json"],
                                               gutter=False), max_scale=0.8)
        self.play(FadeIn(fix_panel.chrome), FadeIn(fix_view.group), run_time=0.6)
        self.play(FadeIn(highlight_rect(fix_view.token_box(1, "npm run nettoyer"), ACCENT, 0.18)), run_time=0.5)
        self.wait(3.0)

        next_ep = label("épisode suivant : le serveur refuse de démarrer  →", 16, DIM)
        next_ep.to_corner(DR, buff=0.3)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(1.5)
