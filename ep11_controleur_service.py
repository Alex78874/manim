"""
Épisode 11 — Contrôleur mince, service épais, projection unique (ADR 0004)

Savoir où écrire une règle métier, et introduire versContrat() avant l'épisode 12.
  1. Trois couches, sans intermédiaire : contrôleur (HTTP), service (métier ET
     accès aux données), modèle (persistance). ADR 0004, section Décision.
  2. Le contrôleur se vide : une version « grasse » de creer() (ILLUSTRATION :
     la logique réelle du service recopiée dans le contrôleur) ; le métier et le
     SQL partent dans utilisateurs_service.ts (extrait réel).
  3. Le vrai contrôleur : trois méthodes de une à deux lignes.
  4. versContrat() : la projection champ par champ. password (et updatedAt)
     ne passent pas la frontière ; une seule projection pour toute l'API,
     importée aussi par session_service.ts.
  5. L'alternative écartée : une couche repository (+ mappers), barrée.

Sources : docs/adr/0004-metier-dans-un-service.md,
server/app/controllers/utilisateurs_controller.ts,
server/app/services/utilisateurs_service.ts (creer : 116-178, versContrat : 73-85),
server/app/services/session_service.ts (import de versContrat),
server/database/schema.ts (colonnes de UtilisateurSchema),
contract/features/utilisateurs/schemas/Utilisateur.yaml.

Rendu vidéo :  manimgl ep11_controleur_service.py Ep11ControleurService -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


CTRL_C = BLUE
SERV_C = GOLD
MODEL_C = VIOLET


FAT_SRC = """async creer({ request, response }: HttpContext) {
  const { email, nom, password } = request.body()
  try {
    const u = await db.transaction(async (trx) => {
      const nouveau = await Utilisateur.create(
        { email, nom, password }, { client: trx })
      await nouveau.refresh()
      return nouveau
    })
    return response.created({
      id: u.id, email: u.email, nom: u.nom,
      role: u.role, createdAt: u.createdAt.toISO()!,
    })
  } catch (erreur) {
    if (erreur?.code === '23505') {
      throw new EmailDejaUtilise()
    }
    throw erreur
  }
}"""

SERVICE_SRC = """async creer(donnees: { … }): Promise<UtilisateurPublic> {
  try {
    return await db.transaction(async (trx) => {
      const utilisateur = await Utilisateur.create(
        { email: donnees.email, nom: donnees.nom, … },
        { client: trx }
      )
      await utilisateur.refresh()
      return versContrat(utilisateur)
    })
  } catch (erreur) {
    if ((erreur as { code?: string })?.code === VIOLATION_UNICITE) {
      throw new EmailDejaUtilise()
    }
    throw erreur
  }
}"""

CONTROLLER_SRC = """export default class UtilisateursController {
  /** listerUtilisateurs — GET /utilisateurs */
  async lister({ request }: HttpContext) {
    const { page, limit, role } = request.qs()

    return utilisateursService.lister({ page, limit, role })
  }

  /** creerUtilisateur — POST /utilisateurs */
  async creer({ request, response }: HttpContext) {
    const { email, nom, password } = request.body()

    return response.created(await utilisateursService.creer({ email, nom, password }))
  }

  /** modifierUtilisateur — PATCH /utilisateurs/:id */
  async modifier({ params, request, auth }: HttpContext) {
    return utilisateursService.modifier(params.id, request.body(), auth.getUserOrFail())
  }
}"""

VERS_CONTRAT_SRC = """export function versContrat(utilisateur: Utilisateur): UtilisateurPublic {
  return {
    id: utilisateur.id,
    email: utilisateur.email,
    nom: utilisateur.nom,
    // …
    role: utilisateur.role as RoleUtilisateur,
    createdAt: utilisateur.createdAt.toISO()!,
  }
}"""


def code_panel(filename, source, center, width, height, tag=None, tag_color=DIM, max_scale=1.0):
    panel = EditorPanel(filename, center, width=width, height=height, tag=tag, tag_color=tag_color)
    view = CodeView(source, ["typescript"])
    panel.fit_code(view, max_scale=max_scale)
    return panel, view


def chip(text, color, size=16):
    t = label(text, size, color, font=MONO_FONT, bold=True)
    bg = RoundedRectangle(width=t.get_width() + 0.3, height=t.get_height() + 0.22, corner_radius=0.1)
    bg.set_fill(color, 0.12).set_stroke(color, 1.5)
    t.move_to(bg)
    return VGroup(bg, t)


class Ep11ControleurService(EpisodeScene):
    EPISODE = "11"
    TITLE = "Contrôleur mince, service épais"

    def construct(self):
        self.trois_couches()
        self.vider()
        self.vrai_controleur()
        self.projection()
        self.ecartee()

    # --- 1. Trois couches ------------------------------------------------------------

    def trois_couches(self):
        self.show_chip("ADR 0004 : trois couches, sans intermédiaire")
        specs = [
            ("contrôleur", "lit la requête, appelle le service, choisit le code de retour", CTRL_C),
            ("service", "les règles métier ET l'accès aux données, une fonction par opération", SERV_C),
            ("modèle", "la persistance", MODEL_C),
        ]
        cards = VGroup()
        for name, desc, color in specs:
            box = RoundedRectangle(width=11.5, height=1.0, corner_radius=0.14)
            box.set_fill(color, 0.08).set_stroke(color, 2)
            n = label(name, 24, color, font=MONO_FONT, bold=True)
            d = label(desc, 19, TXT)
            n.move_to(box.get_left() + np.array([0.35 + n.get_width() / 2, 0, 0]))
            d.move_to(box.get_left() + np.array([3.0 + d.get_width() / 2, 0, 0]))
            cards.add(VGroup(box, n, d))
        cards.arrange(DOWN, buff=0.45).move_to([0, 0.35, 0])
        arrows = VGroup(*[
            Arrow(cards[i][0].get_bottom(), cards[i + 1][0].get_top(), buff=0.04, thickness=2)
            .set_color(DIM) for i in range(2)
        ])
        for i, card in enumerate(cards):
            self.play(FadeIn(card, shift=0.1 * DOWN), run_time=0.6)
            if i < 2:
                self.play(GrowArrow(arrows[i]), run_time=0.3)
        rule = label("un contrôleur de plus d'une quinzaine de lignes signale du métier qui a fui",
                     19, WARN, bold=True).move_to([0, -2.55, 0])
        fit_x(rule)
        self.play(FadeIn(rule, shift=0.1 * UP), run_time=0.6)
        self.wait(3.2)
        self.clear_stage()

    # --- 2. Le contrôleur se vide ---------------------------------------------------------

    def vider(self):
        self.show_chip("Le métier quitte le contrôleur", SERV_C)
        fat_p, fat_v = code_panel("utilisateurs_controller.ts", FAT_SRC, np.array([-3.55, -0.5, 0]),
                                  6.95, 6.3, tag="ILLUSTRATION : à ne pas faire", tag_color=ERROR)
        serv_p, serv_v = code_panel("utilisateurs_service.ts", SERVICE_SRC, np.array([3.55, -0.5, 0]),
                                    6.95, 6.3, tag="l. 116-178, extrait", tag_color=SERV_C)
        self.play(FadeIn(fat_p.chrome), FadeIn(fat_v.group), run_time=0.8)
        count = label("20 lignes : transaction, SQL, projection, erreur 409…", 16, ERROR)
        count.next_to(fat_p.box, DOWN, buff=0.12)
        self.play(FadeIn(count), run_time=0.4)
        self.wait(2.6)

        # Les lignes de métier s'allument, puis partent dans le service
        moving = list(range(3, 20))
        boxes = [fat_v.line_box(i) for i in moving]
        rects = VGroup(*[highlight_rect(b, SERV_C, 0.12) for b in boxes])
        self.play(FadeIn(rects), run_time=0.5)
        self.play(FadeIn(serv_p.chrome), run_time=0.5)
        keep_last = fat_v.lines[19]
        flying = VGroup(*[fat_v.lines[i - 1] for i in moving])
        fat_v.lines.remove(*flying)
        self.add(flying)
        self.play(FadeOut(rects),
                  ReplacementTransform(flying, serv_v.lines),
                  FadeIn(serv_v.gutter),
                  FadeOut(fat_v.gutter),
                  run_time=1.6)
        # Le contrôleur ne garde que sa signature, la lecture du corps et l'appel,
        # écrit dans la même police que le reste du panneau.
        call_v = CodeView("  return response.created(\n"
                          "    await utilisateursService.creer({ email, nom, … }))",
                          ["typescript"], gutter=False)
        scale = fat_v.line_h / call_v.line_h
        # (les étais des lignes 3 à 19 sont partis avec elles : on se repère sur la ligne 2)
        strut_x = fat_v.code_struts[1].get_left()[0]
        y3 = fat_v.line_y(2) - fat_v.line_h
        call_v.fit(scale, np.array([strut_x, y3 + call_v.block_h * scale / 2, 0]))
        call = call_v.group
        self.play(keep_last.animate.move_to([keep_last.get_center()[0], fat_v.line_y(2) - 3 * fat_v.line_h, 0]),
                  FadeIn(call, shift=0.1 * LEFT), FadeOut(count), run_time=0.8)
        after = label("il reste du HTTP : lire, appeler, choisir le code (201)", 16, ACCENT, bold=True)
        after.next_to(fat_p.box, DOWN, buff=0.12)
        vc = serv_v.token_box(9, "versContrat(utilisateur)")
        self.play(FadeIn(after), flash([vc], SERV_C, 0.6), run_time=0.6)
        self.play(FadeIn(highlight_rect(vc, SERV_C, 0.15)), run_time=0.3)
        self.wait(3.4)
        self.clear_stage()

    # --- 3. Le vrai contrôleur ---------------------------------------------------------------

    def vrai_controleur(self):
        self.show_chip("Le vrai contrôleur", CTRL_C)
        p, v = code_panel("server/app/controllers/utilisateurs_controller.ts", CONTROLLER_SRC,
                          np.array([0, -0.85, 0]), 13.6, 5.7, tag="lignes 16-38, sans les commentaires",
                          tag_color=CTRL_C)
        self.play(FadeIn(p.chrome), FadeIn(v.group), run_time=0.8)
        calls = [v.line_box(6), v.line_box(13), v.line_box(18)]
        self.play(flash(calls, CTRL_C, 0.45), run_time=1.35)
        self.play(*[FadeIn(highlight_rect(b, CTRL_C, 0.12)) for b in calls], run_time=0.4)
        note = label("une à deux lignes par méthode · aucune règle métier · aucun accès à la base",
                     17, CTRL_C, bold=True)
        note.move_to([0, 2.42, 0])
        fit_x(note)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(3.6)
        self.clear_stage()

    # --- 4. versContrat ------------------------------------------------------------------------

    def projection(self):
        self.show_chip("versContrat() : la projection unique", ACCENT)
        p, v = code_panel("utilisateurs_service.ts", VERS_CONTRAT_SRC, np.array([0, 1.12, 0]),
                          10.4, 3.2, tag="lignes 73-85", tag_color=ACCENT)
        self.play(FadeIn(p.chrome), FadeIn(v.group), run_time=0.7)
        fields = [v.line_box(i) for i in (3, 4, 5, 7, 8)]
        self.play(flash(fields, ACCENT, 0.3), run_time=1.5)

        # Les colonnes du modèle traversent la frontière, champ par champ
        cols = ["id", "email", "nom", "password", "role", "createdAt", "updatedAt"]
        model = VGroup(*[chip(c, MODEL_C) for c in cols]).arrange(RIGHT, buff=0.22)
        model.move_to([0.6, -0.8, 0])
        m_lbl = label("modèle Lucid", 16, MODEL_C, bold=True)
        m_lbl.next_to(model, LEFT, buff=0.3)
        frontier = dashed(Line([-6.6, -1.75, 0], [6.6, -1.75, 0]), num_dashes=80)
        frontier.set_stroke(ACCENT, 2)
        f_lbl = label("versContrat()", 15, ACCENT, font=MONO_FONT, bold=True)
        f_lbl.move_to([-5.7, -1.55, 0])
        c_lbl = label("contrat : Utilisateur", 16, ACCENT, bold=True)
        self.play(FadeIn(m_lbl), LaggedStartMap(FadeIn, model, lag_ratio=0.08), run_time=0.9)
        self.play(ShowCreation(frontier), FadeIn(f_lbl), run_time=0.6)

        passing = [0, 1, 2, 4, 5]
        out = VGroup(*[chip(cols[i], ACCENT) for i in passing]).arrange(RIGHT, buff=0.3)
        out.move_to([0.6, -2.7, 0])
        c_lbl.next_to(out, LEFT, buff=0.3)
        self.play(*[TransformFromCopy(model[i], out[k]) for k, i in enumerate(passing)],
                  FadeIn(c_lbl), run_time=1.1)

        # password se heurte à la frontière
        pw = model[3].copy()
        self.add(pw)
        self.play(pw.animate.move_to([model[3].get_center()[0], -1.75, 0]), run_time=0.5)
        cross = label("✖", 30, ERROR, bold=True).move_to(pw)
        strike = Line(model[3].get_left(), model[3].get_right()).set_stroke(ERROR, 3)
        self.play(FadeOut(pw, scale=0.6), FadeIn(cross, scale=1.6), ShowCreation(strike),
                  model[6].animate.set_opacity(0.35), run_time=0.6)
        why = label("password ne sort jamais · updatedAt n'est pas au contrat", 16, ERROR)
        why.move_to([0.6, -3.35, 0])
        self.play(FadeIn(why), run_time=0.4)
        self.wait(2.0)
        one = label("une seule projection pour toute l'API : session_service.ts l'importe aussi (EXG-USR-008)",
                    16, TXT).move_to([0, -3.75, 0])
        fit_x(one)
        self.play(FadeIn(one, shift=0.1 * UP), run_time=0.5)
        self.wait(3.2)
        self.clear_stage()

    # --- 5. L'alternative écartée ------------------------------------------------------------

    def ecartee(self):
        self.show_chip("Écarté : service + repository + mappers", ERROR)
        names = [("contrôleur", CTRL_C), ("service", SERV_C), ("modèle", MODEL_C)]
        boxes = VGroup(*[node(n, None, c, width=2.6) for n, c in names])
        boxes.arrange(RIGHT, buff=1.4).move_to([0, 0.6, 0])
        arrows = VGroup(*[
            Arrow(boxes[i].get_right(), boxes[i + 1].get_left(), buff=0.1, thickness=2).set_color(DIM)
            for i in range(2)
        ])
        self.play(FadeIn(boxes), *[GrowArrow(a) for a in arrows], run_time=0.8)
        self.wait(0.5)

        # Une couche de plus s'intercale, puis est barrée
        repo = node("repository", "+ mappers", DIM, width=2.4, planned=True)
        repo.move_to([boxes[1].get_center()[0] + 2.0, -1.0, 0])
        r_in = link(edge_point(boxes[1], DOWN), edge_point(repo, LEFT), DIM, planned=True)
        r_out = link(edge_point(repo, RIGHT), edge_point(boxes[2], DOWN), DIM, planned=True)
        self.play(FadeIn(repo, shift=0.2 * UP), ShowCreation(r_in), ShowCreation(r_out), run_time=0.9)
        x1 = Line(repo.get_corner(UL), repo.get_corner(DR)).set_stroke(ERROR, 4)
        x2 = Line(repo.get_corner(DL), repo.get_corner(UR)).set_stroke(ERROR, 4)
        self.play(ShowCreation(x1), ShowCreation(x2), run_time=0.5)
        why = VGroup(
            label("trois fichiers par opération, pour un seul magasin de données", 19, TXT),
            label("le service écrit ses requêtes ; si deux services partagent un jour une requête,",
                  16, DIM),
            label("la question se reposera (ADR 0004)", 16, DIM),
        ).arrange(DOWN, buff=0.14).move_to([0, -2.6, 0])
        self.play(FadeIn(why, shift=0.1 * UP), run_time=0.7)
        self.wait(3.2)
        next_ep = label("épisode suivant : le middleware de contrat dans les deux sens  →", 15, DIM)
        next_ep.to_corner(DR, buff=0.3)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(1.5)
