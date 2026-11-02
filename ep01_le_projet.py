"""
Épisode 1 — Le projet : le métier, la contrainte et l'échelle

Série d'onboarding cmc-archi. Ce premier épisode pose le décor :
  1. Le client : l'association, ses brigades, ses référent·es.
  2. Le métier : un ramassage produit un bilan ; les chiffres de la communauté.
  3. Aujourd'hui / demain : tableurs et WhatsApp → app mobile + back-office web.
  4. Contrainte n°1 : pas de réseau dans les calanques (critère de recette).
  5. Contrainte n°2 : 6 devs deviennent 30 pendant la semaine intensive.
  6. Les engagements de qualité.

Sources : docs/contexte-projet.md, docs/vocabulaire.md, CLAUDE.md.

Rendu vidéo :  manimgl ep01_le_projet.py Ep01LeProjet -w
Aperçu      :  manimgl ep01_le_projet.py Ep01LeProjet
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

def spreadsheet(cols=4, rows=5, cell=0.22):
    grid = VGroup()
    for r in range(rows):
        for c in range(cols):
            sq = Rectangle(width=cell * 1.6, height=cell)
            fill = "#2C6E49" if r == 0 else PANEL_BG
            sq.set_fill(fill, 1).set_stroke(PANEL_STROKE, 1)
            sq.move_to([c * cell * 1.6, -r * cell, 0])
            grid.add(sq)
    return grid


def chat_bubble(text, color="#25D366", right=False):
    t = label(text, 15, TXT, font=MONO_FONT)
    bg = RoundedRectangle(width=t.get_width() + 0.3, height=t.get_height() + 0.22, corner_radius=0.1)
    bg.set_fill(color, 0.18).set_stroke(color, 1)
    t.move_to(bg)
    return VGroup(bg, t)


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep01LeProjet(EpisodeScene):
    EPISODE = "01"
    TITLE = "Le projet"

    def construct(self):
        self.client()
        self.metier()
        self.aujourdhui()
        self.contrainte_reseau()
        self.contrainte_echelle()
        self.engagements()

    # --- 1. Le client -------------------------------------------------------

    def client(self):
        self.show_chip("Le client", ACCENT)

        asso = RoundedRectangle(width=3.6, height=0.8, corner_radius=0.15)
        asso.set_fill(ACCENT, 0.15).set_stroke(ACCENT, 2)
        asso_txt = label("Clean My Calanques", 26, TXT, bold=True).move_to(asso)
        asso_sub = label("association · Marseille", 16, DIM).next_to(asso, DOWN, buff=0.12)
        asso_group = VGroup(asso, asso_txt, asso_sub).move_to([0, 1.75, 0])
        self.play(FadeIn(asso_group, shift=0.2 * DOWN))

        # Des bénévoles éparpillé·es, qui se regroupent en trois brigades
        centers = [np.array([-4.2, -0.5, 0]), np.array([0, -0.75, 0]), np.array([4.2, -0.5, 0])]
        names = ["Le Panier", "La Belle de Mai", "Les Goudes"]
        rng = np.random.default_rng(3)
        scattered, brigades, referents = VGroup(), [], []
        for k, c in enumerate(centers):
            members = VGroup()
            for i in range(6):
                p = person(TXT, 0.9)
                p.move_to(c + np.array([rng.uniform(-2.2, 2.2), rng.uniform(-1.4, 1.0), 0]))
                members.add(p)
            scattered.add(members)
            brigades.append((members, c))

        self.play(LaggedStartMap(FadeIn, VGroup(*[p for g in scattered for p in g]),
                                 scale=0.5, lag_ratio=0.04), run_time=1.4)

        ring_anims, move_anims, rings, tags = [], [], VGroup(), VGroup()
        for (members, c), name in zip(brigades, names):
            angles = np.linspace(0, TAU, len(members), endpoint=False) + PI / 2
            for p, a in zip(members, angles):
                move_anims.append(p.animate.move_to(c + 0.62 * np.array([np.cos(a), np.sin(a), 0])))
            ring = Circle(radius=1.0).move_to(c).set_stroke(ACCENT, 1.5, opacity=0.7)
            ring.set_fill(ACCENT, 0.06)
            tag = label(name, 17, ACCENT).next_to(ring, DOWN, buff=0.12)
            rings.add(ring)
            tags.add(tag)
        self.play(*move_anims, run_time=1.4)
        self.play(*[ShowCreation(r) for r in rings], *[FadeIn(t) for t in tags], run_time=0.8)

        # Une personne par brigade devient référent·e
        star_anims, links = [], VGroup()
        for members, c in brigades:
            old = members[0]
            ref = star_person(0.9).move_to(c)
            referents.append(ref)
            star_anims.append(FadeTransform(old.copy(), ref))
            star_anims.append(FadeOut(old))
            link = DashedLine(c + 0.25 * UP, asso_sub.get_bottom() + 0.08 * DOWN, dash_length=0.08)
            link.set_stroke(GOLD, 1.5, opacity=0.8)
            links.add(link)
        self.play(*star_anims, run_time=0.9)
        self.play(*[ShowCreation(l) for l in links], run_time=0.9)

        # Le vocabulaire
        legend = VGroup(
            VGroup(person(TXT, 0.8), label("bénévole : participe aux ramassages", 17)),
            VGroup(star_person(0.8), label("référent·e : accueille, gère le matériel, saisit les bilans", 17)),
            VGroup(Circle(radius=0.14).set_stroke(ACCENT, 1.5).set_fill(ACCENT, 0.08),
                   label("brigade : un quartier, une à deux sorties par mois", 17)),
        )
        for row in legend:
            row.arrange(RIGHT, buff=0.2)
        legend.arrange(RIGHT, buff=0.6)
        if legend.get_width() > 13:
            legend.set_width(13)
        legend.move_to([0, -3.2, 0])
        bg = SurroundingRectangle(legend, buff=0.2).set_fill(PANEL_BG, 0.95).set_stroke(PANEL_STROKE, 1)
        self.play(FadeIn(bg), LaggedStartMap(FadeIn, legend, shift=0.15 * LEFT, lag_ratio=0.3),
                  run_time=1.2)
        self.wait(2.2)

        self.clear_stage()

    # --- 2. Le métier : un ramassage produit un bilan -------------------------

    def metier(self):
        self.show_chip("Un ramassage produit un bilan", ACCENT)

        # Le littoral : une mer aux bords découpés (les calanques)
        xs = np.linspace(-7.2, 7.2, 40)
        rng = np.random.default_rng(7)
        coast_y = -1.5 + 0.35 * np.sin(xs * 1.3) + rng.uniform(-0.25, 0.25, len(xs))
        coast_pts = [np.array([x, y, 0]) for x, y in zip(xs, coast_y)]
        sea = Polygon(*coast_pts, np.array([7.2, -4.1, 0]), np.array([-7.2, -4.1, 0]))
        sea.set_fill(SEA, 1).set_stroke(width=0)
        shore = VMobject().set_points_smoothly(coast_pts).set_stroke(SEA_EDGE, 2.5)
        self.play(FadeIn(sea), ShowCreation(shore), run_time=1.0)

        # Une brigade descend sur le littoral, où traînent des déchets
        brigade = VGroup(star_person(0.85), *[person(TXT, 0.85) for _ in range(5)])
        brigade.arrange(RIGHT, buff=0.18).move_to([-4.5, 1.6, 0])
        trash = VGroup()
        for x in np.linspace(-5.5, -1.0, 9):
            y = np.interp(x, xs, coast_y) + 0.25
            d = Square(side_length=0.13).rotate(rng.uniform(0, PI))
            d.set_fill(rng.choice(["#9AA0B4", "#C2B280", "#6C7A89"]), 1).set_stroke(width=0)
            d.move_to([x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.05, 0.25), 0])
            trash.add(d)
        self.play(FadeIn(brigade, shift=0.2 * DOWN), LaggedStartMap(FadeIn, trash, lag_ratio=0.1))
        self.play(brigade.animate.move_to([-3.3, -0.45, 0]), run_time=1.0)
        bag = RoundedRectangle(width=0.35, height=0.45, corner_radius=0.08)
        bag.set_fill("#2C6E49", 1).set_stroke(width=0).move_to([-0.6, -0.3, 0])
        self.play(
            LaggedStart(*[d.animate.move_to(bag).scale(0.3).set_opacity(0) for d in trash],
                        lag_ratio=0.12),
            FadeIn(bag, scale=0.5),
            run_time=1.6,
        )

        # Le bilan
        card = RoundedRectangle(width=3.6, height=2.5, corner_radius=0.15)
        card.set_fill(PANEL_BG, 1).set_stroke(ACCENT, 2)
        card.move_to([3.6, 0.85, 0])
        title = label("Bilan · Sugiton", 22, ACCENT, bold=True)
        rows = VGroup(
            label("participant·es     6", 18, TXT, font=MONO_FONT),
            label("déchets           34 kg", 18, TXT, font=MONO_FONT),
            label("photos             3", 18, TXT, font=MONO_FONT),
            label("lieu, brigade, date", 18, DIM, font=MONO_FONT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        VGroup(title, rows).arrange(DOWN, aligned_edge=LEFT, buff=0.24).move_to(card)
        arrow = Arrow(bag.get_right(), card.get_left(), buff=0.2).set_color(ACCENT)
        self.play(GrowArrow(arrow), FadeIn(card), FadeIn(title))
        self.play(LaggedStartMap(FadeIn, rows, shift=0.1 * RIGHT, lag_ratio=0.25), run_time=1.0)
        note = label("le bilan est la donnée centrale : saisi une fois, il alimente tout le reste",
                     17, DIM).move_to([0, 2.45, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.wait(1.8)
        self.clear_stage()

        # Les chiffres de la communauté
        stats = [
            (lambda a: f"{int(round(20 * a))}+", "brigades"),
            (lambda a: fr_int(601 * a), "membres"),
            (lambda a: fr_int(528 * a), "ramassages"),
            (lambda a: fr_int(2103 * a), "participations"),
            (lambda a: f"{5.6 * a:.1f}".replace(".", ",") + " t", "de déchets"),
        ]
        xs_stats = np.linspace(-5.4, 5.4, len(stats))
        numbers, anims, captions = VGroup(), [], VGroup()
        for x, (fn, cap) in zip(xs_stats, stats):
            num, anim = counter(fn, np.array([x, 0.5, 0]), size=44, color=ACCENT)
            numbers.add(num)
            anims.append(anim)
            captions.add(label(cap, 19, DIM).move_to([x, -0.15, 0]))
        self.add(numbers)
        self.play(*anims, FadeIn(captions), run_time=2.2)
        scale_note = label("quelques centaines de personnes, de tous âges, souvent sur le terrain",
                           20, TXT).move_to([0, -1.4, 0])
        self.play(FadeIn(scale_note, shift=0.1 * UP))
        self.wait(2.0)
        self.clear_stage()

    # --- 3. Aujourd'hui → ce qu'on livre ------------------------------------

    def aujourdhui(self):
        self.show_chip("Aujourd'hui", WARN)

        sheets = VGroup(*[spreadsheet() for _ in range(3)])
        sheets.arrange(RIGHT, buff=0.5).move_to([-3.2, 0.4, 0])
        sheet_caption = label("des tableurs Drive, du copier-coller", 18, DIM)
        sheet_caption.next_to(sheets, DOWN, buff=0.3)
        copies = VGroup(*[
            CurvedArrow(sheets[i].get_top() + 0.1 * UP, sheets[i + 1].get_top() + 0.1 * UP,
                        angle=-PI / 2).set_stroke(WARN, 2)
            for i in range(2)
        ])

        chat = VGroup(
            chat_bubble("sortie samedi 9h ?"),
            chat_bubble("+33 6 12 34 56 78", right=True),
            chat_bubble("qui a les pinces ?"),
            chat_bubble("+33 7 98 76 54 32", right=True),
        ).arrange(DOWN, buff=0.15)
        for b in chat[1::2]:
            b.shift(0.5 * RIGHT)
        chat.move_to([3.9, 0.3, 0])
        chat_caption = label("WhatsApp : l'info se perd, les numéros circulent", 18, DIM)
        chat_caption.next_to(chat, DOWN, buff=0.3)

        self.play(LaggedStartMap(FadeIn, sheets, shift=0.2 * UP, lag_ratio=0.2), run_time=1.0)
        self.play(*[ShowCreation(c) for c in copies], FadeIn(sheet_caption), run_time=0.9)
        self.play(LaggedStartMap(FadeIn, chat, shift=0.15 * UP, lag_ratio=0.25), FadeIn(chat_caption),
                  run_time=1.3)
        clock = label("≈ 1 h de vérification par mois", 20, WARN, bold=True).move_to([0, -2.5, 0])
        self.play(FadeIn(clock, shift=0.1 * UP))
        self.wait(1.5)

        # Ce qu'on livre
        self.show_chip("Ce qu'on livre", ACCENT)
        ph = phone().move_to([-3.0, -0.3, 0])
        ph_title = label("Application mobile", 22, ACCENT, bold=True).next_to(ph, UP, buff=0.25)
        ph_users = VGroup(
            label("bénévoles", 17), label("référent·es", 17, GOLD), label("commerçant·es", 17),
        ).arrange(DOWN, buff=0.15).move_to(ph[1])
        stores = label("App Store · Google Play", 15, DIM).next_to(ph, DOWN, buff=0.2)

        web = browser().move_to([2.9, -0.3, 0])
        web_title = label("Back-office web", 22, VIOLET, bold=True).next_to(web, UP, buff=0.25)
        web_users = label("l'équipe de l'association", 17).move_to(web[0]).shift(0.15 * DOWN)
        web_sub = label("administrateur·ices", 15, DIM).next_to(web, DOWN, buff=0.2)

        self.play(
            FadeTransform(VGroup(sheets, copies, sheet_caption), VGroup(ph, ph_users)),
            FadeTransform(VGroup(chat, chat_caption), VGroup(web, web_users)),
            FadeOut(clock),
            run_time=1.3,
        )
        self.play(FadeIn(ph_title), FadeIn(web_title), FadeIn(stores), FadeIn(web_sub))
        delivery = label("livraison le 24/06/2027", 20, TXT).move_to([0, -3.1, 0])
        self.play(FadeIn(delivery, shift=0.1 * UP))
        self.wait(1.8)
        self.clear_stage()

    # --- 4. Contrainte n°1 : pas de réseau ------------------------------------

    def contrainte_reseau(self):
        self.show_chip("Contrainte n°1 : pas de réseau", ERROR)

        # Paysage : falaises de calanque à droite
        cliff = Polygon(
            [1.2, -4.1, 0], [1.6, -1.0, 0], [2.4, 0.6, 0], [3.1, -0.4, 0], [3.8, 1.4, 0],
            [4.7, 0.2, 0], [5.6, 1.8, 0], [7.2, 1.0, 0], [7.2, -4.1, 0],
        ).set_fill("#2A2C38", 1).set_stroke("#454860", 2)
        water = Rectangle(width=6.2, height=1.2).set_fill(SEA, 1).set_stroke(width=0)
        water.move_to([4.1, -3.5, 0])
        self.play(FadeIn(cliff), FadeIn(water), run_time=0.8)

        ph = phone().move_to([-3.6, -0.4, 0])
        bars = signal_bars(4).move_to(ph[1].get_corner(UR) + np.array([-0.3, -0.16, 0]))
        form_title = label("Bilan · Sugiton", 17, ACCENT, bold=True)
        fields = VGroup(*[
            VGroup(
                label(name, 13, DIM),
                RoundedRectangle(width=1.4, height=0.26, corner_radius=0.05)
                .set_fill(BG, 1).set_stroke(PANEL_STROKE, 1),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
            for name in ("participant·es", "kg", "photos")
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        button = RoundedRectangle(width=1.4, height=0.32, corner_radius=0.08)
        button.set_fill(ACCENT, 1).set_stroke(width=0)
        button_txt = label("Valider", 14, BG, bold=True).move_to(button)
        form = VGroup(form_title, fields, VGroup(button, button_txt)).arrange(DOWN, buff=0.18)
        form.move_to(ph[1]).shift(0.1 * DOWN)
        values = VGroup(*[
            label(v, 13, TXT, font=MONO_FONT).move_to(f[1]).align_to(f[1], LEFT).shift(0.08 * RIGHT)
            for f, v in zip(fields, ("6", "34", "3"))
        ])
        self.play(FadeIn(ph, shift=0.2 * UP), FadeIn(bars), FadeIn(form_title), FadeIn(fields),
                  FadeIn(VGroup(button, button_txt)))

        # La référente descend dans la calanque : le réseau tombe
        # `values` n'est pas encore à l'écran : on le déplace sans l'animer,
        # sinon l'animation l'ajouterait à la scène avant son apparition.
        trip = 5.2 * RIGHT + 0.2 * DOWN
        values.shift(trip)
        everything = VGroup(ph, bars, form_title, fields, button, button_txt)
        self.play(everything.animate.shift(trip), run_time=1.6)
        for n in (3, 2, 1, 0):
            new = signal_bars(n, WARN if n else ERROR).move_to(bars)
            self.play(Transform(bars, new), run_time=0.3)
        no_net = label("aucun réseau", 15, ERROR, bold=True).next_to(ph, UP, buff=0.15)
        self.play(FadeIn(no_net, scale=0.8), run_time=0.4)

        # Elle saisit quand même son bilan
        self.play(LaggedStartMap(FadeIn, values, lag_ratio=0.3), run_time=0.9)
        self.play(Indicate(VGroup(button, button_txt), color=ACCENT, scale_factor=1.12), run_time=0.6)
        badge_bg = RoundedRectangle(width=1.55, height=0.32, corner_radius=0.16)
        badge_bg.set_fill(WARN, 0.2).set_stroke(WARN, 1.5)
        badge_txt = label("en attente d'envoi", 12, WARN, bold=True).move_to(badge_bg)
        badge = VGroup(badge_bg, badge_txt).move_to(VGroup(button, button_txt))
        self.play(FadeTransform(VGroup(button, button_txt), badge), run_time=0.6)
        self.play(badge.animate.set_opacity(0.45), rate_func=there_and_back, run_time=0.8)

        # Ce n'est pas un bonus : c'est un critère de recette
        quote = VGroup(
            label("« Un·e référent·e saisit le bilan d'une sortie", 22, TXT),
            label("depuis son téléphone, y compris sans réseau. »", 22, TXT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        quote.move_to([-3.3, 0.9, 0])
        stamp = label("CRITÈRE DE RECETTE", 26, ERROR, bold=True)
        stamp_box = SurroundingRectangle(stamp, buff=0.15).set_stroke(ERROR, 3)
        stamp_group = VGroup(stamp_box, stamp).rotate(-6 * DEGREES).move_to([-3.3, -0.6, 0])
        self.play(FadeIn(quote, shift=0.1 * UP), run_time=0.8)
        self.play(FadeIn(stamp_group, scale=1.6), run_time=0.4)
        self.play(badge.animate.set_opacity(0.45), rate_func=there_and_back, run_time=0.8)
        self.wait(1.5)
        self.clear_stage()

    # --- 5. Contrainte n°2 : l'échelle ------------------------------------------

    def contrainte_echelle(self):
        self.show_chip("Contrainte n°2 : 6 développeur·ses deviennent 30", ERROR)

        # La frise
        months = ["sept.", "oct.", "nov.", "déc.", "janv.", "févr.", "mars", "avr.", "mai", "juin"]
        x0, x1, y = -6.2, 6.2, -2.3
        axis = Line([x0, y, 0], [x1, y, 0]).set_stroke(PANEL_STROKE, 2)
        step = (x1 - x0) / (len(months) - 1)
        ticks = VGroup()
        for i, m in enumerate(months):
            x = x0 + i * step
            ticks.add(VGroup(
                Line([x, y - 0.06, 0], [x, y + 0.06, 0]).set_stroke(DIM, 1.5),
                label(m, 14, DIM).move_to([x, y - 0.3, 0]),
            ))
        years = VGroup(
            label("2026", 14, DIM).move_to([x0, y - 0.6, 0]),
            label("2027", 14, DIM).move_to([x0 + 4 * step, y - 0.6, 0]),
        )

        def at(month_index, day):
            return x0 + (month_index + (day - 1) / 30) * step

        milestones = [
            (at(2, 27), "27/11  spécifications validées", ACCENT, 0.55),
            (at(4, 8), "08/01  maquettes", DIM, 1.05),
            (at(9, 24), "24/06  livraison", ACCENT, 0.55),
        ]
        marks = VGroup()
        for x, text, color, h in milestones:
            marks.add(VGroup(
                Line([x, y, 0], [x, y + h, 0]).set_stroke(color, 1.5),
                Dot([x, y, 0], radius=0.06).set_fill(color, 1),
                fit_x(label(text, 14, color).move_to([x, y + h + 0.18, 0])),
            ))
        self.play(ShowCreation(axis), FadeIn(ticks), FadeIn(years), run_time=1.0)
        self.play(LaggedStartMap(FadeIn, marks, shift=0.1 * UP, lag_ratio=0.3), run_time=1.0)

        week_x0, week_x1 = at(6, 8), at(6, 13)
        week = Rectangle(width=week_x1 - week_x0 + 0.12, height=0.5)
        week.set_fill(ERROR, 0.3).set_stroke(ERROR, 2).move_to([(week_x0 + week_x1) / 2, y, 0])
        week_lbl = label("08–12/03  semaine intensive", 15, ERROR, bold=True)
        week_lbl.next_to(week, UP, buff=0.5)
        week_line = Line(week.get_top(), week_lbl.get_bottom(), buff=0.05).set_stroke(ERROR, 1.5)
        self.play(FadeIn(week, scale=1.5), ShowCreation(week_line), FadeIn(week_lbl), run_time=0.8)

        # 6 → 30
        six = VGroup(*[person(TXT, 1.1) for _ in range(6)]).arrange(RIGHT, buff=0.22)
        six.move_to([-3.6, 1.0, 0])
        six_lbl = label("6 développeur·ses", 20, TXT, bold=True).next_to(six, DOWN, buff=0.25)
        self.play(LaggedStartMap(FadeIn, six, scale=0.5, lag_ratio=0.1), FadeIn(six_lbl))

        thirty = VGroup(*[person(TXT if i < 6 else VIOLET, 0.85) for i in range(30)])
        thirty.arrange_in_grid(n_rows=3, n_cols=10, buff=0.16).move_to([3.3, 1.0, 0])
        thirty_lbl = label("une trentaine, 5 jours", 20, VIOLET, bold=True)
        thirty_lbl.next_to(thirty, DOWN, buff=0.25)
        arrow = Arrow(six.get_right(), thirty.get_left(), buff=0.3).set_color(ERROR)
        self.play(
            GrowArrow(arrow),
            TransformFromCopy(six, thirty[:6]),
            LaggedStartMap(FadeIn, thirty[6:], scale=0.4, lag_ratio=0.04),
            FadeIn(thirty_lbl),
            run_time=1.8,
        )
        cold = label("les renforts arrivent à froid : ni le métier, ni le vocabulaire, ni le code",
                      17, DIM).move_to([0, -0.4, 0])
        self.play(FadeIn(cold, shift=0.1 * UP), run_time=0.6)
        self.wait(1.2)

        # Une règle floue → 30 interprétations ; une règle écrite → une seule
        top = VGroup(six, six_lbl, arrow, thirty, thirty_lbl, cold)
        self.play(FadeOut(top), run_time=0.5)

        def fan(src_text, color_fn, center, ok):
            box = RoundedRectangle(width=2.3, height=0.6, corner_radius=0.12)
            box.set_fill(PANEL_BG, 1).set_stroke(WARN if not ok else ACCENT, 2)
            txt = label(src_text, 17, WARN if not ok else ACCENT, bold=True).move_to(box)
            src = VGroup(box, txt).move_to(center + 1.2 * UP)
            ends = VGroup()
            arrows = VGroup()
            for i in range(30):
                a = -PI * 0.42 + i * (PI * 0.84) / 29
                end = center + 0.4 * DOWN + 1.9 * np.array([np.sin(a), -abs(np.cos(a)) * 0.35, 0])
                arrows.add(Line(src.get_bottom(), end).set_stroke(DIM, 1, opacity=0.6))
                ends.add(Dot(end, radius=0.07).set_fill(color_fn(i), 1))
            return src, arrows, ends

        palette = ["#F14C4C", "#F7B93E", "#4EC9B0", "#8C7CF0", "#61DAFB", "#E2B714", "#FF79C6"]
        src_a, arr_a, end_a = fan("une règle floue", lambda i: palette[(i * 3) % len(palette)],
                                  np.array([-3.4, 0.5, 0]), ok=False)
        src_b, arr_b, end_b = fan("une règle écrite", lambda i: ACCENT,
                                  np.array([3.4, 0.5, 0]), ok=True)
        cap_a = label("30 interprétations", 18, WARN).next_to(end_a, DOWN, buff=0.25)
        cap_b = label("une seule", 18, ACCENT).next_to(end_b, DOWN, buff=0.25)
        self.play(FadeIn(src_a))
        self.play(LaggedStartMap(ShowCreation, arr_a, lag_ratio=0.02),
                  LaggedStartMap(FadeIn, end_a, scale=0.3, lag_ratio=0.02),
                  FadeIn(cap_a), run_time=1.2)
        self.play(FadeIn(src_b))
        self.play(LaggedStartMap(ShowCreation, arr_b, lag_ratio=0.02),
                  LaggedStartMap(FadeIn, end_b, scale=0.3, lag_ratio=0.02),
                  FadeIn(cap_b), run_time=1.2)
        rule = label("tout ce qui est préparé avant mars est multiplié par trente", 20, TXT, bold=True)
        rule.move_to([0, 2.35, 0])
        self.play(FadeIn(rule, shift=0.1 * DOWN))
        self.wait(2.0)
        self.clear_stage()

    # --- 6. Les engagements -------------------------------------------------

    def engagements(self):
        self.show_chip("Les engagements", ACCENT)

        items = [
            ("≥ 70 %", "de tests sur le code métier"),
            ("< 2 s", "de chargement en 4G"),
            ("vieux", "téléphones supportés"),
            ("RGPD", "conformité « acceptable »"),
            ("0", "anomalie bloquante livrée"),
        ]
        cards = VGroup()
        for big, small in items:
            box = RoundedRectangle(width=2.35, height=1.6, corner_radius=0.15)
            box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
            b = label(big, 34, ACCENT, bold=True)
            s = label(small, 15, DIM)
            if s.get_width() > 2.1:
                s.set_width(2.1)
            VGroup(b, s).arrange(DOWN, buff=0.2).move_to(box)
            cards.add(VGroup(box, b, s))
        cards.arrange(RIGHT, buff=0.25).move_to([0, 0.9, 0])
        self.play(LaggedStartMap(FadeIn, cards, shift=0.2 * UP, lag_ratio=0.15), run_time=1.6)
        self.wait(1.0)

        # Ce qu'il faut retenir : deux contraintes façonnent l'architecture
        pillars = VGroup(
            label("pas de réseau sur le terrain", 22, ERROR, bold=True),
            label("+", 22, DIM),
            label("30 développeur·ses en 5 jours", 22, ERROR, bold=True),
        ).arrange(RIGHT, buff=0.35).move_to([0, -1.25, 0])
        conclusion = label("ces deux contraintes expliquent presque tous les choix d'architecture",
                           20, TXT).next_to(pillars, DOWN, buff=0.35)
        self.play(FadeIn(pillars, shift=0.1 * UP), run_time=0.8)
        self.play(FadeIn(conclusion), run_time=0.6)
        next_ep = label("épisode suivant : la carte de l'architecture  →", 16, DIM)
        next_ep.to_corner(DR, buff=0.4)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(3)
