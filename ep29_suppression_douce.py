"""
Épisode 29 — Rien n'est supprimé : suppression douce (ADR 0013)

Bloc E : les règles hors ligne non négociables.
  1. Synchro par delta et suppression franche : la ligne disparaît du serveur,
     le delta ne renvoie rien, le téléphone garde un fantôme.
  2. Avec `supprime_le` : la ligne reste, marquée ; le delta la renvoie sous
     forme de pierre tombale `{ id, supprimeLe }`, et le téléphone la retire.
  3. Anonymiser un compte : il ne reste que `{ id, supprimeLe }` ; les bilans
     gardent leurs kg ; seules les photos sont réellement détruites.
  4. Le filtre : dans le service généré, `.whereNull('supprime_le')` n'existe
     que dans un TODO commenté, et `lister()` renvoie une liste vide. C'est au
     développeur d'écrire la requête. Rappel : l'unicité (épisode 17).

Statut affiché : documenté + dans le gabarit (la colonne `supprime_le` de la
migration générée). Le filtre est à écrire ; la synchro delta (`modifieDepuis`)
et l'anonymisation des comptes sont documentées, pas codées (la table
`utilisateurs` n'a pas de colonne `supprime_le`).

Sources : docs/adr/0013-suppression-douce-et-anonymisation.md,
docs/adr/0006 (annexe §6 et « Le conflit avec le RGPD »), CLAUDE.md:54-56,
scripts/feature.mjs:268-275 (migration), 321-338 (service).

Rendu vidéo :  manimgl ep29_suppression_douce.py Ep29SuppressionDouce -w
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


LIEUX = [("018f…a1", "Sugiton"), ("018f…b2", "Morgiou"), ("018f…c3", "Sormiou")]
TOMBE = "2027-04-02T10:00:00Z"     # l'exemple de l'ADR 0006, annexe §6


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep29SuppressionDouce(EpisodeScene):
    EPISODE = "29"
    TITLE = "Rien n'est supprimé"

    def construct(self):
        self.set_banner({"documenté", "dans le gabarit npm run feature"},
                        "la colonne est générée · le filtre reste à écrire")
        self.delta(soft=False)
        self.delta(soft=True)
        self.anonymiser()
        self.filtre()

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

    # --- 1 et 2. La synchronisation par delta -----------------------------------------

    def delta(self, soft):
        if soft:
            self.show_chip("Avec supprime_le : la ligne revient, marquée", ACCENT)
        else:
            self.show_chip("Suppression franche : le téléphone garde un fantôme", ERROR)

        # Le téléphone et sa liste en cache
        ph = phone().move_to([-5.0, -0.35, 0])
        scr = ph[1]
        head = label("Ramassages", 16, ACCENT, bold=True)
        rows_ph = VGroup()
        for _, lieu in LIEUX:
            box = RoundedRectangle(width=1.5, height=0.42, corner_radius=0.07)
            box.set_fill(BG, 1).set_stroke(PANEL_STROKE, 1)
            rows_ph.add(VGroup(box, label(lieu, 14, TXT, bold=True).move_to(box)))
        rows_ph.arrange(DOWN, buff=0.12)
        VGroup(head, rows_ph).arrange(DOWN, buff=0.22).move_to(scr).shift(0.35 * UP)

        # La table côté serveur
        cols = [("id", 1.1), ("lieu", 2.75)] + ([("supprime_le", 4.75)] if soft else [])
        tbl_box = RoundedRectangle(width=6.2 if soft else 4.6, height=2.5, corner_radius=0.14)
        tbl_box.set_fill(PANEL_BG, 1).set_stroke(VIOLET, 1.5)
        tbl_box.move_to([3.4 if soft else 2.6, 0.55, 0])
        x_left = tbl_box.get_left()[0] + 0.35
        title = label("table ramassages · server/", 15, VIOLET, bold=True)
        title.next_to(tbl_box, UP, buff=0.12).align_to(tbl_box, LEFT)
        y0 = tbl_box.get_top()[1] - 0.4
        header = VGroup(*[
            label(name, 14, DIM, font=MONO_FONT).move_to([0, y0, 0]) for name, _ in cols
        ])
        offsets = [0, 1.55, 3.25]
        for h, off in zip(header, offsets):
            h.set_x(x_left + off + h.get_width() / 2)
        sep = Line([tbl_box.get_left()[0], y0 - 0.25, 0], [tbl_box.get_right()[0], y0 - 0.25, 0])
        sep.set_stroke(PANEL_STROKE, 1)
        rows_db = VGroup()
        for i, (ident, lieu) in enumerate(LIEUX):
            y = y0 - 0.65 - i * 0.48
            cells = [label(ident, 15, TXT, font=MONO_FONT), label(lieu, 15, TXT, font=MONO_FONT)]
            if soft:
                cells.append(label("null", 15, DIM, font=MONO_FONT))
            for c, off in zip(cells, offsets):
                c.move_to([x_left + off + c.get_width() / 2, y, 0])
            rows_db.add(VGroup(*cells))

        self.play(FadeIn(ph, shift=0.2 * UP), FadeIn(head), FadeIn(rows_ph),
                  FadeIn(tbl_box), FadeIn(title), FadeIn(header), ShowCreation(sep), FadeIn(rows_db),
                  run_time=0.9)
        self.wait(0.6)

        # Morgiou est annulé côté serveur
        target = rows_db[1]
        if soft:
            stamp = label("2027-04-02 10:00", 15, ERROR, font=MONO_FONT, bold=True)
            stamp.move_to(target[2]).align_to(target[2], LEFT)
            fit_w(stamp, tbl_box.get_right()[0] - stamp.get_left()[0] - 0.15)
            stamp.align_to(target[2], LEFT)
            what = label("UPDATE … SET supprime_le = maintenant", 14, DIM, font=MONO_FONT)
            what.next_to(tbl_box, DOWN, buff=0.15).align_to(tbl_box, LEFT)
            self.play(FadeIn(what), run_time=0.4)
            self.play(Transform(target[2], stamp), target[:2].animate.set_opacity(0.45), run_time=0.7)
        else:
            what = label("DELETE … la ligne est effacée", 14, DIM, font=MONO_FONT)
            what.next_to(tbl_box, DOWN, buff=0.15).align_to(tbl_box, LEFT)
            strike = Line(target.get_left() + 0.1 * LEFT, target.get_right() + 0.1 * RIGHT).set_stroke(ERROR, 3)
            self.play(FadeIn(what), ShowCreation(strike), run_time=0.6)
            self.play(FadeOut(target), FadeOut(strike), rows_db[2].animate.move_to(target), run_time=0.7)
        self.wait(0.6)

        # Le téléphone se synchronise par delta
        req = label("GET /ramassages?modifieDepuis=…", 14, TXT, font=MONO_FONT)
        y_req, y_res = 1.6, -1.25
        a_req = Arrow([ph.get_right()[0] + 0.1, y_req - 0.35, 0], [tbl_box.get_left()[0] - 0.1, y_req - 0.35, 0],
                      buff=0).set_color(BLUE)
        req.next_to(a_req, UP, buff=0.08)
        self.play(GrowArrow(a_req), FadeIn(req), run_time=0.7)
        a_res = Arrow([tbl_box.get_left()[0] - 0.1, y_res, 0], [ph.get_right()[0] + 0.1, y_res, 0],
                      buff=0).set_color(ACCENT if soft else DIM)
        if soft:
            res = VGroup(label('[{ "id": "018f…b2",', 14, ACCENT, font=MONO_FONT),
                         label(f'   "supprimeLe": "{TOMBE}" }}]', 14, ACCENT, font=MONO_FONT))
            res.arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        else:
            res = VGroup(label("[ ]   rien n'a changé…", 14, DIM, font=MONO_FONT))
        fit_w(res, a_res.get_width() + 0.6)
        res.next_to(a_res, DOWN, buff=0.1)
        self.play(GrowArrow(a_res), FadeIn(res), run_time=0.7)
        self.wait(0.6)

        ghost_row = rows_ph[1]
        if soft:
            self.play(ghost_row.animate.set_opacity(0.15), run_time=0.5)
            self.play(FadeOut(ghost_row), rows_ph[2].animate.move_to(ghost_row), run_time=0.6)
            msg = label("le téléphone apprend la disparition : la pierre tombale ne porte aucune donnée",
                        17, TXT, bold=True)
        else:
            ghost = dashed(ghost_row[0].copy()).set_stroke(ERROR, 1.8)
            tag = label("fantôme", 13, ERROR, bold=True).next_to(ghost_row, RIGHT, buff=0.15)
            self.play(ghost_row[1].animate.set_color(ERROR), FadeIn(ghost), FadeIn(tag), run_time=0.6)
            self.play(Indicate(ghost_row, color=ERROR, scale_factor=1.08), run_time=0.6)
            msg = label("une absence ne se synchronise pas : il garde la ligne pour toujours",
                        17, TXT, bold=True)
        msg.move_to([0, -2.85, 0])
        fit_w(msg, 13.2)
        self.play(FadeIn(msg, shift=0.1 * UP), run_time=0.6)
        self.wait(3.2)
        self.clear_stage()

    # --- 3. Anonymiser un compte ----------------------------------------------------------

    def anonymiser(self):
        self.show_chip("Supprimer son compte : vider, anonymiser, jamais effacer", GOLD)

        def card(title, color, x):
            box = RoundedRectangle(width=4.1, height=3.3, corner_radius=0.16)
            box.set_fill(PANEL_BG, 1).set_stroke(color, 1.5).move_to([x, 0.35, 0])
            t = label(title, 18, color, bold=True).move_to(box.get_top() + 0.33 * DOWN)
            return box, t

        def mono_lines(lines, anchor, color=TXT):
            g = VGroup(*[label(s, 15, color, font=MONO_FONT) for s in lines])
            g.arrange(DOWN, aligned_edge=LEFT, buff=0.12)
            return g.move_to(anchor)

        # Le compte
        b1, t1 = card("Compte : vidé", GOLD, -4.45)
        acc = mono_lines(['id:    "018f…d4"', 'nom:   "Léa"', 'email: "lea@exemple.fr"', "supprimeLe: null"],
                         b1.get_center() + 0.15 * DOWN)
        # Les bilans
        b2, t2 = card("Bilans : anonymisés", ACCENT, 0)
        bil = mono_lines(["Bilan Sugiton", "auteur·ice: Léa", "déchets: 12 kg"], b2.get_center() + 0.15 * DOWN)
        # Les photos
        b3, t3 = card("Photos : vraiment détruites", ERROR, 4.45)
        frame = RoundedRectangle(width=1.7, height=1.25, corner_radius=0.08).set_fill(SEA, 1).set_stroke(SEA_EDGE, 1.5)
        frame.move_to(b3.get_center() + 0.05 * DOWN)
        faces = VGroup(person(TXT, 1.2), person(TXT, 1.0)).arrange(RIGHT, buff=0.2).move_to(frame)
        photo = VGroup(frame, faces)

        self.play(FadeIn(b1), FadeIn(t1), FadeIn(acc), run_time=0.6)
        self.play(FadeIn(b2), FadeIn(t2), FadeIn(bil), run_time=0.6)
        self.play(FadeIn(b3), FadeIn(t3), FadeIn(photo), run_time=0.6)
        self.wait(1.0)

        # Le compte devient une pierre tombale
        tomb = mono_lines(['id:    "018f…d4"', f'supprimeLe: "{TOMBE[:10]}…"'], b1.get_center() + 0.15 * DOWN)
        self.play(acc[1].animate.set_color(ERROR), acc[2].animate.set_color(ERROR), run_time=0.4)
        self.play(FadeTransform(acc, tomb), run_time=0.8)
        c1 = label("ni nom, ni email : une pierre tombale", 14, DIM).next_to(b1.get_bottom(), UP, buff=0.25)
        self.play(FadeIn(c1), run_time=0.4)

        # Le bilan perd son auteur·ice, garde ses kilos
        new_author = label("auteur·ice: anonyme", 15, DIM, font=MONO_FONT).move_to(bil[1]).align_to(bil[1], LEFT)
        self.play(Transform(bil[1], new_author), Indicate(bil[2], color=ACCENT, scale_factor=1.15), run_time=0.8)
        c2 = label("les chiffres restent : 528 ramassages, 5,6 t", 14, DIM).next_to(b2.get_bottom(), UP, buff=0.25)
        self.play(FadeIn(c2), run_time=0.4)

        # La photo est la seule vraie suppression
        cross = VGroup(Line(frame.get_corner(UL), frame.get_corner(DR)), Line(frame.get_corner(DL), frame.get_corner(UR)))
        cross.set_stroke(ERROR, 4)
        self.play(ShowCreation(cross), photo.animate.set_opacity(0.3), run_time=0.6)
        c3 = label("des visages : rien à anonymiser", 14, DIM).next_to(b3.get_bottom(), UP, buff=0.25)
        self.play(FadeIn(c3), run_time=0.4)

        rule = label("ce qui est personnel est vidé, ce qui est statistique est anonymisé, rien n'est effacé",
                     18, TXT, bold=True).move_to([0, -2.0, 0])
        fit_w(rule, 13.2)
        honest = label("documenté (ADR 0013) : la table utilisateurs n'a pas encore de colonne supprime_le",
                       14, DIM).move_to([0, -2.55, 0])
        self.play(FadeIn(rule, shift=0.1 * UP), run_time=0.6)
        self.play(FadeIn(honest), run_time=0.4)
        self.wait(3.4)
        self.clear_stage()

    # --- 4. Le filtre, à écrire --------------------------------------------------------------

    def filtre(self):
        self.show_chip("Le filtre : c'est à vous de l'écrire", ERROR)
        mig_src = "table.timestamp('supprime_le').nullable()"
        mig = EditorPanel("server/database/migrations/…_create_ramassages_table.ts", [-3.35, 1.95, 0],
                          width=6.6, height=1.1)
        mview = CodeView(mig_src, ["typescript"], gutter=False)
        mig.fit_code(mview, max_scale=0.62)

        src = (
            "async lister(criteres: { page: number; limit: number }): Promise<Liste> {\n"
            "  /**\n"
            "   * TODO : lancer la migration, écrire le modèle, puis la vraie requête.\n"
            "   *\n"
            "   *   const requete = Ramassage.query()\n"
            "   *     .whereNull('supprime_le')   ←  NON NÉGOCIABLE, voir ci-dessous\n"
            "   *     .orderBy('created_at', 'desc')\n"
            "   *  …\n"
            "   * C'est la faute la plus facile à commettre et la plus\n"
            "   * difficile à voir — elle ne casse aucun test tant que personne n'a\n"
            "   * supprimé quoi que ce soit.\n"
            "   */\n"
            "  return { items: [], total: 0, page: criteres.page, limit: criteres.limit }\n"
            "}"
        )
        svc = EditorPanel("server/app/services/ramassages_service.ts", [-1.65, -0.85, 0], width=10.6, height=4.0,
                          tag="généré par npm run feature ramassages", tag_color=GOLD)
        sview = CodeView(src, ["typescript"])
        svc.fit_code(sview, max_scale=0.72)

        self.play(FadeIn(mig.chrome), FadeIn(mview.group), run_time=0.6)
        ok = label("✔ générée : la colonne est là", 16, ACCENT, bold=True).next_to(mig.box, RIGHT, buff=0.35)
        self.play(FadeIn(ok), run_time=0.4)
        self.wait(0.8)
        self.play(FadeIn(svc.chrome), FadeIn(sview.group, shift=0.1 * UP), run_time=0.8)
        self.wait(0.6)

        # Le filtre n'existe que dans un commentaire
        wbox = sview.token_box(6, ".whereNull('supprime_le')")
        self.play(flash([wbox], ERROR, 1.0))
        h1 = highlight_rect(wbox, ERROR)
        n1 = VGroup(label("seulement dans", 15, ERROR, bold=True), label("un commentaire", 15, ERROR, bold=True))
        n1.arrange(DOWN, buff=0.06, aligned_edge=LEFT).next_to(svc.box, RIGHT, buff=0.25).set_y(wbox[0][1])
        fit_x(n1, 0.2)
        self.play(FadeIn(h1), FadeIn(n1), run_time=0.5)
        self.wait(1.2)

        rbox = sview.line_box(13)
        self.play(flash([rbox], WARN, 0.8))
        h2 = highlight_rect(rbox, WARN)
        n2 = VGroup(label("liste vide,", 15, WARN, bold=True), label("mais conforme", 15, WARN, bold=True))
        n2.arrange(DOWN, buff=0.06, aligned_edge=LEFT).next_to(svc.box, RIGHT, buff=0.25).set_y(rbox[0][1])
        fit_x(n2, 0.2)
        self.play(FadeIn(h2), FadeIn(n2), run_time=0.5)
        self.wait(1.2)

        # Les lignes 9 à 11 : la phrase qui résume tout
        self.play(flash([sview.line_box(9), sview.line_box(10), sview.line_box(11)], ERROR, 0.45))
        punch = label("la faute la plus facile à commettre : aucun test du gabarit ne la détecte", 17, TXT, bold=True)
        bg = SurroundingRectangle(punch, buff=0.14).set_fill(BG, 0.96).set_stroke(ERROR, 1.2)
        VGroup(bg, punch).move_to([0, -3.25, 0])
        self.play(FadeIn(bg), FadeIn(punch), run_time=0.6)
        self.wait(2.6)

        # Rappel : l'unicité
        uni = VGroup(
            label("rappel épisode 17", 13, GOLD, bold=True),
            label("une contrainte d'unicité doit", 14, TXT),
            label("tenir compte des lignes supprimées", 14, TXT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        u_bg = SurroundingRectangle(uni, buff=0.16).set_fill(GOLD, 0.06).set_stroke(GOLD, 1.2)
        u = VGroup(u_bg, uni)
        u.next_to(svc.box, RIGHT, buff=0.2).set_y(svc.box.get_center()[1])
        fit_x(u, 0.15)
        self.play(FadeOut(n1), FadeOut(n2), FadeIn(u, shift=0.1 * LEFT), run_time=0.5)
        self.wait(1.5)
        nxt = label("fin du bloc : la suite, npm run verifier  →", 15, DIM).move_to([4.6, 2.6, 0])
        fit_x(nxt)
        self.play(FadeIn(nxt), run_time=0.5)
        self.wait(2.5)
