"""
Épisode 25 — Pourquoi le hors-ligne change le contrat

Bloc E : les règles hors ligne non négociables. On montre le PROBLÈME avant les
solutions (épisodes 26 à 29).
  1. Lire hors ligne est facile : la liste chargée à 13h52 reste affichée.
  2. Écrire est le vrai problème : « Bilan · Sugiton · 12 kg » reste en attente,
     et la file d'attente du téléphone le rejoue cinq heures plus tard.
  3. Quatre pannes possibles, chacune avec son épisode : état écrasé (26),
     identifiant inconnu (27), mauvaise date (28), suppression invisible (29).

Statut affiché : documenté (ADR 0006). L'application mobile n'existe pas encore.
La « file d'attente » est celle du TÉLÉPHONE (ADR 0006), pas une file de messages
côté serveur.

Sources : docs/adr/0006-file-d-attente-hors-ligne.md (contexte, conséquences,
annexe §1 à §4 et §6), CLAUDE.md (section « Non négociable »).

Rendu vidéo :  manimgl ep25_hors_ligne_contrat.py Ep25HorsLigneContrat -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


# ---------------------------------------------------------------------------
# Briques propres à cet épisode (bloc E)
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


def phone_ui(center, clock="13:52", bars=4):
    """Un téléphone avec sa barre d'état : heure à gauche, réseau à droite."""
    ph = phone().move_to(center)
    scr = ph[1]
    b = signal_bars(bars).move_to(scr.get_corner(UR) + np.array([-0.3, -0.16, 0]))
    t = label(clock, 13, TXT, font=MONO_FONT).move_to(scr.get_corner(UL) + np.array([0.33, -0.16, 0]))
    return ph, b, t


def fit_w(mob, w):
    if mob.get_width() > w:
        mob.set_width(w)
    return mob


def pill(text, color, size=13, fill=0.2):
    t = label(text, size, color, bold=True)
    bg = RoundedRectangle(width=t.get_width() + 0.3, height=t.get_height() + 0.16, corner_radius=0.13)
    bg.set_fill(color, fill).set_stroke(color, 1.4)
    t.move_to(bg)
    return VGroup(bg, t)


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep25HorsLigneContrat(EpisodeScene):
    EPISODE = "25"
    TITLE = "Pourquoi le hors-ligne change le contrat"

    def construct(self):
        self.lire()
        self.ecrire()
        self.pannes()

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

    # --- 1. Lire hors ligne : facile ------------------------------------------

    def lire(self):
        self.show_chip("Lire hors ligne : facile", ACCENT)
        self.set_banner({"documenté"}, "ADR 0006 · l'app mobile n'existe pas encore")

        ph, bars, clock = phone_ui([-3.6, -0.35, 0], "13:52", 4)
        scr = ph[1]
        head = label("Ramassages", 16, ACCENT, bold=True)
        items = VGroup()
        for lieu, quand in (("Sugiton", "sam. 9h"), ("Les Goudes", "dim. 10h"),
                            ("Morgiou", "15/03"), ("Sormiou", "22/03")):
            box = RoundedRectangle(width=1.5, height=0.4, corner_radius=0.07)
            box.set_fill(BG, 1).set_stroke(PANEL_STROKE, 1)
            t = VGroup(label(lieu, 13, TXT, bold=True), label(quand, 13, DIM)).arrange(RIGHT, buff=0.12)
            fit_w(t, 1.36).move_to(box)
            items.add(VGroup(box, t))
        items.arrange(DOWN, buff=0.1)
        stamp = label("chargée à 13h52", 13, DIM)
        screen_content = VGroup(head, items, stamp).arrange(DOWN, buff=0.18).move_to(scr).shift(0.05 * DOWN)

        self.play(FadeIn(ph, shift=0.2 * UP), FadeIn(bars), FadeIn(clock), run_time=0.7)
        self.play(FadeIn(head), LaggedStartMap(FadeIn, items, shift=0.1 * DOWN, lag_ratio=0.15),
                  FadeIn(stamp), run_time=1.0)
        self.wait(1.0)

        # Le réseau tombe… et la liste reste là
        for n in (3, 2, 1, 0):
            self.play(Transform(bars, signal_bars(n, WARN if n else ERROR).move_to(bars)), run_time=0.22)
        no_net = label("aucun réseau", 15, ERROR, bold=True).next_to(ph, UP, buff=0.15)
        self.play(FadeIn(no_net, scale=0.8), run_time=0.4)
        self.play(Indicate(items, color=ACCENT, scale_factor=1.04), run_time=0.8)

        check = label("✔", 40, ACCENT, bold=True)
        lines = VGroup(
            label("la liste reste affichée", 24, TXT, bold=True),
            label("une donnée périmée reste vraie", 19, DIM),
            label("à un instant passé", 19, DIM),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        right = VGroup(check, lines).arrange(RIGHT, buff=0.35).move_to([2.6, 0.3, 0])
        self.play(FadeIn(right, shift=0.15 * LEFT), run_time=0.7)
        src = label("ADR 0006 · annexe §1", 14, DIM).next_to(lines, DOWN, buff=0.35, aligned_edge=LEFT)
        self.play(FadeIn(src), run_time=0.3)
        self.wait(2.6)
        self.clear_stage()

    # --- 2. Écrire : le vrai problème --------------------------------------------

    def ecrire(self):
        self.show_chip("Écrire hors ligne : le vrai problème", ERROR)

        ph, bars, clock = phone_ui([-4.7, -0.45, 0], "14:00", 0)
        bars.become(signal_bars(0, ERROR).move_to(bars))
        scr = ph[1]
        title = label("Bilan · Sugiton", 16, ACCENT, bold=True)
        fields = VGroup()
        for name, value in (("participant·es", "5"), ("kg", "12")):
            box = RoundedRectangle(width=1.4, height=0.28, corner_radius=0.05)
            box.set_fill(BG, 1).set_stroke(PANEL_STROKE, 1)
            v = label(value, 14, TXT, font=MONO_FONT).move_to(box).align_to(box, LEFT).shift(0.1 * RIGHT)
            fields.add(VGroup(label(name, 13, DIM), VGroup(box, v)).arrange(DOWN, aligned_edge=LEFT, buff=0.05))
        fields.arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        button = RoundedRectangle(width=1.4, height=0.34, corner_radius=0.08).set_fill(ACCENT, 1).set_stroke(width=0)
        button_txt = label("Valider", 14, BG, bold=True).move_to(button)
        btn = VGroup(button, button_txt)
        form = VGroup(title, fields, btn).arrange(DOWN, buff=0.22).move_to(scr).shift(0.05 * DOWN)
        no_net = label("aucun réseau", 15, ERROR, bold=True).next_to(ph, UP, buff=0.15)

        self.play(FadeIn(ph, shift=0.2 * UP), FadeIn(bars), FadeIn(clock), FadeIn(no_net),
                  FadeIn(form), run_time=0.8)

        # La file d'attente du téléphone
        q_box = RoundedRectangle(width=3.5, height=1.5, corner_radius=0.14)
        q_box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5).move_to([-0.75, -0.45, 0])
        q_title = label("file d'attente du téléphone", 15, DIM).move_to(q_box.get_top() + 0.25 * DOWN)
        q_sep = Line(q_box.get_corner(UL) + 0.5 * DOWN, q_box.get_corner(UR) + 0.5 * DOWN)
        q_sep.set_stroke(PANEL_STROKE, 1)
        row_bg = RoundedRectangle(width=3.1, height=0.48, corner_radius=0.08)
        row_bg.set_fill(WARN, 0.12).set_stroke(WARN, 1.2)
        row_txt = label("Bilan Sugiton · 12 kg", 15, TXT, font=MONO_FONT)
        fit_w(row_txt, 2.8).move_to(row_bg)
        row = VGroup(row_bg, row_txt).move_to(q_box.get_center() + 0.22 * DOWN)
        self.play(FadeIn(q_box), FadeIn(q_title), ShowCreation(q_sep), run_time=0.6)

        # Valider : l'écran répond tout de suite… mais rien n'est parti
        self.play(Indicate(btn, color=ACCENT, scale_factor=1.12), run_time=0.5)
        badge = pill("en attente d'envoi", WARN, 13).move_to(btn)
        to_q = Arrow(ph.get_right() + 0.4 * DOWN, q_box.get_left() + 0.22 * DOWN, buff=0.12).set_color(WARN)
        self.play(FadeTransform(btn, badge), GrowArrow(to_q), FadeIn(row, shift=0.15 * RIGHT), run_time=0.8)
        self.play(badge.animate.set_opacity(0.45), rate_func=there_and_back, run_time=0.7)
        self.wait(0.8)

        # Cinq heures passent
        big_anchor = np.array([-0.75, 1.65, 0])
        big, tick = counter(lambda a: f"{14 + int(round(5 * a)):02d}:00", big_anchor, size=44, color=TXT)
        later = label("cinq heures plus tard", 17, DIM).next_to(big_anchor, DOWN, buff=0.45)
        self.add(big)
        self.play(tick, FadeIn(later), Transform(clock, label("19:00", 13, TXT, font=MONO_FONT).move_to(clock)),
                  run_time=1.6)
        self.wait(0.8)

        # Le réseau revient : la file rejoue la saisie
        for n in (1, 2, 3, 4):
            self.play(Transform(bars, signal_bars(n, WARN if n < 4 else ACCENT).move_to(bars)), run_time=0.18)
        self.play(FadeOut(no_net), run_time=0.3)

        srv = node("server/", "AdonisJS", VIOLET, width=2.4).move_to([4.5, -0.45, 0])
        to_srv = Arrow(q_box.get_right(), srv.get_left(), buff=0.15).set_color(DIM)
        self.play(FadeIn(srv), GrowArrow(to_srv), run_time=0.6)
        dot = packet(WARN).move_to(q_box.get_right())
        self.add(dot)
        self.play(dot.animate.move_to(srv.get_left()), run_time=0.7, rate_func=linear)
        self.remove(dot)
        self.play(Flash(srv.get_left(), color=WARN, line_length=0.15, flash_radius=0.25), run_time=0.3)

        verdict = VGroup(
            pill("201 · accepté", ACCENT, 15),
            label("ou", 15, DIM),
            pill("4xx · refusé", ERROR, 15),
        ).arrange(DOWN, buff=0.14).next_to(srv, DOWN, buff=0.35)
        self.play(FadeIn(verdict, shift=0.1 * DOWN), run_time=0.6)

        promise = VGroup(
            label("une saisie acceptée sur le téléphone est une promesse", 20, TXT, bold=True),
            label("que le serveur peut encore refuser, des heures après", 20, TXT, bold=True),
        ).arrange(DOWN, buff=0.1).move_to([0, -2.85, 0])
        self.play(FadeIn(promise, shift=0.1 * UP), run_time=0.7)
        self.wait(3.0)
        self.clear_stage()

    # --- 3. Les quatre pannes -------------------------------------------------------

    def pannes(self):
        self.show_chip("Quatre pannes, quatre règles", WARN)

        data = [
            ("26", "état écrasé", ["deux PATCH {stock:12}", "→ 12 au lieu de 9"]),
            ("27", "id inconnu", ["participant → bilan ???", "pas encore d'id serveur"]),
            ("28", "mauvaise date", ["saisi à 14h", "compté à 19h"]),
            ("29", "suppression invisible", ["la ligne disparaît", "le téléphone la garde"]),
        ]
        cards = VGroup()
        for ep, title, lines in data:
            box = RoundedRectangle(width=3.05, height=2.4, corner_radius=0.15)
            box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
            cross = label("✖", 26, ERROR, bold=True)
            t = label(title, 20, ERROR, bold=True)
            fit_w(t, 2.7)
            body = VGroup(*[label(s, 14, TXT, font=MONO_FONT) for s in lines]).arrange(DOWN, buff=0.1)
            fit_w(body, 2.7)
            ep_badge = pill(f"épisode {ep}", ACCENT, 13, fill=0.12)
            content = VGroup(cross, t, body, ep_badge).arrange(DOWN, buff=0.2).move_to(box)
            cards.add(VGroup(box, content))
        cards.arrange(RIGHT, buff=0.25).move_to([0, 0.75, 0])

        for card in cards:
            self.play(FadeIn(card, shift=0.15 * UP), run_time=0.55)
            self.wait(1.3)

        rule = VGroup(
            label("ces règles vivent dans le CONTRAT, pas seulement dans l'application", 20, TXT, bold=True),
            label("une fois les applications installées, on ne peut plus les ajouter", 17, DIM),
        ).arrange(DOWN, buff=0.14).move_to([0, -1.55, 0])
        src = label("ADR 0006 · Conséquences", 14, DIM).next_to(rule, DOWN, buff=0.2)
        self.play(FadeIn(rule, shift=0.1 * UP), FadeIn(src), run_time=0.8)
        self.wait(2.0)

        next_ep = label("épisode suivant : intention relative contre état calculé  →", 16, DIM)
        next_ep.move_to([0, -3.15, 0])
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(3.0)
