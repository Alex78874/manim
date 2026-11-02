"""
Épisode 28 — occurredAt contre createdAt, et la borne serveur

Bloc E : les règles hors ligne non négociables.
  1. Deux dates pour une seule saisie : un bilan saisi à 14h dans Sugiton
     (occurredAt, donné par le téléphone), enregistré à 19h (createdAt, posé
     par le serveur). Les statistiques comptent l'heure de l'action.
  2. La borne : de −30 jours à +60 secondes autour de « maintenant ». Les sept
     cas des tests unitaires (horodatage.spec.ts) se posent sur l'axe.
  3. Le code : bornerOccurredAt(), ses deux bornes, et `maintenant` injectable.
  4. Qui l'appelle ? Seulement le service généré par `npm run feature` :
     aucune route actuelle (session, utilisateurs) ne l'utilise.

Statut affiché : documenté + dans le gabarit + codé (la fonction et ses
7 tests unitaires). Elle n'est appelée que par le service que génère le gabarit.

Sources : server/app/services/horodatage.ts, server/tests/unit/horodatage.spec.ts,
docs/adr/0006 (annexe §4.3), CLAUDE.md:59-61, scripts/feature.mjs:166-172,
277-282, 298, 352.

Rendu vidéo :  manimgl ep28_occurred_at.py Ep28OccurredAt -w
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


PHONE_C = GOLD       # ce qui vient du téléphone
SERVER_C = VIOLET    # ce que pose le serveur


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep28OccurredAt(EpisodeScene):
    EPISODE = "28"
    TITLE = "occurredAt contre createdAt"

    def construct(self):
        self.set_banner({"documenté", "dans le gabarit npm run feature", "codé"},
                        "bornerOccurredAt : appelée seulement par le service généré")
        self.deux_dates()
        self.borne()
        self.code()
        self.qui_appelle()

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

    # --- 1. Deux dates pour une seule saisie -------------------------------------------

    def deux_dates(self):
        self.show_chip("Deux dates pour une seule saisie", ACCENT)

        x0, x1, y = -5.6, 5.6, -0.2
        hours = list(range(12, 21))
        step = (x1 - x0) / (len(hours) - 1)

        def hx(h):
            return x0 + (h - 12) * step

        axis = Line([x0 - 0.3, y, 0], [x1 + 0.3, y, 0]).set_stroke(PANEL_STROKE, 2)
        ticks = VGroup(*[
            VGroup(Line([hx(h), y - 0.07, 0], [hx(h), y + 0.07, 0]).set_stroke(DIM, 1.5),
                   label(f"{h}h", 14, DIM).move_to([hx(h), y - 0.32, 0]))
            for h in hours
        ])
        day = label("10/03/2027", 14, DIM).next_to(axis, LEFT, buff=0.1).shift(0.32 * DOWN)
        fit_x(day)
        self.play(ShowCreation(axis), FadeIn(ticks), run_time=0.8)

        # 14h : la saisie sur le téléphone, sans réseau
        ph = phone(width=1.0, height=1.9).move_to([hx(14), 1.55, 0])
        bars = signal_bars(0, ERROR).scale(0.8).move_to(ph[1].get_corner(UR) + np.array([-0.18, -0.12, 0]))
        txt = VGroup(label("Bilan", 13, ACCENT, bold=True), label("Sugiton", 13, ACCENT, bold=True),
                     label("12 kg", 13, TXT)).arrange(DOWN, buff=0.08).move_to(ph[1])
        occ = VGroup(
            Line([hx(14), y, 0], [hx(14), 0.5, 0]).set_stroke(PHONE_C, 2),
            Dot([hx(14), y, 0], radius=0.08).set_fill(PHONE_C, 1),
        )
        occ_lbl = VGroup(label("occurredAt", 18, PHONE_C, font=MONO_FONT, bold=True),
                         label("donnée par le téléphone", 14, DIM),
                         label("quand l'action a eu lieu", 14, DIM)).arrange(DOWN, buff=0.06)
        occ_lbl.next_to([hx(14), y, 0], DOWN, buff=0.65)
        self.play(FadeIn(ph, shift=0.2 * DOWN), FadeIn(bars), FadeIn(txt), run_time=0.6)
        self.play(ShowCreation(occ[0]), FadeIn(occ[1], scale=2), FadeIn(occ_lbl), run_time=0.7)
        self.wait(1.4)

        # 19h : le réseau revient, le serveur enregistre
        srv = node("server/", None, SERVER_C, width=1.7, title_size=18).move_to([hx(19), 1.3, 0])
        cre = VGroup(
            Line([hx(19), y, 0], [hx(19), srv.get_bottom()[1] - 0.05, 0]).set_stroke(SERVER_C, 2),
            Dot([hx(19), y, 0], radius=0.08).set_fill(SERVER_C, 1),
        )
        cre_lbl = VGroup(label("createdAt", 18, SERVER_C, font=MONO_FONT, bold=True),
                         label("posé par le serveur", 14, DIM),
                         label("quand il l'a enregistrée", 14, DIM)).arrange(DOWN, buff=0.06)
        cre_lbl.next_to([hx(19), y, 0], DOWN, buff=0.65)
        span = DashedLine([hx(14), y + 0.35, 0], [hx(19), y + 0.35, 0], dash_length=0.08).set_stroke(DIM, 1.5)
        span_lbl = label("5 heures de file d'attente", 14, DIM).next_to(span, UP, buff=0.08)
        self.play(ShowCreation(span), FadeIn(span_lbl), run_time=0.7)
        self.play(FadeIn(srv), ShowCreation(cre[0]), FadeIn(cre[1], scale=2), FadeIn(cre_lbl), run_time=0.8)
        self.wait(1.0)

        # Les statistiques comptent laquelle ?
        verdict = VGroup(
            VGroup(label("✔", 20, ACCENT, bold=True),
                   label("les statistiques comptent 14h : l'heure de l'action", 18, TXT, bold=True)),
            VGroup(label("✖", 20, ERROR, bold=True),
                   label("horodater à l'arrivée (19h) fausserait les statistiques de l'association", 16, DIM)),
        )
        for v in verdict:
            v.arrange(RIGHT, buff=0.2)
        verdict.arrange(DOWN, aligned_edge=LEFT, buff=0.15).move_to([0, -2.85, 0])
        self.play(Indicate(occ_lbl[0], color=ACCENT, scale_factor=1.15), FadeIn(verdict[0]), run_time=0.8)
        self.play(FadeIn(verdict[1]), run_time=0.5)
        self.wait(3.2)
        self.clear_stage()

    # --- 2. La borne -----------------------------------------------------------------

    def borne(self):
        self.show_chip("Le serveur borne occurredAt", WARN)
        now_s = label("maintenant = 2027-03-10T12:00:00Z", 15, DIM, font=MONO_FONT).move_to([0, 2.4, 0])
        y = 0.25
        xa, xn, xb = -4.6, 3.6, 4.7          # −30 j, maintenant, +60 s (pas à l'échelle)
        line = Line([-6.6, y, 0], [6.6, y, 0]).set_stroke(PANEL_STROKE, 2)
        ok_zone = Rectangle(width=xb - xa, height=0.36).move_to([(xa + xb) / 2, y, 0])
        ok_zone.set_fill(ACCENT, 0.18).set_stroke(ACCENT, 1.5)
        marks = VGroup()
        for x, t, c in ((xa, "−30 jours", ACCENT), (xn, "maintenant", TXT), (xb, "+60 s", ACCENT)):
            marks.add(VGroup(
                Line([x, y - 0.3, 0], [x, y + 0.3, 0]).set_stroke(c, 2),
                label(t, 15, c, bold=True).move_to([x, y - 0.55, 0]),
            ))
        z_l = Rectangle(width=xa + 6.6, height=0.36).move_to([(xa - 6.6) / 2, y, 0])
        z_r = Rectangle(width=6.6 - xb, height=0.36).move_to([(xb + 6.6) / 2, y, 0])
        for z in (z_l, z_r):
            z.set_fill(ERROR, 0.12).set_stroke(width=0)
        out_l = VGroup(z_l, label("HORS_BORNES", 14, ERROR, bold=True).move_to([-5.75, y - 0.55, 0]))
        out_r = VGroup(z_r, label("HORS_BORNES", 14, ERROR, bold=True).move_to([5.7, y - 0.55, 0]))
        scale_note = label("axe non proportionnel", 13, DIM).move_to([0, y - 0.95, 0])
        self.play(FadeIn(now_s), ShowCreation(line), run_time=0.6)
        self.play(FadeIn(ok_zone), FadeIn(marks), FadeIn(scale_note), run_time=0.7)
        self.play(FadeIn(out_l), FadeIn(out_r), run_time=0.4)
        self.wait(0.6)

        # Les cas des tests unitaires
        cases = [
            (xn - 1.3, "−5 h", ACCENT, "accepté"),
            (xb - 0.12, "+59 s", ACCENT, "accepté"),
            (xa + 0.18, "−30 j + 1 min", ACCENT, "accepté"),
            (5.75, "+1 h", ERROR, "refusé"),
            (-5.7, "−31 j", ERROR, "refusé"),
        ]
        dots = VGroup()
        tags = VGroup()
        for i, (x, t, c, _) in enumerate(cases):
            d = Dot([x, y, 0], radius=0.09).set_fill(c, 1).set_stroke(BG, 2)
            up = i % 2 == 0
            tg = label(t, 14, c, font=MONO_FONT, bold=True)
            tg.move_to([x, y + (0.6 if up else 1.0), 0])
            fit_x(tg)
            dots.add(d)
            tags.add(tg)
        for d, tg, (_, _, c, _) in zip(dots, tags, cases):
            self.play(FadeIn(d, shift=0.6 * DOWN), FadeIn(tg), run_time=0.45)
            if c == ERROR:
                self.play(Indicate(d, color=ERROR, scale_factor=1.6), run_time=0.35)
        self.wait(0.6)

        # « hier » n'est même pas une date
        hier = VGroup(
            label("'hier'", 18, TXT, font=MONO_FONT, bold=True),
            label("→", 18, DIM),
            pill("400 · OCCURRED_AT_ILLISIBLE", ERROR, 14, font=MONO_FONT),
        ).arrange(RIGHT, buff=0.25)
        bornes = VGroup(
            label("hors de la zone", 18, TXT, bold=True),
            label("→", 18, DIM),
            pill("400 · OCCURRED_AT_HORS_BORNES", ERROR, 14, font=MONO_FONT),
        ).arrange(RIGHT, buff=0.25)
        res = VGroup(bornes, hier).arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to([0, -1.75, 0])
        self.play(FadeIn(res[0], shift=0.1 * UP), run_time=0.5)
        self.play(FadeIn(res[1], shift=0.1 * UP), run_time=0.5)
        src = label("cas tirés des 7 tests de server/tests/unit/horodatage.spec.ts", 14, DIM).move_to([0, -2.85, 0])
        self.play(FadeIn(src), run_time=0.4)
        self.wait(3.4)
        self.clear_stage()

    # --- 3. Le code -------------------------------------------------------------------

    def code(self):
        self.show_chip("bornerOccurredAt()", ACCENT)
        src = (
            "export function bornerOccurredAt(\n"
            "  occurredAt: string,\n"
            "  maintenant: DateTime = DateTime.utc()\n"
            "): DateTime<true> {\n"
            "  const date = DateTime.fromISO(occurredAt, { zone: 'utc' })\n"
            "\n"
            "  if (!date.isValid) throw new HorodatageIllisible()\n"
            "\n"
            "  if (date > maintenant.plus({ seconds: AVANCE_TOLEREE_EN_SECONDES })) {\n"
            "    throw new HorodatageHorsBornes()\n"
            "  }\n"
            "\n"
            "  if (date < maintenant.minus({ days: ANCIENNETE_MAXIMALE_EN_JOURS })) {\n"
            "    throw new HorodatageHorsBornes()\n"
            "  }\n"
            "\n"
            "  return date\n"
            "}"
        )
        panel = EditorPanel("server/app/services/horodatage.ts", [-2.35, -0.35, 0], width=9.0, height=5.3,
                            tag="lignes 63 à 86, raccourci", tag_color=DIM)
        view = CodeView(src, ["typescript"])
        panel.fit_code(view, max_scale=0.75)
        self.play(FadeIn(panel.chrome), run_time=0.4)
        self.play(FadeIn(view.group, shift=0.1 * RIGHT), run_time=0.8)

        # Les constantes, à droite
        consts = VGroup(
            VGroup(label("AVANCE_TOLEREE_EN_SECONDES", 14, TXT, font=MONO_FONT), label("= 60", 20, ACCENT, bold=True)),
            VGroup(label("ANCIENNETE_MAXIMALE_EN_JOURS", 14, TXT, font=MONO_FONT), label("= 30", 20, ACCENT, bold=True)),
        )
        for c in consts:
            c.arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        consts.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        why = VGroup(
            label("60 s : une horloge un peu en avance", 14, DIM),
            label("n'est pas une faute du référent", 14, DIM),
            label("30 j : comme la table d'idempotence", 14, DIM),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        right = VGroup(consts, why).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([4.75, 0.9, 0])
        fit_x(right, 0.25)
        self.play(FadeIn(right, shift=0.1 * LEFT), run_time=0.6)

        # Les deux bornes s'allument
        self.play(flash([view.line_box(9), view.line_box(10)], WARN, 0.4))
        h1 = highlight_rect(view.line_box(9), WARN)
        self.play(FadeIn(h1), Indicate(consts[0], color=WARN, scale_factor=1.05), run_time=0.6)
        self.wait(0.6)
        self.play(flash([view.line_box(13), view.line_box(14)], WARN, 0.4))
        h2 = highlight_rect(view.line_box(13), WARN)
        self.play(FadeIn(h2), Indicate(consts[1], color=WARN, scale_factor=1.05), run_time=0.6)
        self.wait(0.8)

        # `maintenant` est injectable
        self.play(flash([view.token_box(3, "maintenant: DateTime = DateTime.utc()")], ACCENT, 0.8))
        h3 = highlight_rect(view.token_box(3, "maintenant: DateTime = DateTime.utc()"), ACCENT)
        inj = VGroup(
            label("maintenant : un paramètre", 16, ACCENT, bold=True),
            label("les tests n'ont pas à manipuler", 14, DIM),
            label("l'horloge du système", 14, DIM),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        inj.next_to(right, DOWN, buff=0.45, aligned_edge=LEFT)
        self.play(FadeIn(h3), FadeIn(inj, shift=0.1 * LEFT), run_time=0.6)
        self.wait(3.4)
        self.clear_stage()

    # --- 4. Qui l'appelle ? ------------------------------------------------------------

    def qui_appelle(self):
        self.show_chip("Qui l'appelle aujourd'hui ?", GOLD)
        fn = node("horodatage.ts", "codé · 7 tests unitaires", ACCENT, width=3.3).move_to([0, 1.35, 0])
        gen = node("<nom>_service.ts", "généré par npm run feature", GOLD, width=3.6, planned=True,
                   title_size=19).move_to([-3.6, -0.6, 0])
        cur = node("session · utilisateurs", "les routes actuelles", DIM, width=3.6,
                   title_size=19).move_to([3.6, -0.6, 0])
        a_gen = link(edge_point(gen, UP), edge_point(fn, DL), GOLD)
        a_cur = link(edge_point(cur, UP), edge_point(fn, DR), DIM, planned=True)
        cross = label("✖", 26, ERROR, bold=True).move_to(a_cur.get_center())
        self.play(FadeIn(fn), run_time=0.5)
        self.play(FadeIn(gen), GrowArrow(a_gen), run_time=0.7)
        self.play(FadeIn(cur), ShowCreation(a_cur), run_time=0.7)
        self.play(FadeIn(cross, scale=1.5), run_time=0.4)
        no_call = label("aucune n'appelle bornerOccurredAt", 15, ERROR).next_to(cur, DOWN, buff=0.2)
        self.play(FadeIn(no_call), run_time=0.4)

        snippet = label("if (donnees.occurredAt) bornerOccurredAt(donnees.occurredAt)", 15, TXT, font=MONO_FONT)
        sn_bg = SurroundingRectangle(snippet, buff=0.16).set_fill(PANEL_BG, 1).set_stroke(GOLD, 1.2)
        sn = VGroup(sn_bg, snippet).next_to(gen, DOWN, buff=0.3)
        sn.set_x(-1.0)
        fit_x(sn)
        opt = label("dans le gabarit, occurredAt est facultatif : sans lui, aucune borne", 15, DIM)
        opt.next_to(sn, DOWN, buff=0.2)
        fit_x(opt)
        self.play(FadeIn(sn, shift=0.1 * UP), run_time=0.6)
        self.play(FadeIn(opt), run_time=0.4)
        self.wait(2.8)
        nxt = label("épisode suivant : rien n'est supprimé (suppression douce)  →", 16, DIM)
        nxt.to_corner(DR, buff=0.4).shift(0.45 * UP)
        self.play(FadeIn(nxt), run_time=0.5)
        self.wait(2.5)
