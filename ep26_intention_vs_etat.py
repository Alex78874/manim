"""
Épisode 26 — Intention relative contre état calculé (ADR 0007)

Bloc E : les règles hors ligne non négociables.
  1. État calculé : deux référent·es hors réseau lisent `stock: 15`, retirent
     trois pinces chacun·e et envoient `PATCH {stock: 12}`. Le serveur affiche 12
     alors que 6 pinces sont sorties : une mise à jour perdue.
  2. Intention relative : `POST /materiels/{id}/retraits {quantite: 3}` deux
     fois, le serveur calcule 9. Le bloc « à ne pas faire / à faire » de l'ADR.
  3. Le 409 qui arrive cinq heures après : la dernière place d'une sortie.
     A s'inscrit hors ligne à 9h, B en ligne à 11h, A rejoue à 14h et reçoit 409.
     Les quatre ressources arbitrées par le serveur, et la question ouverte.
  4. Encart : les actions nommées (un nom, pas un verbe) et le `:annuler` écarté.

Statut affiché : documenté (ADR 0006, ADR 0007, docs/vocabulaire.md). Aucune de
ces routes n'existe encore dans le dépôt, et le gabarit `npm run feature` ne
génère pas encore d'action nommée (README, « Ce que le squelette porte déjà »).

Sources : docs/adr/0007-operations-non-crud-en-actions-nommees.md,
docs/adr/0006-file-d-attente-hors-ligne.md (annexe §2, §4.4, §9),
docs/vocabulaire.md (« Les actions, et leur forme »), CLAUDE.md:52-53.

Rendu vidéo :  manimgl ep26_intention_vs_etat.py Ep26IntentionVsEtat -w
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


def small_phone(center, who, bars=0):
    """Un petit téléphone, avec son réseau et le nom de son ou sa référent·e."""
    ph = phone(width=1.55, height=2.9).move_to(center)
    scr = ph[1]
    b = signal_bars(bars, ERROR if bars == 0 else ACCENT)
    b.move_to(scr.get_corner(UR) + np.array([-0.27, -0.15, 0]))
    tag = VGroup(star_person(0.75), label(who, 15, GOLD, bold=True)).arrange(RIGHT, buff=0.12)
    tag.next_to(ph, UP, buff=0.15)
    return ph, b, tag


def request_box(text, color):
    t = label(text, 13, TXT, font=MONO_FONT)
    bg = RoundedRectangle(width=t.get_width() + 0.24, height=t.get_height() + 0.2, corner_radius=0.08)
    bg.set_fill(PANEL_BG, 1).set_stroke(color, 1.5)
    t.move_to(bg)
    return VGroup(bg, t)


def pince():
    return RoundedRectangle(width=0.14, height=0.38, corner_radius=0.05).set_fill("#C2B280", 1).set_stroke(width=0)


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep26IntentionVsEtat(EpisodeScene):
    EPISODE = "26"
    TITLE = "Intention relative contre état calculé"

    def construct(self):
        self.set_banner({"documenté"}, "ADR 0006 · 0007 · aucune de ces routes n'existe encore")
        self.stock(intent=False)
        self.stock(intent=True)
        self.regle()
        self.conflit()
        self.actions_nommees()

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

    # --- 1 et 2. Le stock de pinces -------------------------------------------------

    def stock(self, intent):
        if intent:
            self.show_chip("Une intention relative : le serveur calcule", ACCENT)
        else:
            self.show_chip("Un état calculé : la mise à jour perdue", ERROR)

        phones = []
        for who, x in (("A", -5.75), ("B", -3.75)):
            ph, bars, tag = small_phone([x, -0.55, 0], who, 0)
            read = label("stock lu : 15", 13, TXT, font=MONO_FONT)
            phones.append(dict(ph=ph, bars=bars, tag=tag, read=read, scr=ph[1]))

        srv = node("server/", "AdonisJS", VIOLET, width=2.3).move_to([1.2, 1.05, 0])
        stock_lbl = label("stock en base", 15, DIM).move_to([1.2, 0.0, 0])
        stock_box = RoundedRectangle(width=1.5, height=0.95, corner_radius=0.14)
        stock_box.set_fill(PANEL_BG, 1).set_stroke(VIOLET, 1.5).move_to([1.2, -0.75, 0])
        stock_val = label("15", 40, TXT, bold=True).move_to(stock_box)

        # La réserve réelle : 15 pinces
        reserve = VGroup(*[pince() for _ in range(15)]).arrange_in_grid(n_rows=3, n_cols=5, buff=0.16)
        reserve.move_to([5.0, -0.55, 0])
        res_box = SurroundingRectangle(reserve, buff=0.25).set_stroke(PANEL_STROKE, 1.2).set_fill(PANEL_BG, 1)
        res_title = label("dans la réserve", 15, DIM).next_to(res_box, UP, buff=0.15)
        res_count = label("15", 22, TXT, bold=True).next_to(res_box, DOWN, buff=0.15)

        offline = label("hors réseau, A et B ont lu stock : 15", 17, DIM).move_to([-4.75, 1.85, 0])
        self.play(
            *[FadeIn(VGroup(p["ph"], p["bars"], p["tag"])) for p in phones],
            FadeIn(srv), FadeIn(stock_lbl), FadeIn(stock_box), FadeIn(stock_val),
            FadeIn(res_box), FadeIn(reserve), FadeIn(res_title), FadeIn(res_count),
            run_time=0.9,
        )
        heads = VGroup()
        for p in phones:
            h = label("Pinces", 15, ACCENT, bold=True)
            VGroup(h, p["read"]).arrange(DOWN, buff=0.18).move_to(p["scr"].get_top() + 0.85 * DOWN)
            heads.add(h)
        self.play(FadeIn(heads), *[FadeIn(p["read"]) for p in phones], FadeIn(offline), run_time=0.6)
        self.wait(0.6)

        # Chacun·e retire 3 pinces
        for k, p in enumerate(phones):
            if intent:
                act = label("retirer 3", 14, ACCENT, font=MONO_FONT, bold=True)
            else:
                act = label("15 − 3 = 12", 14, WARN, font=MONO_FONT, bold=True)
            act.next_to(p["read"], DOWN, buff=0.35)
            self.play(FadeIn(act, shift=0.1 * DOWN),
                      *[m.animate.set_opacity(0.12) for m in (reserve[12:15] if k == 0 else reserve[9:12])],
                      Transform(res_count, label(str(12 - 3 * k), 22, TXT, bold=True).move_to(res_count)),
                      run_time=0.7)
            p["act"] = act
        self.wait(0.5)

        # Le réseau revient : les deux files rejouent
        self.play(*[Transform(p["bars"], signal_bars(4, ACCENT).move_to(p["bars"])) for p in phones],
                  FadeOut(offline), run_time=0.5)
        values = (12, 9) if intent else (12, 12)
        for k, p in enumerate(phones):
            if intent:
                req = request_box('POST …/retraits { "quantite": 3 }', ACCENT)
            else:
                req = request_box('PATCH /materiels/{id} { "stock": 12 }', WARN)
            req.move_to(p["ph"].get_top() + 0.35 * DOWN)
            fit_x(req)
            self.play(FadeIn(req, scale=0.8), run_time=0.35)
            self.play(req.animate.move_to(srv.get_left() + 0.1 * LEFT).scale(0.6).set_opacity(0),
                      run_time=0.8)
            self.remove(req)
            new_val = label(str(values[k]), 40, TXT, bold=True).move_to(stock_box)
            self.play(Flash(srv.get_left(), color=ACCENT if intent else WARN, line_length=0.15,
                            flash_radius=0.25),
                      Transform(stock_val, new_val), run_time=0.5)
            if not intent and k == 1:
                self.play(Indicate(stock_val, color=WARN, scale_factor=1.25), run_time=0.6)
            self.wait(0.3)

        # Le verdict
        if intent:
            self.play(stock_val.animate.set_color(ACCENT), res_count.animate.set_color(ACCENT), run_time=0.4)
            eq = label("9  =  9", 26, ACCENT, bold=True).move_to([3.1, -2.2, 0])
            msg = label("« j'ai retiré 3 pinces » reste vrai cinq heures plus tard", 19, TXT, bold=True)
            msg.move_to([0, 2.15, 0])
            self.play(FadeIn(eq, scale=1.3), FadeIn(msg, shift=0.1 * DOWN), run_time=0.7)
        else:
            self.play(stock_val.animate.set_color(ERROR), res_count.animate.set_color(ACCENT), run_time=0.4)
            eq = label("12  ≠  9", 26, ERROR, bold=True).move_to([3.1, -2.2, 0])
            msg = VGroup(
                label("6 pinces sont sorties, le stock en annonce 12", 19, TXT, bold=True),
                label("une mise à jour perdue, et personne ne le sait", 17, ERROR),
            ).arrange(DOWN, buff=0.1).move_to([0, 2.2, 0])
            self.play(FadeIn(eq, scale=1.3), FadeIn(msg, shift=0.1 * DOWN), run_time=0.7)
        self.wait(3.2)
        self.clear_stage()

    # --- 2 bis. La règle -------------------------------------------------------------

    def regle(self):
        self.show_chip("Le client envoie une intention, jamais un état calculé", ACCENT)
        bad_src = 'PATCH /materiels/{id}\n{ "stock": 12 }\n# ← le client a calculé 15 − 3'
        good_src = 'POST /materiels/{id}/retraits\n{ "quantite": 3 }\n# ← le serveur calcule'
        panels = []
        for src, x, tag, color in ((bad_src, -3.55, "à ne pas faire", ERROR),
                                    (good_src, 3.55, "à faire", ACCENT)):
            panel = EditorPanel("ADR 0006 · annexe §4.4", [x, 0.85, 0], width=6.6, height=2.1,
                                tag=tag, tag_color=color)
            panel.box.set_stroke(color, 1.8)
            view = CodeView(src, ["bash"], gutter=False)
            panel.fit_code(view, max_scale=0.95)
            panels.append((panel, view))
        self.play(*[FadeIn(p.chrome) for p, _ in panels], run_time=0.6)
        for p, v in panels:
            self.play(FadeIn(v.group, shift=0.1 * RIGHT), run_time=0.6)
        (_, bad), (_, good) = panels
        self.play(flash([bad.token_box(2, '"stock": 12')], ERROR, 0.8),
                  flash([good.token_box(2, '"quantite": 3')], ACCENT, 0.8))
        marks = VGroup(
            highlight_rect(bad.token_box(2, '"stock": 12'), ERROR),
            highlight_rect(good.token_box(2, '"quantite": 3'), ACCENT),
        )
        self.play(FadeIn(marks), run_time=0.4)

        test = VGroup(
            label("le test de l'ADR 0007 :", 17, DIM),
            label("si le serveur doit faire confiance à l'arithmétique du client,", 20, TXT, bold=True),
            label("l'opération est mal conçue", 20, TXT, bold=True),
        ).arrange(DOWN, buff=0.12).move_to([0, -1.75, 0])
        self.play(FadeIn(test, shift=0.1 * UP), run_time=0.7)
        self.wait(3.4)
        self.clear_stage()

    # --- 3. Le 409 cinq heures après ------------------------------------------------

    def conflit(self):
        self.show_chip("Le refus qui arrive cinq heures après", WARN)

        # La sortie : 12 places, 11 prises
        seats = VGroup(*[
            Square(side_length=0.26).set_fill(DIM if i < 11 else BG, 1).set_stroke(PANEL_STROKE, 1.2)
            for i in range(12)
        ]).arrange(RIGHT, buff=0.08)
        s_title = label("Sortie Sugiton · samedi", 17, ACCENT, bold=True)
        s_left = label("1 place restante", 15, TXT)
        sortie = VGroup(s_title, seats, s_left).arrange(DOWN, buff=0.18)
        s_box = SurroundingRectangle(sortie, buff=0.25).set_fill(PANEL_BG, 1).set_stroke(VIOLET, 1.5)
        s_group = VGroup(s_box, sortie).move_to([0, 1.45, 0])
        srv_tag = label("arbitrée par server/", 13, VIOLET).next_to(s_box, DOWN, buff=0.1)

        ph_a, bars_a, tag_a = small_phone([-4.9, -0.75, 0], "A", 0)
        ph_b, bars_b, tag_b = small_phone([4.9, -0.75, 0], "B", 4)
        no_net = label("hors réseau", 13, ERROR, bold=True).next_to(tag_a, UP, buff=0.08)

        self.play(FadeIn(s_group), FadeIn(srv_tag), run_time=0.6)
        self.play(FadeIn(VGroup(ph_a, bars_a, tag_a, no_net)), FadeIn(VGroup(ph_b, bars_b, tag_b)),
                  run_time=0.6)

        # La frise
        y = -2.75
        axis = Line([-2.8, y, 0], [2.8, y, 0]).set_stroke(PANEL_STROKE, 2)
        hours = {9: -2.2, 11: 0.0, 14: 2.2}
        ticks = VGroup(*[
            VGroup(Dot([x, y, 0], radius=0.05).set_fill(DIM, 1),
                   label(f"{h}h", 14, DIM).move_to([x, y - 0.28, 0]))
            for h, x in hours.items()
        ])
        cursor = Triangle().scale(0.09).rotate(PI).set_fill(TXT, 1).set_stroke(width=0)
        cursor.move_to([hours[9], y + 0.18, 0])
        self.play(ShowCreation(axis), FadeIn(ticks), FadeIn(cursor), run_time=0.6)

        # 9h : A s'inscrit, hors ligne
        btn_a = pill("S'inscrire", ACCENT, 13, fill=0.25).move_to(ph_a[1].get_center() + 0.3 * UP)
        btn_b = pill("S'inscrire", ACCENT, 13, fill=0.25).move_to(ph_b[1].get_center() + 0.3 * UP)
        self.play(FadeIn(btn_a), FadeIn(btn_b), run_time=0.4)
        wait_a = pill("en attente d'envoi", WARN, 13).move_to(btn_a)
        self.play(Indicate(btn_a, color=ACCENT), run_time=0.4)
        self.play(FadeTransform(btn_a, wait_a), run_time=0.5)
        self.wait(0.5)

        # 11h : B s'inscrit, en ligne → 201, la dernière place est prise
        self.play(cursor.animate.move_to([hours[11], y + 0.18, 0]), run_time=0.6)
        self.play(Indicate(btn_b, color=ACCENT), run_time=0.4)
        dot = packet(ACCENT).move_to(ph_b.get_left())
        self.add(dot)
        self.play(dot.animate.move_to(s_box.get_right()), run_time=0.6, rate_func=linear)
        self.remove(dot)
        ok_b = pill("201 · inscrit·e", ACCENT, 13).move_to(btn_b)
        self.play(seats[11].animate.set_fill(GOLD, 1),
                  Transform(s_left, label("0 place restante", 15, ERROR).move_to(s_left)),
                  FadeTransform(btn_b, ok_b), run_time=0.6)
        self.wait(0.5)

        # 14h : A retrouve le réseau, la file rejoue → 409
        self.play(cursor.animate.move_to([hours[14], y + 0.18, 0]), run_time=0.6)
        self.play(Transform(bars_a, signal_bars(4, ACCENT).move_to(bars_a)), FadeOut(no_net), run_time=0.4)
        dot = packet(WARN).move_to(ph_a.get_right())
        self.add(dot)
        self.play(dot.animate.move_to(s_box.get_left()), run_time=0.6, rate_func=linear)
        self.remove(dot)
        back = packet(ERROR).move_to(s_box.get_left())
        self.add(back)
        self.play(back.animate.move_to(ph_a.get_right()), run_time=0.6, rate_func=linear)
        self.remove(back)
        ko_a = pill("refusée · 409", ERROR, 13).move_to(wait_a)
        self.play(FadeTransform(wait_a, ko_a), run_time=0.5)
        note = label("saisie à 9h, refusée à 14h", 14, ERROR).next_to(ph_a, DOWN, buff=0.15)
        self.play(FadeIn(note), run_time=0.4)
        self.wait(1.6)

        # Les quatre ressources arbitrées par le serveur
        self.play(FadeOut(VGroup(s_group, srv_tag, ph_a, bars_a, tag_a, ph_b, bars_b, tag_b, ok_b,
                                 ko_a, note, axis, ticks, cursor)), run_time=0.6)
        rows = [
            ("inscriptions à une sortie", "places limitées"),
            ("retraits de matériel", "stock partagé"),
            ("utilisation d'une dotation", "usage unique"),
            ("réponses à un sondage", "une réponse par personne"),
        ]
        table = VGroup()
        for left, right in rows:
            l = label(left, 19, TXT, bold=True)
            arrow = label("→", 19, DIM)
            r = label(right, 18, DIM)
            table.add(VGroup(l, arrow, r))
        lw = max(r[0].get_width() for r in table)
        for r in table:
            r[1].next_to(r[0], RIGHT, buff=0.3)
            r[1].set_x(r[0].get_left()[0] + lw + 0.45)
            r[2].next_to(r[1], RIGHT, buff=0.3)
        table.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        for r in table:
            r[1].set_x(table.get_left()[0] + lw + 0.45)
            r[2].next_to(r[1], RIGHT, buff=0.3)
        table.move_to([0, 0.75, 0])
        t_title = label("quatre ressources que le serveur arbitre : il peut répondre 409", 19, WARN, bold=True)
        t_title.next_to(table, UP, buff=0.4)
        t_bg = SurroundingRectangle(VGroup(table), buff=0.3).set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.2)
        self.play(FadeIn(t_title), FadeIn(t_bg), LaggedStartMap(FadeIn, table, shift=0.1 * RIGHT, lag_ratio=0.2),
                  run_time=1.2)
        self.wait(2.0)
        q_box = RoundedRectangle(width=9.6, height=0.9, corner_radius=0.14)
        q_box.set_fill(GOLD, 0.06).set_stroke(GOLD, 1.2)
        q_box.move_to([0, -1.95, 0])
        q = VGroup(
            label("question ouverte (ADR 0006 §9)", 14, GOLD, bold=True),
            label("une inscription refusée en 409 : liste d'attente, ou simple signalement ?", 17, TXT),
        ).arrange(DOWN, buff=0.1).move_to(q_box)
        self.play(FadeIn(q_box), FadeIn(q), run_time=0.6)
        self.wait(3.0)
        self.clear_stage()

    # --- 4. Encart : les actions nommées -------------------------------------------------

    def actions_nommees(self):
        self.show_chip("Encart : les actions nommées", VIOLET)
        src = (
            "POST /<ressource>/{id}/<nom-de-l-action>\n"
            "\n"
            "POST /ramassages/{id}/annulation      operationId: annulerRamassage\n"
            "POST /bilans/{id}/validation          operationId: validerBilan\n"
            "POST /materiels/{id}/retraits         operationId: retirerMateriel\n"
            "POST /dotations/{id}/utilisation      operationId: utiliserDotation"
        )
        panel = EditorPanel("docs/vocabulaire.md", [0, 1.0, 0], width=13.0, height=2.75,
                            tag="ADR 0007 · décidé, pas codé", tag_color=VIOLET)
        view = CodeView(src, ["bash"], gutter=False)
        panel.fit_code(view, max_scale=0.9)
        self.play(FadeIn(panel.chrome), run_time=0.5)
        self.play(FadeIn(view.group, shift=0.1 * RIGHT), run_time=0.7)

        nouns = [(3, "annulation"), (4, "validation"), (5, "retraits"), (6, "utilisation")]
        boxes = [view.token_box(l, t) for l, t in nouns]
        self.play(flash(boxes, VIOLET, 0.35))
        marks = VGroup(*[highlight_rect(b, VIOLET) for b in boxes])
        self.play(FadeIn(marks), run_time=0.4)
        why = label("un nom, pas un verbe : l'action a un auteur, une date, un motif, et on voudra la relire",
                    17, TXT).move_to([0, -0.85, 0])
        fit_w(why, 12.6)
        self.play(FadeIn(why, shift=0.1 * UP), run_time=0.6)
        self.wait(2.0)

        bad = label("/ramassages/{id}:annuler", 20, DIM, font=MONO_FONT)
        strike = Line(bad.get_left(), bad.get_right()).set_stroke(ERROR, 3)
        reason = label("écarté : le « : » entre en collision avec la syntaxe :id des routes AdonisJS",
                       16, DIM)
        bad_group = VGroup(VGroup(bad, strike), reason).arrange(DOWN, buff=0.16).move_to([0, -2.0, 0])
        self.play(FadeIn(bad), run_time=0.4)
        self.play(ShowCreation(strike), FadeIn(reason), run_time=0.6)
        self.wait(1.6)

        nxt = label("épisode suivant : l'identifiant fourni par le téléphone (UUIDv7)  →", 16, DIM)
        nxt.move_to([0, -3.15, 0])
        self.play(FadeIn(nxt), run_time=0.5)
        self.wait(2.5)
