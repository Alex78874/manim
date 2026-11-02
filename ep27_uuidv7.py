"""
Épisode 27 — UUIDv7 fourni par le client (ADR 0012)

Bloc E : les règles hors ligne non négociables.
  1. Le problème : hors réseau, un bilan puis trois participants qui pointent
     vers lui. Avec un identifiant donné par le serveur, ils pointent vers « ??? ».
     Avec un identifiant minté par le téléphone, ils sont valides tout de suite.
  2. Un UUIDv7 se fabrique : 48 bits d'horodatage, le « 7 » de la version,
     le variant [89ab], le reste aléatoire (exemple de UuidV7.yaml).
  3. Dans l'index (B-tree, schématique) : les v4 tombent au hasard, les v7
     s'ajoutent en fin. Ce qui naît côté serveur garde gen_random_uuid() (v4).
  4. Le contrat refuse un v4 : le `pattern` de UuidV7.yaml, et le test que
     génère `npm run feature` (400 VALIDATION_ERROR, aucune ligne de code serveur).

Statut affiché : documenté + dans le gabarit `npm run feature`. UuidV7.yaml
existe dans le contrat mais n'est référencé que par le gabarit : aucune
opération actuelle ne l'utilise. Côté téléphone, aucune bibliothèque UUIDv7
n'est encore choisie (l'app n'existe pas).

Sources : docs/adr/0012-identifiants-uuidv7-generes-par-le-client.md,
docs/adr/0006 (annexe §4.2), contract/features/_shared/schemas/UuidV7.yaml:28-36,
scripts/feature.mjs:141-174 (CreationX.yaml), 259-264 (migration), 447-491 (test),
server/app/middleware/contract_middleware.ts (VALIDATION_ERROR),
server/database/migrations/1761885935168_create_users_table.ts:25.

Rendu vidéo :  manimgl ep27_uuidv7.py Ep27Uuidv7 -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


# ---------------------------------------------------------------------------
# Briques propres au bloc E (copiées d'un épisode à l'autre : cmc_style est figé)
# ---------------------------------------------------------------------------

STATUTS = [
    ("documenté", VIOLET),
    ("dans le gabarit npm run feature", GOLD),
    ("codé", ACCENT),
]


def status_banner(actifs, note=None):
    """Bandeau discret en bas : les trois statuts, seuls les actifs sont allumés."""
    pills = VGroup()
    for nom, color in STATUTS:
        on = nom in actifs
        t = label(nom, 13, color if on else DIM, bold=on)
        bg = RoundedRectangle(width=t.get_width() + 0.3, height=0.3, corner_radius=0.15)
        bg.set_fill(color, 0.16 if on else 0).set_stroke(color if on else PANEL_STROKE, 1.2)
        t.move_to(bg)
        pills.add(VGroup(bg, t))
    pills.arrange(RIGHT, buff=0.15)
    row = VGroup(label("statut", 13, DIM), pills)
    if note:
        row.add(label(note, 13, DIM))
    row.arrange(RIGHT, buff=0.25)
    return row.move_to([0, -3.7, 0])


def fit_w(mob, w):
    if mob.get_width() > w:
        mob.set_width(w)
    return mob


def pill(text, color, size=13, fill=0.2, font=UI_FONT):
    t = label(text, size, color, font=font, bold=True)
    bg = RoundedRectangle(width=t.get_width() + 0.3, height=t.get_height() + 0.18, corner_radius=0.13)
    bg.set_fill(color, fill).set_stroke(color, 1.4)
    t.move_to(bg)
    return VGroup(bg, t)


V7 = "019298b4-7c3a-7def-8a1b-2f4e6c8d0a12"     # l'exemple de UuidV7.yaml
V4 = "7c3a0192-98b4-4def-8a1b-2f4e6c8d0a12"     # ID_V4 du test généré


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep27Uuidv7(EpisodeScene):
    EPISODE = "27"
    TITLE = "UUIDv7 fourni par le client"

    def construct(self):
        self.set_banner({"documenté", "dans le gabarit npm run feature"},
                        "UuidV7.yaml : aucune opération actuelle ne le référence")
        self.probleme()
        self.anatomie()
        self.index()
        self.contrat()

    def set_banner(self, actifs, note=None):
        new = status_banner(actifs, note)
        old = getattr(self, "banner", None)
        if old is None:
            self.play(FadeIn(new), run_time=0.5)
        else:
            self.permanent.discard(old)
            self.play(FadeTransform(old, new), run_time=0.5)
        self.banner = new
        self.permanent.add(new)

    # --- 1. Un identifiant qu'on n'a pas encore ------------------------------------

    def probleme(self):
        self.show_chip("Hors réseau : qui donne l'identifiant ?", ERROR)

        ph = phone().move_to([-5.2, -0.45, 0])
        bars = signal_bars(0, ERROR).move_to(ph[1].get_corner(UR) + np.array([-0.3, -0.16, 0]))
        no_net = label("aucun réseau", 15, ERROR, bold=True).next_to(ph, UP, buff=0.15)
        screen = VGroup(
            label("Bilan · Sugiton", 16, ACCENT, bold=True),
            label("+ Léa", 14, TXT), label("+ Karim", 14, TXT), label("+ Inès", 14, TXT),
        ).arrange(DOWN, buff=0.2).move_to(ph[1])
        self.play(FadeIn(ph, shift=0.2 * UP), FadeIn(bars), FadeIn(no_net), FadeIn(screen[0]), run_time=0.7)
        self.play(LaggedStartMap(FadeIn, screen[1:], shift=0.1 * DOWN, lag_ratio=0.3), run_time=0.9)
        self.wait(0.8)

        # Le graphe des actions en file : trois participants pointent vers le bilan
        def bilan_node(id_text, color):
            return node("bilan", f"id : {id_text}", color, width=3.4, title_size=20, subtitle_size=15)

        bil = bilan_node("???", ERROR).move_to([1.6, 1.3, 0])
        parts = VGroup(*[
            node("participant", name, DIM, width=2.2, title_size=17, subtitle_size=14)
            for name in ("Léa", "Karim", "Inès")
        ]).arrange(RIGHT, buff=0.45).move_to([1.6, -1.25, 0])
        arrows = VGroup(*[link(edge_point(p, UP), edge_point(bil, DOWN) + (i - 1) * 0.9 * RIGHT, ERROR)
                          for i, p in enumerate(parts)])
        frame_lbl = label("actions en file d'attente sur le téléphone", 15, DIM).move_to([1.6, 2.35, 0])
        self.play(FadeIn(frame_lbl), FadeIn(bil), run_time=0.6)
        self.play(LaggedStartMap(FadeIn, parts, shift=0.1 * UP, lag_ratio=0.2),
                  LaggedStartMap(GrowArrow, arrows, lag_ratio=0.2), run_time=1.0)
        why = label("si c'est le serveur qui le donne : pas avant le retour du réseau, dans cinq heures",
                    16, ERROR).move_to([1.6, -2.45, 0])
        fit_w(why, 8.6)
        self.play(FadeIn(why), Indicate(bil, color=ERROR, scale_factor=1.05), run_time=0.8)
        self.wait(2.4)

        # L'alternative écartée
        alt = VGroup(
            label("id temporaire + table de correspondance", 16, DIM),
            label("+ réécriture de chaque action en file", 16, DIM),
            label("deux fois le code, même résultat : écarté", 16, WARN, bold=True),
        ).arrange(DOWN, buff=0.08).move_to([1.6, -2.55, 0])
        self.play(FadeOut(why), run_time=0.3)
        self.play(FadeIn(alt), run_time=0.5)
        self.wait(2.6)

        # La décision : le téléphone minte l'identifiant
        good = bilan_node("019298b4-…", ACCENT).move_to(bil)
        green = VGroup(*[link(edge_point(p, UP), edge_point(good, DOWN) + (i - 1) * 0.9 * RIGHT, ACCENT)
                         for i, p in enumerate(parts)])
        mint_arrow = Arrow(ph.get_right() + 1.1 * UP, good.get_left(), buff=0.15).set_color(ACCENT)
        mint = label("UUIDv7 minté par le téléphone", 15, ACCENT, bold=True)
        mint.next_to(mint_arrow.get_center(), UP, buff=0.25).shift(0.3 * LEFT)
        ok = label("valides tout de suite, rien à réécrire", 18, ACCENT, bold=True).move_to(alt)
        self.play(FadeTransform(bil, good), *[Transform(a, g) for a, g in zip(arrows, green)],
                  GrowArrow(mint_arrow), FadeIn(mint), FadeOut(alt), run_time=1.0)
        self.play(FadeIn(ok, shift=0.1 * UP), run_time=0.5)
        self.wait(2.8)
        self.clear_stage()

    # --- 2. L'anatomie d'un UUIDv7 ---------------------------------------------------

    def anatomie(self):
        self.show_chip("Un UUIDv7 se fabrique", GOLD)
        colors = []
        for i, c in enumerate(V7):
            if i < 13:
                colors.append(ACCENT if c != "-" else DIM)
            elif i == 14:
                colors.append(GOLD)
            elif i == 19:
                colors.append(VIOLET)
            else:
                colors.append(DIM if c == "-" else TXT)
        spans = "".join(f'<span foreground="{col}">{c}</span>' for c, col in zip(V7, colors))
        uid = markup(spans, size=40, font=MONO_FONT).move_to([0, 0.55, 0])
        plain = label(V7, 40, TXT, font=MONO_FONT).move_to(uid)
        self.play(FadeIn(plain, shift=0.1 * UP), run_time=0.6)
        self.wait(0.6)
        self.play(FadeTransform(plain, uid), run_time=0.6)

        n = len(V7)
        left, right = uid.get_left()[0], uid.get_right()[0]
        cw = (right - left) / n

        def span_x(a, b):
            return left + a * cw, left + b * cw

        def bracket(a, b, color, text, depth, size=16, up=False, side="center"):
            x0, x1 = span_x(a, b)
            sgn = 1 if up else -1
            y = (uid.get_top()[1] if up else uid.get_bottom()[1]) + sgn * 0.12
            yb = y + sgn * depth
            line = VMobject().set_points_as_corners([[x0 + 0.03, y, 0], [x0 + 0.03, yb, 0],
                                                     [x1 - 0.03, yb, 0], [x1 - 0.03, y, 0]])
            line.set_stroke(color, 2)
            mid = (x0 + x1) / 2
            t = label(text, size, color, bold=True).next_to([mid, yb, 0], UP if up else DOWN, buff=0.12)
            if side == "left":
                t.set_x(x0 - 0.1 - t.get_width() / 2).set_y(yb)
            elif side == "right":
                t.set_x(x1 + 0.1 + t.get_width() / 2).set_y(yb)
            fit_x(t)
            return VGroup(line, t)

        b_time = bracket(0, 13, ACCENT, "horodatage : 48 bits, en millisecondes", 0.25)
        b_ver = bracket(14, 15, GOLD, "« 7 » : la version", 0.55, up=True, side="left")
        b_var = bracket(19, 20, VIOLET, "[89ab] : le variant", 0.55, up=True, side="right")
        b_rand = bracket(20, 36, DIM, "aléatoire", 0.25)
        b_time[1].set_x(span_x(0, 13)[0] + b_time[1].get_width() / 2)
        date = label("0x019298b47c3a ms → 17/10/2024 04:20:18 UTC", 15, DIM, font=MONO_FONT)
        date.next_to(b_time[1], DOWN, buff=0.1).align_to(b_time[1], LEFT)
        fit_x(date)
        self.play(ShowCreation(b_time[0]), FadeIn(b_time[1]), run_time=0.7)
        self.play(FadeIn(date), run_time=0.5)
        self.wait(1.8)
        self.play(ShowCreation(b_ver[0]), FadeIn(b_ver[1]), run_time=0.6)
        self.wait(0.6)
        self.play(ShowCreation(b_var[0]), FadeIn(b_var[1]), run_time=0.6)
        self.wait(0.6)
        self.play(ShowCreation(b_rand[0]), FadeIn(b_rand[1]), run_time=0.6)
        src = label("exemple de contract/features/_shared/schemas/UuidV7.yaml", 14, DIM).move_to([0, -1.75, 0])
        self.play(FadeIn(src), run_time=0.4)
        conseq = label("même longueur, même type de colonne qu'un v4 : seuls ces repères changent", 18, TXT)
        conseq.move_to([0, -2.4, 0])
        self.play(FadeIn(conseq, shift=0.1 * UP), run_time=0.6)
        self.wait(3.0)
        self.clear_stage()

    # --- 3. Dans l'index ---------------------------------------------------------------

    def index(self):
        self.show_chip("Dans l'index de la base (schéma)", BLUE)
        rng = np.random.default_rng(11)

        def row(y, title, color):
            pages = VGroup(*[
                RoundedRectangle(width=1.25, height=0.6, corner_radius=0.06)
                .set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
                for _ in range(6)
            ]).arrange(RIGHT, buff=0.18).move_to([0.9, y, 0])
            t = label(title, 19, color, bold=True).next_to(pages, LEFT, buff=0.45)
            return pages, t

        p4, t4 = row(1.2, "v4", WARN)
        p7, t7 = row(-0.9, "v7", ACCENT)
        lbl4 = label("aléatoire : les insertions tombent au hasard, l'index se fragmente", 16, DIM)
        lbl4.next_to(p4, DOWN, buff=0.2)
        lbl7 = label("horodaté : les insertions se font en fin d'index", 16, DIM)
        lbl7.next_to(p7, DOWN, buff=0.2)
        self.play(FadeIn(p4), FadeIn(t4), FadeIn(p7), FadeIn(t7), run_time=0.6)

        # v4 : au hasard
        fills4 = [0] * 6
        anims = []
        drops = VGroup()
        for k in range(10):
            i = int(rng.integers(0, 6))
            fills4[i] += 1
            dot = packet(WARN, 0.06).move_to(p4[i].get_center() + np.array([-0.45 + 0.13 * fills4[i], 0, 0]))
            drops.add(dot)
        self.play(LaggedStart(*[FadeIn(d, shift=0.5 * DOWN) for d in drops], lag_ratio=0.25),
                  LaggedStart(*[Indicate(p4[int(np.argmin([np.linalg.norm(d.get_center() - p.get_center())
                                                             for p in p4]))], color=WARN, scale_factor=1.06)
                                for d in drops], lag_ratio=0.25),
                  run_time=2.0)
        self.play(FadeIn(lbl4), run_time=0.4)

        # v7 : toujours à droite
        drops7 = VGroup()
        last = p7[-1]
        for k in range(6):
            dot = packet(ACCENT, 0.06).move_to(last.get_center() + np.array([-0.45 + 0.15 * k, 0, 0]))
            drops7.add(dot)
        self.play(LaggedStart(*[FadeIn(d, shift=0.5 * DOWN) for d in drops7], lag_ratio=0.3),
                  Indicate(last, color=ACCENT, scale_factor=1.06), run_time=1.6)
        new_page = last.copy().next_to(last, RIGHT, buff=0.18)
        fit_x(new_page, 0.2)
        new_dots = VGroup(*[packet(ACCENT, 0.06).move_to(new_page.get_center() + np.array([-0.45 + 0.15 * k, 0, 0]))
                            for k in range(2)])
        self.play(FadeIn(new_page, shift=0.2 * LEFT), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(d, shift=0.5 * DOWN) for d in new_dots], lag_ratio=0.3), run_time=0.6)
        self.play(FadeIn(lbl7), run_time=0.4)
        self.wait(2.0)

        honest = VGroup(
            label("aux volumes du projet, l'écart serait difficile à mesurer : mais il est gratuit aujourd'hui", 16, TXT),
            label("ce qui naît côté serveur (back-office, reprise) garde gen_random_uuid() : un v4, même colonne",
                  16, DIM),
        ).arrange(DOWN, buff=0.14).move_to([0, -2.7, 0])
        for h in honest:
            fit_w(h, 13.2)
        self.play(FadeIn(honest, shift=0.1 * UP), run_time=0.7)
        self.wait(3.4)
        self.clear_stage()

    # --- 4. Le contrat refuse un v4 -------------------------------------------------------

    def contrat(self):
        self.show_chip("Le contrat refuse toute autre version", ACCENT)
        yaml_src = (
            "type: string\n"
            "format: uuid\n"
            "pattern: '^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'\n"
            "example: 019298b4-7c3a-7def-8a1b-2f4e6c8d0a12"
        )
        panel = EditorPanel("contract/features/_shared/schemas/UuidV7.yaml", [0, 1.45, 0], width=13.4,
                            height=2.0, tag="lignes 28 à 36", tag_color=DIM)
        view = CodeView(yaml_src, ["yaml"])
        panel.fit_code(view, max_scale=0.75)
        self.play(FadeIn(panel.chrome), FadeIn(view.group), run_time=0.7)

        fmt = highlight_rect(view.token_box(2, "format: uuid"), WARN)
        note_fmt = label("format: uuid accepte aussi un v4…", 15, WARN).next_to(panel.box, DOWN, buff=0.15)
        note_fmt.align_to(panel.box, LEFT).shift(0.3 * RIGHT)
        self.play(FadeIn(fmt), FadeIn(note_fmt), run_time=0.5)
        self.wait(1.6)
        pat_line = view.text[2]
        i7 = pat_line.find("-7[") + 1
        i89 = pat_line.find("[89ab]")
        boxes = [view.span_box(3, i7, 1), view.span_box(3, i89, 6)]
        self.play(flash(boxes, ACCENT, 0.6))
        marks = VGroup(highlight_rect(boxes[0], GOLD), highlight_rect(boxes[1], VIOLET))
        note_pat = label("…le pattern exige le « 7 » et le variant", 15, ACCENT)
        note_pat.next_to(note_fmt, RIGHT, buff=0.3)
        self.play(FadeIn(marks), FadeIn(note_pat), run_time=0.5)
        self.wait(2.2)

        # Le test généré par npm run feature
        test_src = (
            "/** Un UUID version 4. Bien formé, et REFUSÉ par le contrat (ADR 0012). */\n"
            "const ID_V4 = '7c3a0192-98b4-4def-8a1b-2f4e6c8d0a12'\n"
            "…\n"
            "const reponse = await client.post('/api/v1/ramassages').json({ id: ID_V4 })\n"
            "reponse.assertStatus(400)\n"
            "reponse.assertBodyContains({ code: 'VALIDATION_ERROR' })"
        )
        tpanel = EditorPanel("server/tests/functional/ramassages.spec.ts", [0, -1.45, 0], width=13.4,
                             height=2.5, tag="généré par npm run feature ramassages", tag_color=GOLD)
        tview = CodeView(test_src, ["typescript"])
        tpanel.fit_code(tview, max_scale=0.72)
        self.play(FadeIn(tpanel.chrome), FadeIn(tview.group), run_time=0.7)
        self.wait(1.0)
        self.play(flash([tview.token_box(2, "4def")], WARN, 0.6))
        self.play(flash([tview.line_box(5), tview.line_box(6)], ACCENT, 0.5))
        res = VGroup(highlight_rect(tview.line_box(5), ACCENT), highlight_rect(tview.line_box(6), ACCENT))
        self.play(FadeIn(res), run_time=0.4)
        self.wait(1.0)

        punch = label("refusé par le CONTRAT, à l'entrée : aucune ligne de code serveur", 18, TXT, bold=True)
        punch_bg = SurroundingRectangle(punch, buff=0.14).set_fill(BG, 0.95).set_stroke(ACCENT, 1.2)
        VGroup(punch_bg, punch).move_to([0, -3.15, 0])
        self.play(FadeIn(punch_bg), FadeIn(punch), run_time=0.6)
        self.wait(3.5)
