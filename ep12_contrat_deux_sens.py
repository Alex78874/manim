"""
Épisode 12 — Le middleware de contrat dans les deux sens (pièce maîtresse)

Distinguer 400 (faute du client) et 500 (bug du serveur), et voir le YAML s'exécuter.
  0. Un gardien, deux sens : entrée -> 400, sortie -> 500.
  A. La query : `?page=2` devient le nombre 2, `limit` reçoit 20 par défaut ; `?limite=5` -> 400.
  B. Le corps : un POST avec `role: 'administrateur'` -> 400 VALIDATION_ERROR, details /role.
     Le contrôleur n'est jamais atteint (EXG-USR-004).
  C. La réponse : un champ non déclaré (`password`) -> 500 CONTRACT_RESPONSE_VIOLATION.
  D. En production : `logger.error`, et la réponse part quand même.
  Encart : 403 / 409 sortent par le handler d'exceptions, sans validation.
  Fin : ce qu'il faut retenir ; les messages Ajv sont en anglais.

Sources : server/app/middleware/contract_middleware.ts, server/app/services/contract_validator.ts,
server/app/exceptions/handler.ts, server/app/services/utilisateurs_service.ts,
server/app/controllers/utilisateurs_controller.ts, server/start/routes/utilisateurs.ts,
contract/features/utilisateurs/{paths/utilisateurs.yaml, schemas/CreationUtilisateur.yaml,
schemas/Utilisateur.yaml}, server/tests/functional/utilisateurs.spec.ts (EXG-USR-001, -004).

Note : le code fautif de la partie C (ajout de `password` dans la projection) est une
illustration, pas du code du dépôt. Le reste des extraits est copié du dépôt (raccourci par « … »).

Rendu vidéo :  manimgl ep12_contrat_deux_sens.py Ep12ContratDeuxSens -w
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

class Excerpt(CodeView):
    """Un CodeView dont la numérotation commence à `first` (extrait d'un vrai fichier)."""

    def __init__(self, source, lexer_names, first=1, font_size=BASE_FS):
        spans = highlight_lines(source, lexer_names)
        cal = MarkupText(STRUT * 20, font=CODE_FONT, font_size=font_size)
        self.adv = cal.get_width() / 20
        self.block_h = cal.get_height()
        self.line_h = self.block_h * LINE_SPACING
        self.text = source.split("\n")
        cols = max(2, len(str(first + len(spans) - 1)))
        self.gutter, self.lines = VGroup(), VGroup()
        self.gutter_struts, self.code_struts = [], []
        code_x = (cols + GUTTER_GAP) * self.adv
        for i, line_markup in enumerate(spans):
            y = -i * self.line_h
            num, num_strut = make_line(f'<span foreground="{DIM}">{first + i:>{cols}}</span>', font_size)
            place(num, num_strut, 0, y)
            self.gutter.add(num)
            self.gutter_struts.append(num_strut)
            code, code_strut = make_line(line_markup, font_size)
            place(code, code_strut, code_x, y)
            self.lines.add(code)
            self.code_struts.append(code_strut)
        self.group = VGroup(self.gutter, self.lines)


def code_panel(filename, source, lexer, x, top, width, height=None, first=1, tag=None,
               tag_color=DIM, max_scale=0.8, gutter=True):
    """Une fenêtre d'éditeur, haut en `top`, centrée en `x`, et son code.

    Sans `height`, la fenêtre prend la hauteur de son code. `gutter=False` masque les
    numéros de ligne : pour un extrait raccourci, de vrais numéros mentiraient.
    Renvoie (panneau, vue, groupe affichable)."""
    view = Excerpt(source, [lexer], first)
    gutter_w = view.code_struts[0].get_left()[0] - view.gutter_struts[0].get_left()[0]
    w, h = view.size
    if not gutter:
        w -= gutter_w
    code_w = width - 0.64
    if height is None:
        height = h * min(max_scale, code_w / w) + 1.1
    panel = EditorPanel(filename, [x, top - height / 2, 0], width, height, tag, tag_color)
    scale = min(max_scale, panel.code_w / w, panel.code_h / h)
    if scale < 0.58:
        print(f"[ep12] {filename} : code petit (échelle {scale:.2f})", file=sys.stderr)
    view.fit(scale, panel.code_top_left())
    if not gutter:
        view.gutter.set_opacity(0)
        view.lines.shift(gutter_w * scale * LEFT)
    return panel, view, VGroup(panel.chrome, view.group)


def http_pill(method, path, color=BLUE, size=18):
    m = label(method, size, BG, font=MONO_FONT, bold=True)
    m_bg = RoundedRectangle(width=m.get_width() + 0.24, height=0.36, corner_radius=0.08)
    m_bg.set_fill(color, 1).set_stroke(width=0)
    m.move_to(m_bg)
    p = label(path, size, TXT, font=MONO_FONT)
    row = VGroup(VGroup(m_bg, m), p).arrange(RIGHT, buff=0.2)
    bg = RoundedRectangle(width=row.get_width() + 0.3, height=0.56, corner_radius=0.12)
    bg.set_fill(PANEL_BG, 1).set_stroke(color, 1.5).move_to(row)
    return VGroup(bg, row)


def badge(text, color, size=18):
    t = label(text, size, color, font=MONO_FONT, bold=True)
    bg = RoundedRectangle(width=t.get_width() + 0.4, height=t.get_height() + 0.26, corner_radius=0.1)
    bg.set_fill(color, 0.15).set_stroke(color, 1.5)
    t.move_to(bg)
    return VGroup(bg, t)


def caption(text, point, color=DIM, size=16):
    return fit_x(label(text, size, color).move_to(point))


def cross_at(point, size=30):
    return label("✖", size, ERROR, bold=True).move_to(point)


# ---------------------------------------------------------------------------
# Extraits (copiés du dépôt, raccourcis par « … »)
# ---------------------------------------------------------------------------

YAML_PARAMS = """\
parameters:
  - name: page
    in: query
    schema:
      type: integer
      minimum: 1
      default: 1
  - name: limit
    in: query
    schema:
      type: integer
      minimum: 1
      maximum: 100
      default: 20
  - name: role
    …"""

CONTROLEUR_LISTER = """\
async lister({ request }: HttpContext) {
  const { page, limit, role } = request.qs()
  return utilisateursService.lister({ page, limit, role })
}"""

VALIDATEUR_QUERY = """return this.#souple.compile(
  prefixerRefs({
    type: 'object',
    // Strict volontairement : un `?limite=5` au lieu de `?limit=5` doit
    // échouer bruyamment plutôt que d'être ignoré en silence.
    additionalProperties: false,
    …"""

REPONSE_LIMITE = """{
  "code": "VALIDATION_ERROR",
  "message": "La requête ne respecte pas le contrat de l'API.",
  "details": [{
    "path": "/limite",
    "message": "must NOT have additional properties"
  }]
}"""

CORPS_ROLE = """\
{
  "email": "ambitieux@calanques.fr",
  "nom": "Ambitieux",
  "password": "motdepasse1",
  "role": "administrateur"
}"""

YAML_CREATION = """\
type: object
additionalProperties: false
required:
  - email
  - nom
  - password
properties:
  email: …
  nom: …
  password: …"""

REPONSE_ROLE = """{
  "code": "VALIDATION_ERROR",
  "message": "La requête ne respecte pas le contrat de l'API.",
  "details": [{
    "path": "/role",
    "message": "must NOT have additional properties"
  }]
}"""

SERVICE_AVANT = """\
        await utilisateur.refresh()

        return versContrat(utilisateur)
      })"""

SERVICE_APRES = """\
        await utilisateur.refresh()

        return {
          ...versContrat(utilisateur),
          password: utilisateur.password, // « pour déboguer »
        }
      })"""

YAML_UTILISATEUR = """\
type: object
additionalProperties: false
required: …
properties:
  id: …
  email: …
  nom: …
  role: …
  createdAt: …"""

REPONSE_500 = """{
  "code": "CONTRACT_RESPONSE_VIOLATION",
  "message": "La réponse de creerUtilisateur …",
  "details": [{
    "path": "/password",
    "message": "must NOT have additional properties"
  }]
}"""

MIDDLEWARE_SORTIE = """\
} catch (erreur) {
  if (!(erreur instanceof ViolationDeContrat)) throw erreur

  ctx.logger.error(
    { operationId, status: …, details: erreur.details },
    'Réponse non conforme au contrat'
  )

  if (app.inProduction) return

  return this.#repondreEnErreur(ctx, 500, {
    code: 'CONTRACT_RESPONSE_VIOLATION',
    …"""

JOURNAL = """\
level: 50 (error)
msg: "Réponse non conforme au contrat"
operationId: "creerUtilisateur"
status: 201
details: [{ path: "/password", … }]"""


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------


class Ep12ContratDeuxSens(EpisodeScene):
    EPISODE = "12"
    TITLE = "Le contrat dans les deux sens"

    def construct(self):
        self.deux_sens()
        self.cas_query()
        self.cas_corps()
        self.cas_reponse()
        self.cas_production()
        self.encart_handler()
        self.retenir()

    # --- 0. Un gardien, deux sens -----------------------------------------------

    def deux_sens(self):
        self.show_chip("Un gardien, deux sens")

        client = node("client", "web, mobile, test", BLUE, width=2.3, height=2.6)
        client.move_to([-5.2, -0.45, 0])
        metier = node("contrôleur", "puis service, Lucid", VIOLET, width=2.5, height=2.6)
        metier.move_to([5.1, -0.45, 0])

        gate = RoundedRectangle(width=3.0, height=3.4, corner_radius=0.16)
        gate.set_fill(ACCENT, 0.08).set_stroke(ACCENT, 2.2).move_to([0, -0.45, 0])
        g_title = label("contract()", 24, ACCENT, font=MONO_FONT, bold=True)
        g_title.move_to(gate.get_top() + 0.38 * DOWN)
        sep = DashedLine([-1.4, -0.6, 0], [1.4, -0.6, 0], dash_length=0.08)
        sep.set_stroke(ACCENT, 1.2, opacity=0.6)
        top_txt = VGroup(label("entrée", 20, TXT, bold=True),
                         label("params · query · body", 15, DIM)).arrange(DOWN, buff=0.06)
        top_txt.move_to([0, 0.2, 0])
        bot_txt = VGroup(label("sortie", 20, TXT, bold=True),
                         label("la réponse", 15, DIM)).arrange(DOWN, buff=0.06)
        bot_txt.move_to([0, -1.4, 0])
        gate_group = VGroup(gate, g_title, sep, top_txt, bot_txt)

        y_in, y_out = 0.2, -1.4
        p_in = [np.array([client.get_right()[0], y_in, 0]), np.array([metier.get_left()[0], y_in, 0])]
        p_out = [np.array([metier.get_left()[0], y_out, 0]), np.array([client.get_right()[0], y_out, 0])]
        lane_in = VGroup(
            link(p_in[0], np.array([gate.get_left()[0], y_in, 0]), BLUE),
            link(np.array([gate.get_right()[0], y_in, 0]), p_in[1], BLUE),
        )
        lane_out = VGroup(
            link(p_out[0], np.array([gate.get_right()[0], y_out, 0]), ACCENT),
            link(np.array([gate.get_left()[0], y_out, 0]), p_out[1], ACCENT),
        )

        self.play(FadeIn(client), FadeIn(metier), run_time=0.7)
        self.play(FadeIn(gate_group, scale=0.95), run_time=0.8)
        self.play(*[GrowArrow(a) for a in lane_in], run_time=0.6)
        go = packet(BLUE, 0.09).move_to(p_in[0])
        self.add(go)
        self.play(go.animate.move_to(p_in[1]), run_time=1.4, rate_func=linear)
        self.remove(go)
        self.play(*[GrowArrow(a) for a in lane_out], run_time=0.6)
        back = packet(ACCENT, 0.09).move_to(p_out[0])
        self.add(back)
        self.play(back.animate.move_to(p_out[1]), run_time=1.4, rate_func=linear)
        self.remove(back)

        e400 = badge("400 · faute du client", WARN, 17).move_to([-2.65, y_in + 0.6, 0])
        e500 = badge("500 · bug du serveur", ERROR, 17).move_to([-2.65, y_out - 0.6, 0])
        self.play(FadeIn(e400, shift=0.1 * UP), run_time=0.5)
        self.wait(1.2)
        self.play(FadeIn(e500, shift=0.1 * DOWN), run_time=0.5)
        self.wait(1.2)

        route = markup(
            f'<span foreground="{DIM}">la route lui passe son operationId :  </span>'
            f'<span foreground="{TXT}">.use(middleware.contract({{ operationId: </span>'
            f'<span foreground="{GOLD}">\'creerUtilisateur\'</span>'
            f'<span foreground="{TXT}"> }}))</span>',
            size=18, font=MONO_FONT,
        )
        route.move_to([0, 2.15, 0])
        fit_x(route)
        self.play(FadeIn(route, shift=0.1 * DOWN), run_time=0.6)
        self.wait(3.0)
        self.clear_stage()

    # --- A. La query est normalisée ---------------------------------------------

    def cas_query(self):
        self.show_chip("A · La query : le YAML s'exécute", BLUE)

        _, yv, yaml_panel = code_panel(
            "contract/…/paths/utilisateurs.yaml", YAML_PARAMS, "yaml",
            -3.6, 2.5, 6.4, tag="contrat", tag_color=ACCENT, max_scale=0.8, gutter=False,
        )
        self.play(FadeIn(yaml_panel), run_time=0.7)

        pill = http_pill("GET", "/api/v1/utilisateurs?page=2").move_to([3.65, 2.2, 0])
        self.play(FadeIn(pill, shift=0.15 * LEFT), run_time=0.6)

        recu = markup(
            f'<span foreground="{DIM}">reçu   </span>'
            f'<span foreground="{TXT}">{{ page: </span><span foreground="{GOLD}">"2"</span>'
            f'<span foreground="{TXT}"> }}</span>',
            size=22, font=MONO_FONT,
        ).move_to([3.65, 1.35, 0])
        recu_note = caption("une query arrive toujours en chaînes", [3.65, 0.95, 0], DIM, 15)
        self.play(FadeIn(recu), FadeIn(recu_note), run_time=0.6)
        self.wait(0.8)

        arrow = Arrow([2.3, 0.7, 0], [2.3, -0.2, 0], buff=0.05, thickness=2.5).set_color(ACCENT)
        ajv = VGroup(label("Ajv « souple »", 16, ACCENT, bold=True),
                     label("coerceTypes + useDefaults", 15, ACCENT)).arrange(DOWN, aligned_edge=LEFT,
                                                                             buff=0.06)
        ajv.next_to(arrow, RIGHT, buff=0.2)
        normal = markup(
            f'<span foreground="{DIM}">après  </span>'
            f'<span foreground="{TXT}">{{ page: </span><span foreground="#AE81FF">2</span>'
            f'<span foreground="{TXT}">, limit: </span><span foreground="#AE81FF">20</span>'
            f'<span foreground="{TXT}"> }}</span>',
            size=22, font=MONO_FONT,
        ).move_to([3.65, -0.5, 0])
        self.play(GrowArrow(arrow), FadeIn(ajv), run_time=0.7)
        self.play(flash(yv.word_boxes(5), ACCENT, 0.25), run_time=0.75)
        type_hl = highlight_rect(yv.line_box(5), ACCENT)
        self.play(FadeIn(type_hl), run_time=0.3)
        default_hl = highlight_rect(yv.line_box(14), GOLD)
        self.play(FadeIn(normal, shift=0.1 * DOWN), FadeIn(default_hl), run_time=0.7)
        cap2 = caption("2 devient un nombre, limit reçoit son défaut", [3.65, -0.9, 0], TXT, 15)
        self.play(FadeIn(cap2), run_time=0.5)
        self.wait(2.2)

        _, _, ctrl = code_panel(
            "app/controllers/utilisateurs_controller.ts", CONTROLEUR_LISTER, "typescript",
            3.65, -1.3, 6.5, max_scale=0.7, gutter=False,
        )
        ctrl_note = caption("le contrôleur lit des nombres, défauts compris : rien à redéclarer",
                            [3.6, -3.65, 0], TXT, 15)
        self.play(FadeIn(ctrl, shift=0.1 * UP), run_time=0.6)
        self.play(FadeIn(ctrl_note), run_time=0.5)
        self.wait(2.4)

        # Une faute de frappe dans la query
        right = VGroup(recu, recu_note, arrow, ajv, normal, cap2, ctrl, ctrl_note)
        pill2 = http_pill("GET", "/api/v1/utilisateurs?limite=5").move_to(pill)
        _, vv, valid_panel = code_panel(
            "app/services/contract_validator.ts", VALIDATEUR_QUERY, "typescript",
            -3.6, 2.5, 6.4, tag="serveur", tag_color=VIOLET, max_scale=0.8, gutter=False,
        )
        self.play(FadeOut(right), FadeOut(type_hl), FadeOut(default_hl),
                  FadeTransform(pill, pill2), run_time=0.7)
        typo = caption("une faute de frappe : « limite » au lieu de « limit »",
                       [3.65, 1.55, 0], DIM, 15)
        self.play(FadeIn(typo), run_time=0.5)
        self.play(FadeOut(yaml_panel), FadeIn(valid_panel), run_time=0.8)
        strict_hl = highlight_rect(vv.line_box(6), WARN)
        self.play(flash(vv.word_boxes(4)[:7], WARN, 0.15), run_time=1.05)
        self.play(FadeIn(strict_hl), run_time=0.4)
        left_note = caption("un paramètre inconnu n'est pas ignoré : il est refusé",
                            [-3.6, valid_panel.get_bottom()[1] - 0.4, 0], TXT, 15)
        self.play(FadeIn(left_note), run_time=0.5)
        self.wait(1.2)

        _, _, rep = code_panel(
            "réponse  ·  400", REPONSE_LIMITE, "json", 3.65, 0.6, 6.8,
            tag="contrôleur non appelé", tag_color=WARN, max_scale=0.7,
        )
        b400 = badge("400 VALIDATION_ERROR", WARN).move_to([3.65, 1.05, 0])
        self.play(FadeOut(typo), FadeIn(b400, scale=1.2), run_time=0.5)
        self.play(FadeIn(rep, shift=0.1 * UP), run_time=0.7)
        test_ref = caption("c'est le test « EXG-USR-001 — les bornes du contrat sont appliquées »",
                           [3.65, rep.get_bottom()[1] - 0.4, 0], DIM, 15)
        self.play(FadeIn(test_ref), run_time=0.5)
        self.wait(3.5)
        self.clear_stage()

    # --- B. Le corps est refusé : EXG-USR-004 -----------------------------------

    def cas_corps(self):
        self.show_chip("B · Le corps : un rôle à l'inscription", WARN)

        pill = http_pill("POST", "/api/v1/utilisateurs").move_to([-3.6, 2.3, 0])
        _, bv, body = code_panel(
            "corps de la requête", CORPS_ROLE, "json", -3.6, 1.85, 6.4,
            tag="client", tag_color=BLUE, max_scale=0.75,
        )
        _, cv, yaml_panel = code_panel(
            "contract/…/schemas/CreationUtilisateur.yaml", YAML_CREATION, "yaml",
            3.65, 2.55, 6.3, tag="contrat", tag_color=ACCENT, max_scale=0.72, gutter=False,
        )
        self.play(FadeIn(pill, shift=0.15 * RIGHT), FadeIn(body), run_time=0.8)
        self.wait(0.6)
        self.play(FadeIn(yaml_panel), run_time=0.6)

        role_hl = highlight_rect(bv.line_box(5), ERROR)
        addl_hl = highlight_rect(cv.line_box(2), WARN)
        props_box = SurroundingRectangle(
            VGroup(*[highlight_rect(cv.line_box(i), DIM) for i in (8, 9, 10)]), buff=0.04,
        ).set_stroke(DIM, 1.5)
        no_role = label("pas de « role » ici", 17, ERROR).next_to(props_box, RIGHT, buff=0.4)
        fit_x(no_role)
        self.play(FadeIn(role_hl), run_time=0.4)
        self.wait(0.6)
        self.play(ShowCreation(props_box), FadeIn(no_role), run_time=0.6)
        self.wait(0.6)
        self.play(FadeIn(addl_hl), run_time=0.4)
        self.wait(1.6)

        _, _, rep = code_panel(
            "réponse  ·  400", REPONSE_ROLE, "json", -3.6, -0.75, 6.4, max_scale=0.7,
        )
        self.play(FadeIn(rep, shift=0.1 * UP), run_time=0.7)
        self.wait(1.8)

        # Le contrôleur n'est jamais atteint
        gate = node("contract()", "entrée", ACCENT, width=2.1, title_size=18, subtitle_size=13)
        gate.move_to([1.85, -1.75, 0])
        ctrl = node("creer()", "contrôleur", VIOLET, width=2.1, title_size=18, subtitle_size=13)
        ctrl.move_to([5.55, -1.75, 0])
        arr = link(edge_point(gate, RIGHT), edge_point(ctrl, LEFT), DIM)
        x = cross_at(arr.get_center(), 28)
        self.play(FadeIn(gate), FadeIn(ctrl), GrowArrow(arr), run_time=0.6)
        self.play(FadeIn(x, scale=1.6), ctrl.animate.set_opacity(0.35), run_time=0.5)
        never = caption("jamais atteint : aucune ligne de métier ne s'exécute",
                        [3.7, -2.7, 0], TXT, 16)
        exg = badge("EXG-USR-004 · pas d'escalade de privilège", ACCENT, 15).move_to([3.7, -3.3, 0])
        self.play(FadeIn(never), run_time=0.5)
        self.play(FadeIn(exg), run_time=0.5)
        self.wait(3.5)
        self.clear_stage()

    # --- C. La réponse est refusée : un bug du serveur ---------------------------

    def cas_reponse(self):
        self.show_chip("C · La réponse : un bug du serveur", ERROR)

        height = 6 * 0.2932 * 0.66 + 1.1     # même fenêtre avant et après
        _, sv, service = code_panel(
            "app/services/utilisateurs_service.ts", SERVICE_AVANT, "typescript",
            -3.6, 2.5, 6.6, height=height, first=160, tag="creer()", max_scale=0.66,
        )
        _, uv, yaml_panel = code_panel(
            "contract/…/schemas/Utilisateur.yaml", YAML_UTILISATEUR, "yaml",
            3.75, 2.5, 6.2, tag="contrat", tag_color=ACCENT, max_scale=0.7, gutter=False,
        )
        self.play(FadeIn(service), run_time=0.6)
        ok_hl = highlight_rect(sv.line_box(3), ACCENT)
        ok_cap = caption("la projection unique, champ par champ (épisode 11)",
                         [-3.6, service.get_bottom()[1] - 0.35, 0], DIM, 15)
        self.play(FadeIn(ok_hl), FadeIn(ok_cap), run_time=0.5)
        self.wait(1.4)

        # Quelqu'un « ajoute un champ pour déboguer » (illustration)
        _, sv2, service2 = code_panel(
            "app/services/utilisateurs_service.ts", SERVICE_APRES, "typescript",
            -3.6, 2.5, 6.6, height=height, first=160, tag="creer()  ·  modifié", tag_color=ERROR,
            max_scale=0.66,
        )
        self.play(FadeOut(ok_hl), FadeOut(ok_cap), FadeTransform(service, service2), run_time=0.9)
        bad_hl = highlight_rect(sv2.line_box(5), ERROR)
        bad_cap = caption("illustration : on expose un champ que le contrat ne déclare pas",
                          [-3.6, service2.get_bottom()[1] - 0.35, 0], ERROR, 15)
        self.play(FadeIn(bad_hl), FadeIn(bad_cap), run_time=0.5)
        self.wait(1.2)
        self.play(FadeIn(yaml_panel), run_time=0.6)
        addl = highlight_rect(uv.line_box(2), WARN)
        self.play(FadeIn(addl), run_time=0.4)
        self.wait(1.0)

        _, _, rep = code_panel(
            "réponse  ·  500", REPONSE_500, "json", -3.6, -0.6, 6.6,
            tag="le hash ne sort pas", tag_color=ACCENT, max_scale=0.68,
        )
        b500 = badge("500 CONTRACT_RESPONSE_VIOLATION", ERROR, 17).move_to([3.75, -0.95, 0])
        self.play(FadeIn(b500, scale=1.2), run_time=0.5)
        self.play(FadeIn(rep, shift=0.1 * UP), run_time=0.7)
        full = VGroup(
            label("« La réponse de creerUtilisateur ne respecte", 16, TXT),
            label("pas le contrat. C'est un bug du serveur,", 16, TXT),
            label("pas de l'appelant. »", 16, TXT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).move_to([3.75, -1.95, 0])
        dev = VGroup(
            label("en dev et en test : on BLOQUE,", 16, GOLD, bold=True),
            label("le développeur le voit tout de suite", 16, GOLD),
        ).arrange(DOWN, buff=0.08).move_to([3.75, -3.15, 0])
        self.play(FadeIn(full), run_time=0.6)
        self.wait(1.8)
        self.play(FadeIn(dev), run_time=0.5)
        self.wait(3.5)
        self.clear_stage()

    # --- D. En production : journaliser sans bloquer -----------------------------

    def cas_production(self):
        self.show_chip("D · En production : on journalise", GOLD)

        _, mv, mid = code_panel(
            "app/middleware/contract_middleware.ts", MIDDLEWARE_SORTIE, "typescript",
            -3.55, 2.5, 6.8, max_scale=0.72, gutter=False,
        )
        self.play(FadeIn(mid), run_time=0.7)

        log_hl = highlight_rect(mv.line_box(4), GOLD)
        prod_hl = highlight_rect(mv.line_box(9), GOLD)
        self.play(FadeIn(log_hl), run_time=0.4)

        _, _, journal = code_panel(
            "journal du serveur", JOURNAL, "yaml", 3.65, 2.5, 6.4,
            tag="schématique", max_scale=0.72,
        )
        self.play(FadeIn(journal, shift=0.1 * LEFT), run_time=0.6)
        self.wait(1.2)
        self.play(FadeIn(prod_hl), run_time=0.4)

        lanes = VGroup(
            VGroup(label("dev / test", 18, TXT, bold=True),
                   label("→", 18, DIM), badge("500", ERROR, 16),
                   label("bloqué", 17, DIM)).arrange(RIGHT, buff=0.2),
            VGroup(label("production", 18, GOLD, bold=True),
                   label("→", 18, DIM), badge("201", ACCENT, 16),
                   label("la réponse part telle quelle", 17, DIM)).arrange(RIGHT, buff=0.2),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        lanes.move_to([3.65, journal.get_bottom()[1] - 1.0, 0])
        fit_x(lanes)
        self.play(LaggedStartMap(FadeIn, lanes, shift=0.1 * RIGHT, lag_ratio=0.5), run_time=1.0)
        self.wait(1.6)

        quote = VGroup(
            label("« Transformer la réponse d'un utilisateur en 500 à cause", 15, DIM),
            label("d'un champ en trop ferait plus de dégâts que le défaut", 15, DIM),
            label("lui-même ; l'alerte part dans les logs, le trafic continue. »", 15, DIM),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        quote.move_to([-3.55, mid.get_bottom()[1] - 0.75, 0])
        fit_x(quote)
        why = VGroup(
            label("Le champ en trop sortirait donc en production :", 16, TXT),
            label("c'est pour ça qu'on bloque en dev et en test.", 16, GOLD, bold=True),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        why.move_to([3.65, lanes.get_bottom()[1] - 0.75, 0])
        fit_x(why)
        self.play(FadeIn(quote), run_time=0.6)
        self.wait(1.2)
        self.play(FadeIn(why), run_time=0.6)
        self.wait(3.5)
        self.clear_stage()

    # --- Encart : ce qui ne passe pas par la validation ---------------------------

    def encart_handler(self):
        self.show_chip("Encart : 403 et 409 passent par le handler", VIOLET)

        y_top, y_bot = 1.0, -1.35
        client = node("client", None, BLUE, width=2.0)
        client.move_to([-5.0, y_top, 0])
        gate = node("contract()", "sortie", ACCENT, width=2.4)
        gate.move_to([-0.6, y_top, 0])
        service = node("service", "createError(…, 409)", VIOLET, width=3.0)
        service.move_to([4.4, y_top, 0])
        handler = node("handler.ts", "exceptions", GOLD, width=2.6)
        handler.move_to([-0.6, y_bot, 0])

        normal = VGroup(
            link(edge_point(service, LEFT), edge_point(gate, RIGHT), DIM, planned=True),
            link(edge_point(gate, LEFT), edge_point(client, RIGHT), DIM, planned=True),
        )
        normal_cap = caption("une réponse normale : validée", [1.9, y_top + 0.85, 0], DIM, 15)
        self.play(FadeIn(client), FadeIn(gate), FadeIn(service), run_time=0.7)
        self.play(*[ShowCreation(a) for a in normal], FadeIn(normal_cap), run_time=0.8)
        self.wait(0.8)

        # L'exception saute par-dessus la validation de sortie
        s_bottom = edge_point(service, DOWN)
        h_right = edge_point(handler, RIGHT)
        jump_pts = [s_bottom, [s_bottom[0], y_bot, 0], h_right + 0.1 * RIGHT]
        jump = VMobject().set_points_as_corners([np.array(p) for p in jump_pts]).set_stroke(ERROR, 2.5)
        jump_tip = ArrowTip().set_fill(ERROR, 1).set_stroke(width=0).scale(0.6).rotate(PI)
        jump_tip.move_to(h_right + 0.1 * RIGHT + jump_tip.get_width() / 2 * RIGHT)
        exc = label("409 EMAIL_ALREADY_USED, 403 …", 15, ERROR, font=MONO_FONT)
        exc.move_to([2.5, y_bot + 0.3, 0])
        self.play(ShowCreation(jump), FadeIn(handler), run_time=0.9)
        self.play(FadeIn(jump_tip), FadeIn(exc), run_time=0.4)
        skip = caption("contract() ne voit pas l'exception", [-0.6, y_top - 0.75, 0], TXT, 15)
        self.play(gate.animate.set_opacity(0.35), FadeIn(skip), run_time=0.6)

        c_bottom = edge_point(client, DOWN)
        h_left = edge_point(handler, LEFT)
        out_pts = [h_left, [c_bottom[0], y_bot, 0], c_bottom + 0.1 * DOWN]
        out = VMobject().set_points_as_corners([np.array(p) for p in out_pts]).set_stroke(GOLD, 2.5)
        out_tip = ArrowTip().set_fill(GOLD, 1).set_stroke(width=0).scale(0.6).rotate(PI / 2)
        out_tip.move_to(c_bottom + 0.1 * DOWN + out_tip.get_height() / 2 * DOWN)
        shape = label("{ code, message }", 18, GOLD, font=MONO_FONT)
        shape.move_to([-3.0, y_bot + 0.3, 0])
        self.play(ShowCreation(out), run_time=0.7)
        self.play(FadeIn(out_tip), FadeIn(shape), run_time=0.4)
        note = VGroup(
            label("La forme de ces erreurs n'est garantie que par handler.ts et les tests fonctionnels.",
                  16, TXT),
            label("Une réponse ≥ 500 n'est jamais validée non plus : on gère déjà une panne.", 15, DIM),
        ).arrange(DOWN, buff=0.14).move_to([0, -2.85, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.wait(3.8)
        self.clear_stage()

    # --- À retenir ---------------------------------------------------------------

    def retenir(self):
        self.show_chip("À retenir")
        rows = [
            ("entrée", "params, query, body", "400 VALIDATION_ERROR", "faute du client", WARN),
            ("sortie", "la réponse", "500 CONTRACT_RESPONSE_VIOLATION", "bug du serveur", ERROR),
            ("en prod", "réponse non conforme", "logger.error", "la réponse part", GOLD),
        ]
        table = VGroup()
        for sens, quoi, code, qui, color in rows:
            table.add(VGroup(
                label(sens, 22, color, font=MONO_FONT, bold=True),
                label(quoi, 18, DIM),
                label(code, 18, color, font=MONO_FONT),
                label(qui, 19, TXT),
            ))
        widths = [max(r[i].get_width() for r in table) for i in range(4)]
        for k, row in enumerate(table):
            x = 0
            for i, cell in enumerate(row):
                cell.move_to([x + cell.get_width() / 2, -k * 0.8, 0])
                x += widths[i] + 0.55
        table.move_to([0, 1.0, 0])
        self.play(LaggedStartMap(FadeIn, table, shift=0.1 * RIGHT, lag_ratio=0.35), run_time=1.6)
        self.wait(1.4)

        ajv = VGroup(
            label("Les messages d'Ajv sortent en anglais, tels quels :", 17, DIM),
            label("must NOT have additional properties", 19, TXT, font=MONO_FONT),
            label("alors que le contrat promet du français : point ouvert, à trancher.", 17, DIM),
        ).arrange(DOWN, buff=0.14).move_to([0, -1.55, 0])
        self.play(FadeIn(ajv), run_time=0.7)
        next_ep = label("épisode suivant : les tests Japa  →", 16, DIM)
        next_ep.to_corner(DR, buff=0.4)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(3.5)
