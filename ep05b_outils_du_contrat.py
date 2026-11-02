"""
Épisode 5b — Les cinq outils du contrat, au travail sur un vrai YAML

Même principe que Prettier vs ESLint : un carré flashe sur le vrai fichier,
et on voit ce que chaque outil en fait. L'ordre est celui de `npm run sync`,
puis l'exécution :
  0. Les cinq outils et leur moment (génération ou exécution).
  1. Redocly assemble : les $ref de connexion.yaml sont suivis (même en
     cascade) et rangés dans un seul dist/openapi.json.
  2. Spectral relit : une déconnexion copiée-collée garde l'operationId de la
     connexion et un tag mal orthographié. Une error, un warning ; on corrige.
  3. Orval écrit le SDK : l'operationId nomme la fonction, le hook et le mock ;
     les schémas deviennent des interfaces.
  4. openapi-typescript écrit les types du serveur : `jeton:` au lieu de
     `token:` ne compile pas.
  5. Ajv contrôle à l'exécution : une requête fautive est refusée en 400 avant
     le contrôleur, avec un détail par champ.
  6. Récapitulatif.

Sources : contract/package.json, contract/.spectral.yaml, contract/openapi.yaml,
contract/features/session/**, contract/features/_shared/**, package.json (sync),
sdk/orval.config.ts, sdk/src/msw.ts, server/package.json (sync:contract),
server/app/services/session_service.ts, server/app/services/contract_validator.ts,
server/app/middleware/contract_middleware.ts.

Illustratif (pas copié d'une vraie sortie) : les numéros de ligne de Spectral,
le scénario de copier-coller, la faute `jeton:`, la requête fautive, et la
mise en forme condensée du code généré par Orval.

Rendu vidéo :  manimgl ep05b_outils_du_contrat.py Ep05bOutilsDuContrat -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


PINK = "#F07EB0"          # Spectral
PER_WORD = 0.035
PER_LINE = 0.12
CAPTION_Y = -3.6


# ---------------------------------------------------------------------------
# Les fichiers montrés à l'écran
# ---------------------------------------------------------------------------

CONNEXION = """\
post:
  summary: Ouvrir une session
  operationId: seConnecter
  tags:
    - Session
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: '../schemas/Identifiants.yaml'
  responses:
    '200':
      description: Session ouverte.
      content:
        application/json:
          schema:
            $ref: '../schemas/Session.yaml'
    '400':
      $ref: '../../_shared/responses/BadRequest.yaml'
    '401':
      $ref: '../../_shared/responses/Unauthorized.yaml'"""

BUNDLE = """\
{
  "openapi": "3.1.0",
  "paths": {
    "/session/connexion": {
      "post": {
        "summary": "Ouvrir une session",
        "operationId": "seConnecter",
        "tags": ["Session"],
        "requestBody": {… "#/components/schemas/Identifiants"},
        "responses": {
          "200": {… "#/components/schemas/Session"},
          "400": {"$ref": "#/components/responses/BadRequest"},
          "401": {"$ref": "#/components/responses/Unauthorized"}
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Identifiants": {"type": "object", …},
      "Session": {"type": "object", …},
      "Utilisateur": {"type": "object", …},
      "Role": {"type": "string", "enum": […]},
      "ApiError": {"type": "object", …}
    },
    "responses": {
      "BadRequest": {…},
      "Unauthorized": {…}
    }
  }
}"""

DECONNEXION_FAUTIF = """\
post:
  summary: Fermer la session courante
  operationId: seConnecter
  tags:
    - Sessions
  security:
    - bearerAuth: []
  responses:
    '204':
      description: Session fermée.
    '401':
      $ref: '../../_shared/responses/Unauthorized.yaml'"""

DECONNEXION = (DECONNEXION_FAUTIF
               .replace("operationId: seConnecter", "operationId: seDeconnecter")
               .replace("- Sessions", "- Session"))

SPECTRAL_CONFIG = """\
extends:
  - "spectral:oas\""""

CONNEXION_COURT = """\
post:
  operationId: seConnecter
  tags:
    - Session
  requestBody:
    content: … schema:
      $ref: '../schemas/Identifiants.yaml'
  responses:
    '200':
      content: … schema:
        $ref: '../schemas/Session.yaml'"""

ORVAL_MODEL = """\
export interface Identifiants {
  email: string;
  /** @minLength 1 */
  password: string;
}"""

ORVAL_ENDPOINT = """\
export const seConnecter = (identifiants: Identifiants, signal?: AbortSignal) =>
  customInstance<Session>({ url: `/session/connexion`, method: 'POST',
    data: identifiants, signal });

export const useSeConnecter = (options?) => useMutation(…);"""

ORVAL_MSW = """\
export const getSeConnecterResponseMock = (): Session => ({
  utilisateur: { id: faker.string.uuid(), … }, token: faker.string.alpha(20) });

export const getSeConnecterMockHandler = (override?) =>
  http.post('*/session/connexion', … getSeConnecterResponseMock());"""

USAGE = """\
const connexion = useSeConnecter()
connexion.mutate({ data: { email, password } })"""

SESSION_SCHEMA = """\
type: object
additionalProperties: false
required:
  - utilisateur
  - token
properties:
  utilisateur:
    $ref: '../../utilisateurs/schemas/Utilisateur.yaml'
  token:
    type: string
    description: Jeton d'accès opaque, …"""

TYPES_TS = """\
export interface components {
    schemas: {
        Session: {
            utilisateur: components["schemas"]["Utilisateur"];
            /** @description Jeton d'accès opaque, … */
            token: string;
        };
    };
}"""

SERVICE_FAUTIF = """\
type Session = components['schemas']['Session']
async seConnecter(identifiants: …): Promise<Session> {
  const jeton = await Utilisateur.accessTokens.create(utilisateur)
  return {
    utilisateur: versContrat(utilisateur),
    jeton: jeton.value!.release(),
  }"""

SERVICE = SERVICE_FAUTIF.replace("    jeton: jeton", "    token: jeton")

IDENTIFIANTS = """\
type: object
additionalProperties: false
required:
  - email
  - password
properties:
  email:
    type: string
    format: email
  password:
    type: string
    minLength: 1"""

REQUETE = """\
{
  "email": "lea.cmc.fr",
  "password": "",
  "role": "administrateur"
}"""

REPONSE_400 = """\
{
  "code": "VALIDATION_ERROR",
  "message": "La requête ne respecte pas le contrat de l'API.",
  "details": [
    { "path": "/email", "message": "must match format \\"email\\"" },
    { "path": "/password", "message": "must NOT have fewer than 1 characters" },
    { "path": "/role", "message": "must NOT have additional properties" }
  ]
}"""


# ---------------------------------------------------------------------------
# Petits outils
# ---------------------------------------------------------------------------

def sp(text, color=TXT):
    return f'<span foreground="{color}">{escape(text, quote=False)}</span>'


def row(*segments):
    """Une ligne de console : (texte, couleur), ... -> (texte brut, markup)."""
    return "".join(t for t, _ in segments), "".join(sp(t, c) for t, c in segments)


class TermView(CodeView):
    """Comme CodeView, mais les lignes sont colorées à la main (sortie de console)."""

    def __init__(self, rows, font_size=BASE_FS):
        cal = MarkupText(STRUT * 20, font=CODE_FONT, font_size=font_size)
        self.adv = cal.get_width() / 20
        self.block_h = cal.get_height()
        self.line_h = self.block_h * LINE_SPACING
        self.text = [plain for plain, _ in rows]
        self.gutter, self.lines = VGroup(), VGroup()
        self.gutter_struts, self.code_struts = [], []
        for i, (_, mk) in enumerate(rows):
            line, strut = make_line(mk, font_size)
            place(line, strut, 0, -i * self.line_h)
            self.lines.add(line)
            self.code_struts.append(strut)
        self.group = VGroup(self.gutter, self.lines)


def panels(*specs, gutter=False, max_scale=1.6):
    """Plusieurs (EditorPanel, CodeView) ajustés à la MÊME taille de police."""
    built = []
    for filename, source, lexer, center, width, height, tag, tag_color in specs:
        panel = EditorPanel(filename, center, width=width, height=height, tag=tag,
                            tag_color=tag_color)
        view = source if isinstance(source, CodeView) else CodeView(source, [lexer], gutter=gutter)
        built.append((panel, view))
    scale = min([max_scale] + [min(p.code_w / v.size[0], p.code_h / v.size[1]) for p, v in built])
    for panel, view in built:
        view.fit(scale, panel.code_top_left())
    return built


def words(view, lines):
    return [b for ln in lines for b in view.word_boxes(ln)]


def squiggle(x0, x1, y, color, amp=0.022, period=0.14):
    n = max(16, int((x1 - x0) / period * 14))
    xs = np.linspace(x0, x1, n)
    wave = VMobject()
    wave.set_points_as_corners([np.array([x, y + amp * np.sin(TAU * (x - x0) / period), 0])
                                for x in xs])
    return wave.set_stroke(color, 2.2).set_fill(opacity=0)


def file_card(name, color):
    t = label(name, 13, color, font=MONO_FONT)
    bg = RoundedRectangle(width=t.get_width() + 0.3, height=t.get_height() + 0.22,
                          corner_radius=0.06)
    bg.set_fill(PANEL_BG, 1).set_stroke(color, 1.6)
    return VGroup(bg, t.move_to(bg))


def mark(symbol, color, view, line, size=18):
    m = label(symbol, size, color, bold=True)
    return m.move_to([view.group.get_right()[0] + 0.28, view.line_y(line), 0])


class Ep05bOutilsDuContrat(EpisodeScene):
    EPISODE = "05b"
    TITLE = "Les cinq outils du contrat"

    def construct(self):
        self.cap = None
        self.intro()
        self.redocly()
        self.spectral()
        self.orval()
        self.openapi_typescript()
        self.ajv()
        self.recap()

    # --- outils de mise en scène -------------------------------------------------

    def say(self, lines, pos=(0, CAPTION_Y), color=TXT, size=17, width=13.6):
        """Remplace la légende courante (une ou plusieurs lignes)."""
        if isinstance(lines, str):
            lines = [lines]
        new = VGroup(*[label(t, size, color if i == 0 else DIM) for i, t in enumerate(lines)])
        new.arrange(DOWN, buff=0.1)
        if new.get_width() > width:
            new.set_width(width)
        new.move_to([pos[0], pos[1], 0])
        fit_x(new)
        anims = [FadeIn(new, shift=0.08 * UP)]
        if self.cap is not None:
            anims.append(FadeOut(self.cap))
        self.play(*anims, run_time=0.5)
        self.cap = new

    def next_section(self):
        self.clear_stage()
        self.cap = None

    def reveal(self, view, lines, *extra, run_time=0.4):
        self.play(*[FadeIn(view.lines[i - 1], shift=0.06 * RIGHT) for i in lines], *extra,
                  run_time=run_time)

    def scan_words(self, view, lines, color):
        boxes = words(view, lines)
        if boxes:
            self.play(flash(boxes, color, PER_WORD))

    def scan_lines(self, view, lines, color):
        self.play(flash([view.line_box(ln) for ln in lines], color, PER_LINE))

    # --- 0. Les cinq outils ------------------------------------------------------

    def intro(self):
        self.show_chip("Cinq outils autour d'un fichier YAML")
        yaml = node("contract/*.yaml", "OpenAPI 3.1 · écrit à la main", ACCENT, width=3.6)
        yaml.move_to([0, 2.0, 0])
        tools = [
            ("Redocly", "assemble les fichiers", BLUE),
            ("Spectral", "relit le contrat", PINK),
            ("Orval", "écrit le SDK des fronts", GOLD),
            ("openapi-typescript", "écrit les types du serveur", VIOLET),
            ("Ajv", "contrôle chaque requête", ACCENT),
        ]
        xs = (-5.6, -2.8, 0.0, 2.8, 5.6)
        nodes, roles, arrows = VGroup(), VGroup(), VGroup()
        for x, (name, role, color) in zip(xs, tools):
            n = node(name, None, color, width=2.55, title_size=20).move_to([x, 0.15, 0])
            nodes.add(n)
            roles.add(label(role, 15, DIM).next_to(n, DOWN, buff=0.18))
            arrows.add(link(edge_point(yaml, DOWN), edge_point(n, UP), color, width=1.6))

        self.play(FadeIn(yaml, shift=0.1 * DOWN), run_time=0.6)
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.12),
                  LaggedStartMap(FadeIn, nodes, shift=0.1 * DOWN, lag_ratio=0.12), run_time=1.3)
        self.play(LaggedStartMap(FadeIn, roles, lag_ratio=0.12), run_time=0.9)

        def bracket(x0, x1, y, text, color):
            line = Line([x0, y, 0], [x1, y, 0]).set_stroke(color, 2)
            ends = VGroup(*[Line([x, y, 0], [x, y + 0.12, 0]).set_stroke(color, 2) for x in (x0, x1)])
            t = label(text, 16, color, bold=True).next_to(line, DOWN, buff=0.14)
            return VGroup(line, ends, t)

        sync = bracket(-6.85, 4.15, -1.25, "npm run sync : à la génération, dans cet ordre", TXT)
        run = bracket(4.35, 6.85, -1.25, "serveur lancé", ACCENT)
        self.play(FadeIn(sync), FadeIn(run), run_time=0.7)
        self.say(["on les regarde travailler, un par un, sur la vraie route de connexion",
                  "contract/features/session/paths/connexion.yaml"], pos=(0, -2.85))
        self.wait(3.0)
        self.next_section()

    # --- 1. Redocly : assembler ----------------------------------------------------

    def redocly(self):
        self.show_chip("1 · Redocly : assembler les fichiers", BLUE)
        (left, lv), (right, rv) = panels(
            ("contract/features/session/paths/connexion.yaml", CONNEXION, "yaml",
             np.array([-3.55, -0.3, 0]), 6.9, 5.8, "extrait", DIM),
            ("contract/dist/openapi.json", BUNDLE, "json",
             np.array([3.55, -0.3, 0]), 6.9, 5.8, "généré · extrait", BLUE),
        )
        self.play(FadeIn(left.chrome), FadeIn(lv.group), FadeIn(right.chrome), run_time=0.8)
        # Le squelette vient d'openapi.yaml lui-même
        self.reveal(rv, [1, 2, 3, 17, 18, 19, 25, 26, 29, 30, 31], run_time=0.6)
        self.say(["redocly bundle part de openapi.yaml et suit chaque $ref, fichier après fichier",
                  "commande : npm run bundle  (dans contract/)"])
        self.wait(1.0)

        # openapi.yaml renvoie vers connexion.yaml : le fichier entier entre dans "paths"
        self.fly(file_card("connexion.yaml", BLUE), left.chrome[2].get_center(),
                 rv.lines[3].get_center())
        self.reveal(rv, [4, 5, 15, 16])
        self.scan_words(lv, range(1, 6), BLUE)
        self.reveal(rv, [6, 7, 8])
        self.scan_words(lv, range(6, 11), BLUE)

        marks = []
        marks += self.follow_ref(lv, rv, 11, "'../schemas/Identifiants.yaml'", "Identifiants.yaml",
                                 20, 9, '"#/components/schemas/Identifiants"')
        self.say(["le fichier pointé est rangé dans components",
                  "et le chemin de fichier devient un renvoi interne : #/components/…"])
        self.wait(1.6)

        self.scan_words(lv, range(12, 18), BLUE)
        self.reveal(rv, [10, 14])
        marks += self.follow_ref(lv, rv, 18, "'../schemas/Session.yaml'", "Session.yaml",
                                 21, 11, '"#/components/schemas/Session"')
        # Session cite Utilisateur, qui cite Role
        self.reveal(rv, [22])
        self.reveal(rv, [23])
        self.say("Session cite Utilisateur, qui cite Role : les $ref sont suivis en cascade")
        self.wait(1.4)

        self.scan_words(lv, [19], BLUE)
        marks += self.follow_ref(lv, rv, 20, "'../../_shared/responses/BadRequest.yaml'",
                                 "BadRequest.yaml", 27, 12, '"#/components/responses/BadRequest"')
        self.reveal(rv, [24])
        self.scan_words(lv, [21], BLUE)
        marks += self.follow_ref(lv, rv, 22, "'../../_shared/responses/Unauthorized.yaml'",
                                 "Unauthorized.yaml", 28, 13,
                                 '"#/components/responses/Unauthorized"')
        self.say("Unauthorized cite aussi ApiError : déjà rangé, il n'est pas copié deux fois")
        self.play(Indicate(rv.lines[23], color=BLUE, scale_factor=1.04), run_time=0.8)
        self.wait(0.8)

        self.play(*[FadeOut(m) for m in marks], run_time=0.4)
        self.say(["20 fichiers YAML  →  un seul dist/openapi.json",
                  "c'est ce fichier-là que lisent Spectral, Orval, openapi-typescript et Ajv"])
        self.play(Indicate(right.box, color=BLUE, scale_factor=1.02), run_time=0.8)
        self.wait(2.6)
        self.next_section()

    def fly(self, card, start, end):
        card.move_to(start)
        self.play(FadeIn(card, scale=0.8), run_time=0.25)
        self.play(card.animate.move_to(end).scale(0.85), run_time=0.55)
        self.play(FadeOut(card), run_time=0.2)

    def follow_ref(self, lv, rv, line, token, card_name, comp_line, ref_line, ref_token):
        """Un $ref : le fichier part dans components, le chemin devient un renvoi interne."""
        self.scan_lines(lv, [line], BLUE)
        src = highlight_rect(lv.token_box(line, token), BLUE, 0.18)
        self.play(FadeIn(src), run_time=0.25)
        self.fly(file_card(card_name, BLUE), src.get_center(), rv.lines[comp_line - 1].get_center())
        dst = highlight_rect(rv.token_box(ref_line, ref_token), BLUE, 0.18)
        self.reveal(rv, [comp_line, ref_line], FadeIn(dst))
        return [src, dst]

    # --- 2. Spectral : relire -------------------------------------------------------

    def spectral(self):
        self.show_chip("2 · Spectral : relire le contrat", PINK)
        console_rows = [
            row(("$ ", DIM), ("npm run contract", TXT)),
            row(("> redocly bundle openapi.yaml -o dist/openapi.json", DIM), ("   ✔", ACCENT)),
            row(("> spectral lint dist/openapi.json --ruleset .spectral.yaml", DIM)),
            row(("dist/openapi.json", TXT)),
            row((" 61:24", DIM), ("    error", ERROR), ("  operation-operationId-unique  ", DIM),
                ('Every operation must have unique "operationId".', TXT),
                ("   paths./session/deconnexion.post.operationId", DIM)),
            row((" 63:13", DIM), ("  warning", WARN), ("  operation-tag-defined         ", DIM),
                ("Operation tags must be defined in global tags.", TXT),
                ("    paths./session/deconnexion.post.tags[0]", DIM)),
            row(("✖ 2 problems (1 error, 1 warning, 0 infos, 0 hints)", ERROR)),
        ]
        clean_rows = console_rows[:3] + [
            row(("No results with a severity of 'error' found!", ACCENT)),
            row((" ", TXT)), row((" ", TXT)), row((" ", TXT)),
        ]
        (left, lv), (conf, cv) = panels(
            ("contract/features/session/paths/deconnexion.yaml", DECONNEXION_FAUTIF, "yaml",
             np.array([-2.55, 0.8, 0]), 8.8, 3.6, "copié de connexion.yaml", PINK),
            ("contract/.spectral.yaml", SPECTRAL_CONFIG, "yaml",
             np.array([4.6, 1.85, 0]), 4.5, 1.5, None, DIM),
            gutter=True,
        )
        (console, tv), = panels(
            ("terminal", TermView(console_rows), None, np.array([0, -2.3, 0]), 13.9, 2.6,
             "à la racine du dépôt", DIM),
        )
        (_, tv_clean), = panels(
            ("terminal", TermView(clean_rows), None, np.array([0, -2.3, 0]), 13.9, 2.6,
             None, DIM),
        )
        # Même échelle pour les deux sorties : on recale la seconde sur la première
        tv_clean.group.scale(tv.adv / tv_clean.adv, about_point=tv_clean.group.get_corner(UL))
        tv_clean.group.shift(tv.group.get_corner(UL) - tv_clean.group.get_corner(UL))

        side = (4.6, -0.15)
        self.play(FadeIn(left.chrome), FadeIn(lv.group), run_time=0.7)
        self.play(FadeIn(conf.chrome), FadeIn(cv.group), run_time=0.5)
        rules = label("aucune règle maison : les règles standard d'OpenAPI", 14, DIM)
        rules.next_to(conf.box, DOWN, buff=0.15)
        self.play(FadeIn(rules), run_time=0.5)
        self.say(["scénario : on crée la déconnexion",
                  "en copiant connexion.yaml…",
                  "…et on oublie deux choses"], pos=side, size=15, width=4.6)
        self.wait(1.6)

        self.play(FadeIn(console.chrome), run_time=0.4)
        for i in (1, 2, 3):
            self.reveal(tv, [i], run_time=0.3)

        issues = {
            3: ("seConnecter", ERROR, 5, ["même operationId que la connexion :",
                                          "deux hooks useSeConnecter, deux mocks…"]),
            5: ("Sessions", WARN, 6, ["tag inconnu : absent de la liste",
                                      "« tags » de openapi.yaml"]),
        }
        decor = []
        for ln in range(1, 13):
            self.scan_lines(lv, [ln], PINK)
            if ln not in issues:
                continue
            token, color, out_row, text = issues[ln]
            band = Rectangle(width=left.code_w + 0.2, height=lv.line_h)
            band.set_fill(color, 0.14).set_stroke(width=0)
            band.move_to([left.box.get_center()[0], lv.line_y(ln), 0])
            self.add(band)
            self.bring_to_front(lv.group)
            x0 = lv.token_box(ln, token)[0][0] - len(token) * lv.adv / 2
            wave = squiggle(x0, x0 + len(token) * lv.adv, lv.line_y(ln) - 0.47 * lv.block_h,
                            color, period=lv.adv * 1.4)
            new_rows = [4, out_row] if out_row == 5 else [out_row]
            self.play(FadeIn(band), ShowCreation(wave), run_time=0.35)
            self.reveal(tv, new_rows, run_time=0.35)
            self.say(text, pos=side, color=color, size=15, width=4.6)
            self.wait(1.4)
            decor += [band, wave]
        self.reveal(tv, [7], run_time=0.4)
        self.say(["Spectral ne corrige rien, il signale.",
                  "une error fait échouer la commande :",
                  "npm run sync s'arrête là"], pos=side, color=PINK, size=15, width=4.6)
        self.wait(2.6)

        # On corrige le YAML, on relance : plus rien
        fixed = CodeView(DECONNEXION, ["yaml"], gutter=True)
        fixed.group.scale(lv.adv / fixed.adv, about_point=ORIGIN)
        fixed.adv, fixed.block_h, fixed.line_h = lv.adv, lv.block_h, lv.line_h
        fixed.group.shift(lv.group.get_corner(UL) - fixed.group.get_corner(UL))
        self.play(*[FadeOut(m) for m in decor], run_time=0.3)
        self.play(FadeTransform(lv.lines[2], fixed.lines[2]),
                  FadeTransform(lv.lines[4], fixed.lines[4]), run_time=0.8)
        self.play(FadeOut(VGroup(*tv.lines[3:])), run_time=0.3)
        self.reveal(tv_clean, [4], run_time=0.4)
        self.say(["seDeconnecter, tag « Session » :", "contrat relu, la génération peut continuer"],
                 pos=side, color=ACCENT, size=15, width=4.6)
        self.wait(2.4)
        self.next_section()

    # --- 3. Orval : écrire le SDK ---------------------------------------------------

    def orval(self):
        self.show_chip("3 · Orval : écrire le SDK des fronts", GOLD)
        (left, lv), (usage, uv) = panels(
            ("contract/…/connexion.yaml", CONNEXION_COURT, "yaml",
             np.array([-4.35, 0.83, 0]), 5.2, 3.55, "extrait", DIM),
            ("clients/web · exemple", USAGE, "typescript",
             np.array([-4.35, -1.83, 0]), 5.2, 1.5, "écrit à la main", DIM),
        )
        (p1, v1), (p2, v2), (p3, v3) = panels(
            ("sdk/src/generated/model/identifiants.ts", ORVAL_MODEL, "typescript",
             np.array([2.7, 1.605, 0]), 8.5, 1.99, "généré", GOLD),
            ("sdk/src/generated/endpoints/session/session.ts", ORVAL_ENDPOINT, "typescript",
             np.array([2.7, -0.505, 0]), 8.5, 1.99, "généré · condensé", GOLD),
            ("sdk/src/generated/endpoints/session/session.msw.ts", ORVAL_MSW, "typescript",
             np.array([2.7, -2.615, 0]), 8.5, 1.99, "généré · condensé", GOLD),
        )
        side = (-4.35, -3.15)
        self.play(FadeIn(left.chrome), FadeIn(lv.group), run_time=0.7)
        self.say(["npm run generate (dans sdk/) : Orval lit dist/openapi.json",
                  "et écrit sdk/src/generated/, qu'on ne modifie jamais"],
                 pos=side, size=14, width=5.2)
        self.wait(1.2)

        # L'operationId nomme tout
        self.play(flash(words(lv, [2]), GOLD, 0.12))
        op = highlight_rect(lv.token_box(2, "seConnecter"), GOLD, 0.22)
        self.play(FadeIn(op), run_time=0.3)
        self.play(FadeIn(p2.chrome), FadeIn(v2.group), FadeIn(p3.chrome), FadeIn(v3.group),
                  run_time=0.8)
        names = [(v2, 1, "seConnecter"), (v2, 5, "useSeConnecter"),
                 (v3, 1, "getSeConnecterResponseMock"), (v3, 4, "getSeConnecterMockHandler")]
        boxes = [v.token_box(ln, t) for v, ln, t in names]
        self.play(flash(boxes, GOLD, 0.3))
        hls = VGroup(*[highlight_rect(b, GOLD, 0.2) for b in boxes])
        self.play(FadeIn(hls), run_time=0.4)
        self.say(["operationId  →  le nom de la fonction,",
                  "du hook React Query et du mock MSW"], pos=side, color=GOLD, size=15, width=5.2)
        self.wait(2.2)

        # Les schémas deviennent des interfaces
        self.play(FadeOut(hls), FadeOut(op), run_time=0.3)
        self.play(flash([lv.line_box(7)], GOLD, 0.3))
        ref = highlight_rect(lv.token_box(7, "Identifiants"), GOLD, 0.22)
        self.play(FadeIn(ref), FadeIn(p1.chrome), FadeIn(v1.group, shift=0.05 * DOWN), run_time=0.7)
        arg = highlight_rect(v2.token_box(1, "identifiants: Identifiants"), GOLD, 0.2)
        self.play(FadeIn(arg), run_time=0.3)
        self.say(["chaque schéma  →  une interface TypeScript,",
                  "et le corps de la requête est typé"], pos=side, color=GOLD, size=15, width=5.2)
        self.wait(1.8)

        self.play(FadeOut(ref), FadeOut(arg), run_time=0.3)
        self.play(flash([lv.line_box(11)], GOLD, 0.3))
        ref = highlight_rect(lv.token_box(11, "Session"), GOLD, 0.22)
        outs = VGroup(highlight_rect(v2.token_box(2, "customInstance<Session>"), GOLD, 0.2),
                      highlight_rect(v3.token_box(1, "Session"), GOLD, 0.2))
        self.play(FadeIn(ref), FadeIn(outs), run_time=0.5)
        self.say(["la réponse 200 type le retour,",
                  "et faker en fabrique une fausse pour le mock"],
                 pos=side, color=GOLD, size=15, width=5.2)
        self.wait(1.8)
        self.play(FadeOut(ref), FadeOut(outs), run_time=0.3)
        ci = highlight_rect(v2.token_box(2, "customInstance"), GOLD, 0.2)
        self.play(FadeIn(ci), run_time=0.3)
        self.say(["customInstance : le seul fetch du SDK,",
                  "écrit à la main (sdk/src/custom-instance.ts)"],
                 pos=side, color=GOLD, size=15, width=5.2)
        self.wait(1.8)
        self.play(FadeOut(ci), run_time=0.3)

        # Et côté front, on appelle le hook
        self.play(FadeIn(usage.chrome), FadeIn(uv.group, shift=0.05 * UP), run_time=0.6)
        self.play(flash(words(uv, [1, 2]), GOLD, PER_WORD))
        self.say(["le front n'écrit ni fetch ni URL : il appelle le hook.",
                  "et avec MSW, il tourne sans serveur (épisode 20)"],
                 pos=side, color=TXT, size=15, width=5.2)
        self.wait(2.6)
        self.next_section()

    # --- 4. openapi-typescript : les types du serveur ---------------------------------

    def openapi_typescript(self):
        self.show_chip("4 · openapi-typescript : les types du serveur", VIOLET)
        (left, lv), (right, rv) = panels(
            ("contract/features/session/schemas/Session.yaml", SESSION_SCHEMA, "yaml",
             np.array([-3.55, 0.95, 0]), 6.9, 3.3, None, DIM),
            ("server/app/contract/types.ts", TYPES_TS, "typescript",
             np.array([3.55, 0.95, 0]), 6.9, 3.3, "généré · extrait", VIOLET),
        )
        (svc, sv), = panels(
            ("server/app/services/session_service.ts", SERVICE_FAUTIF, "typescript",
             np.array([0, -1.92, 0]), 13.9, 2.25, "écrit à la main", DIM),
        )
        self.play(FadeIn(left.chrome), FadeIn(lv.group), FadeIn(right.chrome), run_time=0.7)
        self.reveal(rv, [1, 2, 8, 9])
        self.say(["npm run sync:contract (dans server/) : copie le bundle, puis",
                  "openapi-typescript en tire un fichier de types, sans aucun code exécutable"],
                 pos=(0, -1.15), size=15)
        self.wait(1.0)

        self.scan_words(lv, [1, 2], VIOLET)
        self.reveal(rv, [3, 7])
        self.scan_words(lv, [3, 4, 5], VIOLET)
        req = highlight_rect(lv.line_box(3), VIOLET, 0.15)
        self.play(FadeIn(req), run_time=0.3)
        self.scan_words(lv, [6, 7, 8], VIOLET)
        self.reveal(rv, [4], FadeIn(highlight_rect(rv.token_box(4, 'components["schemas"]["Utilisateur"]'),
                                                   VIOLET, 0.15)))
        self.scan_words(lv, [9, 10, 11], VIOLET)
        self.reveal(rv, [5, 6])
        self.say(["required  →  aucun « ? » : utilisateur et token sont obligatoires",
                  "le $ref devient un renvoi vers le type Utilisateur"], pos=(0, -1.15), size=15)
        self.wait(2.0)

        # Le service s'appuie dessus : une faute de nom ne compile pas
        self.play(FadeOut(self.cap), FadeIn(svc.chrome), FadeIn(sv.group, shift=0.05 * UP),
                  run_time=0.7)
        self.cap = None
        self.play(flash(words(sv, [1]), VIOLET, PER_WORD))
        self.scan_lines(sv, [2, 3, 4, 5, 6], VIOLET)
        x0 = sv.token_box(6, "jeton:")[0][0] - 5 * sv.adv / 2
        wave = squiggle(x0, x0 + 5 * sv.adv, sv.line_y(6) - 0.47 * sv.block_h, ERROR,
                        period=sv.adv * 1.4)
        err = label("error TS2353: Object literal may only specify known properties, and 'jeton' "
                    "does not exist in type '{ utilisateur: …; token: string; }'.",
                    14, ERROR, font=MONO_FONT)
        if err.get_width() > 13.6:
            err.set_width(13.6)
        err.move_to([0, -3.45, 0])
        self.play(ShowCreation(wave), FadeIn(err, shift=0.05 * UP), run_time=0.6)
        self.wait(2.2)

        fixed = CodeView(SERVICE, ["typescript"], gutter=False)
        fixed.group.scale(sv.adv / fixed.adv, about_point=ORIGIN)
        fixed.group.shift(sv.group.get_corner(UL) - fixed.group.get_corner(UL))
        ok = label("✔ tsc : le service rend exactement la forme du contrat", 15, ACCENT, bold=True)
        ok.move_to(err)
        self.play(FadeOut(wave), FadeTransform(sv.lines[5], fixed.lines[5]),
                  FadeOut(err), FadeIn(ok), run_time=0.8)
        self.wait(1.4)
        self.play(FadeOut(ok), run_time=0.3)
        self.say(["mais les types s'effacent quand le code tourne :",
                  "pour contrôler les vraies données qui arrivent, il faut Ajv"],
                 pos=(0, -3.4), color=VIOLET, size=16)
        self.wait(2.4)
        self.next_section()

    # --- 5. Ajv : contrôler à l'exécution ---------------------------------------------

    def ajv(self):
        self.show_chip("5 · Ajv : contrôler chaque requête", ACCENT)
        (left, lv), (req, qv), (resp, pv) = panels(
            ("contract/features/session/schemas/Identifiants.yaml", IDENTIFIANTS, "yaml",
             np.array([-3.85, 1.0, 0]), 6.2, 3.2, None, DIM),
            ("POST /session/connexion", REQUETE, "json",
             np.array([3.5, 1.45, 0]), 6.9, 2.3, "requête entrante", ACCENT),
            ("réponse  ·  HTTP 400", REPONSE_400, "json",
             np.array([0, -2.13, 0]), 13.9, 2.94, "envoyée par le middleware de contrat", ERROR),
        )
        ctrl = node("contrôleur", "seConnecter", DIM, width=2.3, title_size=18)
        ctrl.move_to([5.65, -0.1, 0])
        side = (2.15, -0.1)

        self.play(FadeIn(left.chrome), FadeIn(lv.group), FadeIn(ctrl), run_time=0.7)
        start = req.box.get_center() + 7 * RIGHT
        group = VGroup(req.chrome, qv.group)
        group.shift(start - req.box.get_center())
        self.add(group)
        self.play(group.animate.shift(-(start - np.array([3.5, 1.45, 0]))), run_time=0.8)
        self.say(["le middleware de contrat l'arrête AVANT le contrôleur,",
                  "et la compare au schéma compilé par Ajv"], pos=side, size=14, width=4.3)
        self.wait(1.2)

        self.play(FadeIn(resp.chrome), run_time=0.4)
        self.reveal(pv, [1, 2, 3, 4, 8, 9])
        checks = [
            (2, [7, 8, 9], 5, "format: email  →  il manque le @"),
            (3, [10, 11, 12], 6, "minLength: 1  →  mot de passe vide"),
            (4, [2], 7, "additionalProperties: false  →  « role » n'existe pas"),
        ]
        crosses = []
        for body_line, schema_lines, detail, why in checks:
            self.play(flash([qv.line_box(body_line)], ACCENT, 0.3),
                      flash([lv.line_box(ln) for ln in schema_lines], ACCENT, 0.1),
                      run_time=0.4)
            rule = highlight_rect(lv.line_box(schema_lines[-1]), ERROR, 0.16)
            cross = mark("✖", ERROR, qv, body_line)
            self.play(FadeIn(rule), FadeIn(cross, scale=1.5), run_time=0.3)
            self.reveal(pv, [detail], run_time=0.35)
            self.say(why, pos=side, color=ERROR, size=15, width=4.3)
            self.wait(1.2)
            self.play(FadeOut(rule), run_time=0.2)
            crosses.append(cross)

        never = node("contrôleur", "✖ jamais appelé", ERROR, width=2.3, title_size=18)
        never.move_to(ctrl)
        self.play(FadeTransform(ctrl, never), run_time=0.5)
        self.say(["les trois erreurs d'un coup (allErrors),",
                  "un détail par champ : le front l'affiche sous l'input"],
                 pos=side, color=TXT, size=14, width=4.3)
        self.wait(2.4)
        self.say(["et dans l'autre sens, la réponse du contrôleur est",
                  "contrôlée aussi  →  500 (épisode 12)"], pos=side, color=TXT, size=14, width=4.3)
        self.wait(2.4)
        self.next_section()

    # --- 6. Récapitulatif -------------------------------------------------------------

    def recap(self):
        self.show_chip("Qui fait quoi, et quand")
        yaml = node("contract/*.yaml", "20 fichiers · à la main", ACCENT, width=3.1)
        bundle = node("dist/openapi.json", "un seul fichier", TXT, width=3.1)
        sdk = node("sdk/", "fonctions · hooks · mocks", GOLD, width=3.4)
        types = node("types.ts", "les types du serveur", VIOLET, width=3.4)
        check = node("contrôle en direct", "requêtes et réponses", ACCENT, width=3.4)
        yaml.move_to([-5.4, 0.9, 0])
        bundle.move_to([-1.2, 0.9, 0])
        sdk.move_to([4.6, 2.1, 0])
        types.move_to([4.6, 0.9, 0])
        check.move_to([4.6, -0.3, 0])

        a1 = link(edge_point(yaml, RIGHT), edge_point(bundle, LEFT), BLUE)
        t1 = label("Redocly", 16, BLUE, bold=True).next_to(a1, UP, buff=0.1)
        gate = label("✔ Spectral", 16, PINK, bold=True).next_to(bundle, DOWN, buff=0.15)
        outs = VGroup()
        for target, name, color in ((sdk, "Orval", GOLD), (types, "openapi-typescript", VIOLET),
                                    (check, "Ajv", ACCENT)):
            a = link(edge_point(bundle, RIGHT), edge_point(target, LEFT), color)
            t = label(name, 15, color, bold=True).move_to(a.get_center() + 0.32 * UP)
            outs.add(VGroup(a, t))

        self.play(FadeIn(yaml), run_time=0.4)
        self.play(GrowArrow(a1), FadeIn(t1), FadeIn(bundle), run_time=0.7)
        self.play(FadeIn(gate, shift=0.1 * UP), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(o) for o in outs], lag_ratio=0.2),
                  LaggedStartMap(FadeIn, VGroup(sdk, types, check), lag_ratio=0.2), run_time=1.2)

        when = VGroup(
            markup(f'<span foreground="{TXT}"><b>npm run sync</b></span>'
                   f'<span foreground="{DIM}">  ·  Redocly → Spectral → Orval → openapi-typescript'
                   f'  ·  à la génération</span>', size=17),
            markup(f'<span foreground="{ACCENT}"><b>serveur lancé</b></span>'
                   f'<span foreground="{DIM}">  ·  Ajv  ·  à chaque requête, dans les deux sens</span>',
                   size=17),
        ).arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to([0, -2.1, 0])
        self.play(LaggedStartMap(FadeIn, when, shift=0.1 * UP, lag_ratio=0.3), run_time=0.9)
        rule = label("on n'écrit que le YAML : tout le reste en découle", 19, TXT, bold=True)
        rule.move_to([0, -3.2, 0])
        self.play(FadeIn(rule, shift=0.1 * UP), run_time=0.6)
        next_ep = label("épisode suivant : npm run sync, la chaîne de génération  →", 15, DIM)
        next_ep.to_corner(DR, buff=0.35)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(3.5)
