"""
Épisode 9 — Le serveur refuse de démarrer, et ce qu'il ne vérifie pas

Le garde-fou de démarrage (server/providers/contract_provider.ts) compare les
routes déclarées aux opérations du contrat. « Toute route déclare son
operationId » n'est pas une règle de revue : c'est une impossibilité technique.
  1. On efface le `.use(middleware.contract(...))` d'une route : au démarrage,
     un logger.warn jaune puis le logger.fatal rouge, et l'application s'arrête
     (process.exitCode = 1, puis app.terminate()).
  2. Deux ensembles : les routes et les opérations. La route orpheline fait
     arrêter le serveur ; l'opération sans route n'est qu'un avertissement en dev.
  3. Les autres fautes détectées : operationId mal orthographié, chemin ou
     méthode qui ne correspondent pas au contrat.
  4. Avertir ou bloquer : `this.app.inDev && !process.env.CI`. La même fonction
     tourne dans tests/functional/contract.spec.ts, où NODE_ENV=test : là,
     l'opération sans route fait échouer le test. La CI est locale : c'est
     `npm run verifier` qui lance ces tests (épisode 30).
  5. Ce qui n'est PAS vérifié : seuls operationId, chemin et méthode sont
     comparés. `security` dans le YAML contre `middleware.auth()` sur la route :
     aucune alerte. HORS_CONTRAT est vide, et router.resource() n'est pas utilisé.

Les messages affichés sont ceux du code (contract_provider.ts:53-198). Le
logger écrit du JSON pino (config/logger.ts, sans pino-pretty) : la console
montre le champ `msg` mis en forme, précédé du niveau. Un démarrage réussi ne
journalise rien du garde-fou : il n'y a pas de ligne « N opérations compilées ».

Sources : server/providers/contract_provider.ts, server/start/routes.ts (en-tête),
server/start/routes/utilisateurs.ts, server/start/routes/session.ts,
server/app/middleware/contract_middleware.ts, server/tests/functional/contract.spec.ts,
server/bin/test.ts (NODE_ENV=test), server/config/logger.ts,
contract/features/session/paths/moi.yaml, docs/adr/0003.

Rendu vidéo :  manimgl ep09_garde_fou.py Ep09GardeFou -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


def caption(text, point, color=DIM, size=15):
    return label(text, size, color).move_to(point)


def code_panel(filename, source, lexer, center, width, height, tag=None, tag_color=DIM,
               max_scale=1.0):
    panel = EditorPanel(filename, center, width=width, height=height, tag=tag, tag_color=tag_color)
    view = CodeView(source, [lexer])
    panel.fit_code(view, max_scale=max_scale)
    return panel, view


def console_rows(panel, rows, size=15, top_pad=0.0):
    """Lignes de console monospace, colorées, alignées à gauche dans un panneau."""
    # Text() avale les espaces de tête : on mesure l'avance d'un caractère
    # monospace et on décale chaque ligne d'autant de colonnes.
    adv = label("M" * 20, size, TXT, font=MONO_FONT).get_width() / 20
    group, indents = VGroup(), []
    lh = 0.3 * size / 15
    for text, color in rows:
        stripped = text.lstrip(" ")
        indents.append(len(text) - len(stripped))
        group.add(label(stripped if stripped else " ", size, color, font=MONO_FONT))
    widest = max(m.get_width() + n * adv for m, n in zip(group, indents))
    scale = min(1.0, panel.code_w / widest)
    for i, (t, n) in enumerate(zip(group, indents)):
        t.scale(scale)
        t.move_to([0, panel.code_top - top_pad - i * lh * scale, 0])
        t.align_to([panel.code_left + n * adv * scale, 0, 0], LEFT)
    return group


class Ep09GardeFou(EpisodeScene):
    EPISODE = "09"
    TITLE = "Le garde-fou de démarrage"

    def construct(self):
        self.effacer()
        self.ensembles()
        self.variantes()
        self.avertir_ou_bloquer()
        self.non_verifie()

    # --- 1. On efface une ligne ---------------------------------------------------

    def effacer(self):
        self.show_chip("Une route sans operationId")
        src = (
            "  router\n"
            "    .get('/utilisateurs', [controllers.Utilisateurs, 'lister'])\n"
            "    .use(middleware.contract({ operationId: 'listerUtilisateurs' }))\n"
            "\n"
            "  router\n"
            "    .post('/utilisateurs', [controllers.Utilisateurs, 'creer'])\n"
            "    .use(middleware.contract({ operationId: 'creerUtilisateur' }))\n"
            "  …"
        )
        panel, view = code_panel("server/start/routes/utilisateurs.ts", src, "typescript",
                                 np.array([0, 1.3, 0]), 13.6, 2.9, tag="lignes 12-18")
        console = EditorPanel("terminal · server/", np.array([0, -2.05, 0]), width=13.6, height=3.65,
                              tag="journal pino (JSON) : niveau + msg, mis en forme")
        prompt = console_rows(console, [("$ npm run dev", TXT)], 16)
        quiet = console_rows(console, [("", DIM),
                                       ("# démarrage normal : le garde-fou ne journalise rien", DIM)], 16)

        self.play(FadeIn(panel.chrome), FadeIn(view.group), run_time=0.8)
        self.play(FadeIn(console.chrome), FadeIn(prompt), run_time=0.6)
        self.play(FadeIn(quiet[1]), run_time=0.5)
        self.wait(1.8)

        # Le curseur sélectionne la ligne du contrat, puis l'efface
        box = view.line_box(7)
        self.play(flash([box], ACCENT, 0.6), run_time=0.6)
        sel = highlight_rect(box, BLUE, 0.25)
        self.play(FadeIn(sel), run_time=0.4)
        self.wait(0.4)
        self.play(FadeOut(sel), FadeOut(view.lines[6]), FadeOut(view.gutter[6]), run_time=0.6)
        gone = label("ligne effacée", 15, ERROR, bold=True).move_to(
            [view.col_x(7, 6) + 1.0, view.line_y(7), 0])
        self.play(FadeIn(gone), FadeOut(quiet), run_time=0.4)

        # On relance : avertissement, puis arrêt
        rows = [
            ("$ npm run dev", TXT),
            ("", TXT),
            ("[warn]  Opérations du contrat sans implémentation :", WARN),
            ("          creerUtilisateur (POST /utilisateurs) — déclaré au contrat, aucune route ne l'implémente.", WARN),
            ("[fatal] Le contrat et les routes ne concordent pas :", ERROR),
            ("          · POST /api/v1/utilisateurs — route hors contrat. Ajoute .use(middleware.contract({ operationId }))", ERROR),
            ("            ou déclare le préfixe dans HORS_CONTRAT.", ERROR),
            ("", ERROR),
            ("        Le serveur est arrêté. Corrige les routes ou le contrat.", ERROR),
        ]
        out = console_rows(console, rows, 16)
        self.remove(prompt)
        self.add(out[0])
        self.play(Indicate(out[0], color=ACCENT, scale_factor=1.05), run_time=0.5)
        self.play(FadeIn(out[2:4], shift=0.05 * UP), run_time=0.6)
        self.wait(0.6)
        self.play(FadeIn(out[4:], shift=0.05 * UP), run_time=0.8)
        stop = label("process.exitCode = 1  ·  app.terminate()", 16, ERROR, font=MONO_FONT, bold=True)
        stop_bg = SurroundingRectangle(stop, buff=0.12).set_fill(ERROR, 0.12).set_stroke(ERROR, 1.5)
        stop_g = VGroup(stop_bg, stop).next_to(console.box.get_corner(DR), UL, buff=0.2)
        self.play(FadeIn(stop_g, scale=1.2), run_time=0.5)
        self.wait(3.4)
        self.clear_stage()

    # --- 2. Deux ensembles -------------------------------------------------------

    def ensembles(self):
        self.show_chip("Deux ensembles comparés au démarrage")
        cy = -0.1
        left = Ellipse(width=5.6, height=4.2).move_to([-1.45, cy, 0])
        left.set_fill(VIOLET, 0.07).set_stroke(VIOLET, 2.5)
        right = Ellipse(width=5.6, height=4.2).move_to([1.45, cy, 0])
        right.set_fill(ACCENT, 0.07).set_stroke(ACCENT, 2.5)
        l_lbl = label("routes déclarées", 19, VIOLET, bold=True).move_to([-3.1, cy + 2.35, 0])
        r_lbl = label("opérations du contrat", 19, ACCENT, bold=True).move_to([3.1, cy + 2.35, 0])
        l_sub = label("start/routes/*.ts", 15, DIM, font=MONO_FONT).next_to(l_lbl, DOWN, buff=0.06)
        r_sub = label("app/contract/openapi.json", 15, DIM, font=MONO_FONT).next_to(r_lbl, DOWN, buff=0.06)
        # Les étiquettes du haut ne doivent pas mordre sur les ellipses
        for m in (l_lbl, r_lbl, l_sub, r_sub):
            m.shift(0.15 * UP)

        ids = ["seConnecter", "seDeconnecter", "monProfil",
               "listerUtilisateurs", "creerUtilisateur", "modifierUtilisateur"]
        col = VGroup(*[label(i, 18, TXT, font=MONO_FONT) for i in ids])
        col.arrange(DOWN, buff=0.16).move_to([0, cy, 0])
        self.play(ShowCreation(left), ShowCreation(right), FadeIn(l_lbl), FadeIn(r_lbl),
                  FadeIn(l_sub), FadeIn(r_sub), run_time=1.0)
        self.play(LaggedStartMap(FadeIn, col, lag_ratio=0.12), run_time=1.0)
        ok = label("les 6 se recouvrent : rien à signaler", 17, ACCENT).move_to([0, -2.85, 0])
        self.play(FadeIn(ok), run_time=0.5)
        self.wait(1.2)

        # creerUtilisateur se dédouble : la route d'un côté, l'opération de l'autre
        creer = col[4]
        route = label("POST /utilisateurs", 18, ERROR, font=MONO_FONT, bold=True)
        route.move_to([-3.05, cy, 0])
        op = label("creerUtilisateur", 18, WARN, font=MONO_FONT, bold=True).move_to([3.05, cy, 0])
        route_src = creer.copy()
        self.play(FadeOut(ok),
                  ReplacementTransform(route_src, route),
                  ReplacementTransform(creer, op),
                  col[5].animate.move_to(creer.get_center()), run_time=1.0)
        no_id = label("sans operationId", 15, ERROR).next_to(route, DOWN, buff=0.1)
        no_route = label("sans route", 15, WARN).next_to(op, DOWN, buff=0.1)
        self.play(FadeIn(no_id), FadeIn(no_route), run_time=0.4)
        for _ in range(2):
            self.play(route.animate.set_opacity(0.25), rate_func=there_and_back, run_time=0.5)

        verdict_l = label("anomalie → fatal, le serveur s'arrête", 17, ERROR, bold=True)
        verdict_l.move_to([-3.4, -2.75, 0])
        verdict_r = label("travail en cours → warn (en dev)", 17, WARN, bold=True)
        verdict_r.move_to([3.4, -2.75, 0])
        why_r = label("le contrat se merge avant le code", 15, DIM).next_to(verdict_r, DOWN, buff=0.1)
        self.play(FadeIn(verdict_l, shift=0.1 * UP), run_time=0.5)
        self.play(FadeIn(verdict_r, shift=0.1 * UP), FadeIn(why_r), run_time=0.5)
        self.wait(2.4)
        self.clear_stage()

    # --- 3. Les autres fautes ------------------------------------------------------

    def variantes(self):
        self.show_chip("Les autres fautes détectées", ERROR)
        cases = [
            ("operationId mal orthographié",
             ".use(middleware.contract({ operationId: 'listerUtilisateur' }))",
             'GET,HEAD /api/v1/utilisateurs — operationId "listerUtilisateur" absent du contrat.'),
            ("chemin différent du contrat",
             ".patch('/users/:id', [controllers.Utilisateurs, 'modifier'])",
             'modifierUtilisateur — la route est montée sur "/users/{id}" alors que le contrat '
             'déclare "/utilisateurs/{id}".'),
            ("méthode différente du contrat",
             ".put('/utilisateurs/:id', [controllers.Utilisateurs, 'modifier'])",
             "modifierUtilisateur — la route répond à PUT alors que le contrat déclare PATCH."),
        ]
        cards = VGroup()
        y = 1.95
        for title, code, msg in cases:
            box = RoundedRectangle(width=13.6, height=1.45, corner_radius=0.14)
            box.set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5).move_to([0, y, 0])
            t = label(title, 19, TXT, bold=True)
            t.move_to(box.get_corner(UL) + np.array([0.3 + t.get_width() / 2, -0.25, 0]))
            c = label(code, 18, BLUE, font=MONO_FONT)
            m = label("[fatal] · " + msg, 17, ERROR, font=MONO_FONT)
            for mob, dy in ((c, -0.65), (m, -1.08)):
                if mob.get_width() > 13.0:
                    mob.set_width(13.0)
                mob.move_to(box.get_corner(UL) + np.array([0.3 + mob.get_width() / 2, dy, 0]))
            cards.add(VGroup(box, t, c, m))
            y -= 1.62
        for card in cards:
            self.play(FadeIn(card[0]), FadeIn(card[1]), FadeIn(card[2]), run_time=0.5)
            self.play(FadeIn(card[3], shift=0.05 * UP), run_time=0.5)
            self.wait(1.9)
        note = label("route.methods : router.get() déclare GET et HEAD", 16, DIM)
        note.move_to([0, -3.1, 0])
        tsc = label("bonus : l'operationId est typé (OperationId), tsc souligne aussi la faute de frappe",
                    16, DIM).next_to(note, DOWN, buff=0.1)
        self.play(FadeIn(note), FadeIn(tsc), run_time=0.5)
        self.wait(2.6)
        self.clear_stage()

    # --- 4. Avertir ou bloquer ------------------------------------------------------

    def avertir_ou_bloquer(self):
        self.show_chip("Avertir ou bloquer ?", WARN)
        src = (
            "if (operationsSansRoute.length > 0) {\n"
            "  if (this.app.inDev && !process.env.CI) {\n"
            "    logger.warn(\n"
            "      ['Opérations du contrat sans implémentation :', ...operationsSansRoute].join('\\n  ')\n"
            "    )\n"
            "  } else {\n"
            "    anomalies.push(...operationsSansRoute)\n"
            "  }\n"
            "}"
        )
        panel, view = code_panel("server/providers/contract_provider.ts", src, "typescript",
                                 np.array([0, 1.15, 0]), 13.6, 3.2, tag="lignes 177-185")
        self.play(FadeIn(panel.chrome), FadeIn(view.group), run_time=0.8)
        cond = view.token_box(2, "this.app.inDev && !process.env.CI")
        self.play(flash([cond], WARN, 0.6), run_time=0.6)
        self.play(FadeIn(highlight_rect(cond, WARN, 0.15)), run_time=0.3)

        def outcome(head, sub, color, x):
            box = RoundedRectangle(width=4.35, height=1.25, corner_radius=0.12)
            box.set_fill(color, 0.08).set_stroke(color, 1.8).move_to([x, -1.45, 0])
            h = label(head, 19, color, font=MONO_FONT, bold=True)
            s = VGroup(*[label(part, 16, TXT) for part in sub.split("|")]).arrange(DOWN, buff=0.08)
            for mob in (h, s):
                if mob.get_width() > 4.05:
                    mob.set_width(4.05)
            VGroup(h, s).arrange(DOWN, buff=0.14).move_to(box)
            return VGroup(box, h, s)

        dev = outcome("npm run dev", "NODE_ENV=development|→ warn jaune, ça démarre", WARN, -4.6)
        ci = outcome("CI=true, ou hors dev", "→ anomalie|fatal, le serveur s'arrête", ERROR, 0.0)
        test = outcome("npm test", "NODE_ENV=test|→ le test échoue", ERROR, 4.6)
        self.play(FadeIn(dev, shift=0.1 * UP), run_time=0.6)
        self.play(FadeIn(ci, shift=0.1 * UP), run_time=0.6)
        self.wait(0.8)

        # La même fonction, rejouée par un test
        same = label("la même fonction, importée par tests/functional/contract.spec.ts :", 16, DIM)
        same.move_to([0, -2.55, 0])
        imp = label("import { comparerRoutesEtContrat } from '#providers/contract_provider'", 16,
                    BLUE, font=MONO_FONT).next_to(same, DOWN, buff=0.12)
        self.play(FadeIn(same), FadeIn(imp), run_time=0.6)
        self.play(FadeIn(test, shift=0.1 * UP), run_time=0.6)
        tname = label("test : « toute opération du contrat est implémentée »", 16, TXT)
        tname.next_to(test, UP, buff=0.12)
        self.play(FadeIn(tname), run_time=0.4)
        local = label("la CI est locale : npm run verifier lance ces tests (épisode 30)", 17, ACCENT, bold=True)
        local.move_to([0, -3.6, 0])
        self.play(FadeIn(local, shift=0.1 * UP), run_time=0.6)
        self.wait(3.0)
        self.clear_stage()

    # --- 5. Ce qui n'est pas vérifié -------------------------------------------------

    def non_verifie(self):
        self.show_chip("Ce que le garde-fou ne vérifie pas", ERROR)
        yaml_src = (
            "get:\n"
            "  operationId: monProfil\n"
            "  security:\n"
            "    - bearerAuth: []"
        )
        route_src = (
            "router\n"
            "  .get('/moi', [controllers.Session, 'profil'])\n"
            "  .use([middleware.auth(), middleware.contract({ operationId: 'monProfil' })])"
        )
        yp, yv = code_panel("contract/features/session/paths/moi.yaml", yaml_src, "yaml",
                            np.array([-3.3, 1.82, 0]), 7.0, 1.8, max_scale=0.75)
        said = VGroup(label("le contrat dit :", 18, DIM),
                      label("route protégée (Bearer)", 22, ACCENT, bold=True)).arrange(DOWN, buff=0.1)
        said.move_to([3.6, 1.82, 0])
        rp, rv = code_panel("server/start/routes/session.ts", route_src, "typescript",
                            np.array([0, -0.07, 0]), 13.6, 1.75, tag="lignes 23-25")
        self.play(FadeIn(yp.chrome), FadeIn(yv.group), run_time=0.6)
        self.play(FadeIn(said), run_time=0.4)
        self.play(FadeIn(rp.chrome), FadeIn(rv.group), run_time=0.6)
        sec_rect = highlight_rect(yv.span_box(3, 2, len("security:")), ACCENT, 0.15)
        auth_box = rv.token_box(3, "middleware.auth(), ")
        self.play(FadeIn(sec_rect), FadeIn(highlight_rect(auth_box, ACCENT, 0.15)), run_time=0.5)
        self.wait(0.6)

        # Quelqu'un retire auth() : le serveur démarre quand même
        strike = Line(auth_box[0] + np.array([-auth_box[1] / 2, 0, 0]),
                      auth_box[0] + np.array([auth_box[1] / 2, 0, 0])).set_stroke(ERROR, 3)
        self.play(ShowCreation(strike), run_time=0.5)
        silent = label("le serveur démarre : aucune alerte, rien ne compare security et auth()",
                       18, WARN, bold=True)
        silent.move_to([0, -1.22, 0])
        nuance = label("ici, getUserOrFail() du contrôleur renvoie encore un 401 ; "
                       "une route qui ne l'appelle pas serait publique", 15, DIM)
        nuance.next_to(silent, DOWN, buff=0.1)
        fit_x(nuance)
        self.play(FadeIn(silent, shift=0.1 * UP), run_time=0.6)
        self.play(FadeIn(nuance), run_time=0.5)
        self.wait(2.2)

        rows = VGroup(
            label("✔  comparés : operationId · chemin · méthode", 17, ACCENT),
            label("✖  non comparé : security du YAML  ↔  middleware.auth() de la route", 17, ERROR),
            label("•  HORS_CONTRAT = [ ]  : vide, et doit le rester", 17, TXT),
            label("•  pas de router.resource() : ses routes n'auraient pas d'operationId", 17, TXT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.13)
        rows.move_to([0, -2.72, 0]).to_edge(LEFT, buff=0.6)
        bg = SurroundingRectangle(rows, buff=0.25).set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
        self.play(FadeIn(bg), LaggedStartMap(FadeIn, rows, shift=0.1 * RIGHT, lag_ratio=0.3), run_time=1.6)
        self.wait(3.0)
        next_ep = label("épisode suivant : le voyage d'une requête  →", 15, DIM)
        next_ep.to_corner(DR, buff=0.3)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(1.5)
