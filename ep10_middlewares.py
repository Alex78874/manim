"""
Épisode 10 — Le voyage d'une requête : l'oignon des middlewares

Savoir où vit chaque responsabilité, donc où chercher un bug. Une requête
`PATCH /api/v1/utilisateurs/:id` traverse trois couches, dans l'ordre exact de
server/start/kernel.ts et de server/start/routes/utilisateurs.ts :
  1. Serveur (server.use, toutes les requêtes, même sans route) :
     force_json_response → container_bindings → cors.
  2. Routeur (router.use, requêtes qui ont une route) :
     bodyparser → session → shield → initialize_auth → silent_auth.
  3. Route (middlewares nommés) : auth() puis contract(). On ne valide pas le
     corps d'une requête qu'on va rejeter en 401.
  4. Le cœur : contrôleur → service → Lucid → PostgreSQL.
  5. Le retour : la réponse repasse par contract(), qui la valide (500 si elle
     viole le contrat ; en production, un simple log).
  6. Où chercher un bug : 401, 400, 403/404/409, 500.

À droite, le fichier source de chaque couche, la ligne en cours surlignée.
Deux extraits sont remis en forme sur plusieurs lignes (signalé dans l'étiquette
du panneau) pour rester lisibles.

Sources : server/start/kernel.ts:18-56, server/start/routes.ts (en-tête),
server/start/routes/utilisateurs.ts:22-24, server/app/middleware/*.ts,
server/app/controllers/utilisateurs_controller.ts:34-37,
server/app/services/utilisateurs_service.ts:183-216, server/config/cors.ts,
server/config/shield.ts, server/config/auth.ts, server/app/exceptions/handler.ts.

Rendu vidéo :  manimgl ep10_middlewares.py Ep10Middlewares -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


SERVER_C = BLUE
ROUTER_C = VIOLET
ROUTE_C = ACCENT
CORE_C = GOLD

# Colonne de gauche : l'oignon. Colonne de droite : le code.
OUTER = (-6.95, -1.45)
INSET = 0.15
ROW_H = 0.32
PANEL_CENTER_X = 2.85
PANEL_W = 8.0

SOURCES = {
    "server": (
        "start/kernel.ts", "lignes 25-29",
        "server.use([\n"
        "  () => import('#middleware/force_json_response_middleware'),\n"
        "  () => import('#middleware/container_bindings_middleware'),\n"
        "  () => import('@adonisjs/cors/cors_middleware'),\n"
        "])",
    ),
    "router": (
        "start/kernel.ts", "lignes 35-41",
        "router.use([\n"
        "  () => import('@adonisjs/core/bodyparser_middleware'),\n"
        "  () => import('@adonisjs/session/session_middleware'),\n"
        "  () => import('@adonisjs/shield/shield_middleware'),\n"
        "  () => import('@adonisjs/auth/initialize_auth_middleware'),\n"
        "  () => import('#middleware/silent_auth_middleware'),\n"
        "])",
    ),
    "route": (
        "start/routes/utilisateurs.ts", "l. 22-24, mis en forme",
        "router\n"
        "  .patch('/utilisateurs/:id', [controllers.Utilisateurs, 'modifier'])\n"
        "  .use([\n"
        "    middleware.auth(),\n"
        "    middleware.contract({ operationId: 'modifierUtilisateur' }),\n"
        "  ])",
    ),
    "core": (
        "app/controllers/utilisateurs_controller.ts", "lignes 34-37",
        "/** modifierUtilisateur — PATCH /utilisateurs/:id */\n"
        "async modifier({ params, request, auth }: HttpContext) {\n"
        "  return utilisateursService.modifier(params.id, request.body(), auth.getUserOrFail())\n"
        "}",
    ),
    "retour": (
        "app/middleware/contract_middleware.ts", "l. 96-112, extrait",
        "await next()\n"
        "…\n"
        "const contenu = ctx.response.content\n"
        "if (!contenu) return\n"
        "\n"
        "try {\n"
        "  validateurDeContrat.validerReponse(operationId, ctx.response.getStatus(), contenu[0])",
    ),
}


def layer_box(x0, x1, y_top, y_bot, color, title):
    box = RoundedRectangle(width=x1 - x0, height=y_top - y_bot, corner_radius=0.14)
    box.move_to([(x0 + x1) / 2, (y_top + y_bot) / 2, 0])
    box.set_fill(color, 0.05).set_stroke(color, 1.8)
    t = label(title, 14, color, bold=True)
    t.move_to([x0 + 0.15 + t.get_width() / 2, y_top - 0.17, 0])
    return VGroup(box, t)


def mw_row(name, x0, x1, y, color):
    box = RoundedRectangle(width=x1 - x0, height=ROW_H, corner_radius=0.07)
    box.move_to([(x0 + x1) / 2, y, 0]).set_fill(PANEL_BG, 1).set_stroke(color, 1, opacity=0.6)
    t = label(name, 15, TXT, font=MONO_FONT)
    t.move_to([x0 + 0.15 + t.get_width() / 2, y, 0])
    row = VGroup(box, t)
    row.box = box
    return row


class Ep10Middlewares(EpisodeScene):
    EPISODE = "10"
    TITLE = "Le voyage d'une requête"

    def construct(self):
        self.build()
        self.depart()
        self.couche("server", SERVER_C, [
            ("force la réponse en JSON", "réécrit l'en-tête Accept : application/json"),
            ("lie HttpContext et Logger", "au conteneur, le temps de cette requête"),
            ("en-têtes CORS", "toutes origines en dev, aucune ailleurs"),
        ], "Couche 1 : le serveur")
        self.couche("router", ROUTER_C, [
            ("lit le corps", "le JSON envoyé devient request.body()"),
            ("session", "héritée du starter kit : l'API n'utilise que des jetons"),
            ("en-têtes de sécurité", "HSTS, X-Frame-Options (CSRF désactivé)"),
            ("prépare ctx.auth", "garde par défaut : api, jetons opaques"),
            ("auth.check()", "identifie le jeton s'il y en a un, sans jamais rejeter"),
        ], "Couche 2 : le routeur")
        self.couche("route", ROUTE_C, [
            ("auth() : pas de jeton valide → 401", "authenticateUsing() avec le garde api"),
            ("contract() : params, query et corps", "validés par Ajv avant le contrôleur, sinon 400"),
        ], "Couche 3 : la route")
        self.coeur()
        self.retour()
        self.ou_chercher()

    # --- construction de l'oignon -------------------------------------------------

    def build(self):
        x0, x1 = OUTER
        rx0, rx1 = x0 + INSET, x1 - INSET
        tx0, tx1 = rx0 + INSET, rx1 - INSET

        outer = layer_box(x0, x1, 2.72, -3.3, SERVER_C, "serveur · server.use() · toutes les requêtes")
        router = layer_box(rx0, rx1, 1.2, -3.15, ROUTER_C, "routeur · router.use() · requêtes routées")
        route = layer_box(tx0, tx1, -1.08, -3.0, ROUTE_C, "route · .use([…])")

        def rows(names, ys, xa, xb, color):
            return [mw_row(n, xa + 0.12, xb - 0.12, y, color) for n, y in zip(names, ys)]

        self.rows = {
            "server": rows(["force_json_response", "container_bindings", "cors"],
                           [2.2, 1.83, 1.46], x0, x1, SERVER_C),
            "router": rows(["bodyparser", "session", "shield", "initialize_auth", "silent_auth"],
                           [0.68, 0.31, -0.06, -0.43, -0.8], rx0, rx1, ROUTER_C),
            "route": rows(["auth()", "contract({ operationId })"],
                          [-1.6, -1.97], tx0, tx1, ROUTE_C),
        }
        core_names = ["contrôleur", "service", "Lucid", "PostgreSQL"]
        core = VGroup()
        cw = (tx1 - tx0 - 0.24 - 3 * 0.22) / 4
        for i, n in enumerate(core_names):
            b = RoundedRectangle(width=cw, height=0.48, corner_radius=0.08)
            b.set_fill(CORE_C, 0.1).set_stroke(CORE_C, 1.5)
            b.move_to([tx0 + 0.12 + cw / 2 + i * (cw + 0.22), -2.55, 0])
            t = label(n, 13, CORE_C, bold=True)
            if t.get_width() > cw - 0.1:
                t.set_width(cw - 0.1)
            t.move_to(b)
            core.add(VGroup(b, t))
        arrows = VGroup(*[
            Arrow(core[i][0].get_right(), core[i + 1][0].get_left(), buff=0.02, thickness=1.5)
            .set_color(CORE_C) for i in range(3)
        ])
        self.layers = dict(server=outer, router=router, route=route)
        self.core = core
        self.core_arrows = arrows
        self.packet_x = OUTER[1] - 0.55

    def depart(self):
        self.show_chip("PATCH /api/v1/utilisateurs/:id")
        req = label('PATCH /api/v1/utilisateurs/:id  ·  Authorization: Bearer oat_…  ·  { "nom": "…" }',
                    15, BLUE, font=MONO_FONT)
        if req.get_width() > PANEL_W - 0.3:
            req.set_width(PANEL_W - 0.3)
        req_bg = RoundedRectangle(width=PANEL_W, height=0.5, corner_radius=0.1)
        req_bg.set_fill(BLUE, 0.08).set_stroke(BLUE, 1.2).move_to([PANEL_CENTER_X, 2.47, 0])
        req.move_to(req_bg)
        self.play(FadeIn(req_bg), FadeIn(req), run_time=0.6)

        all_rows = [r for k in ("server", "router", "route") for r in self.rows[k]]
        self.play(FadeIn(self.layers["server"]), run_time=0.4)
        self.play(FadeIn(self.layers["router"]), run_time=0.4)
        self.play(FadeIn(self.layers["route"]), run_time=0.4)
        self.play(LaggedStartMap(FadeIn, VGroup(*all_rows), lag_ratio=0.06),
                  FadeIn(self.core), FadeIn(self.core_arrows), run_time=1.2)
        hint = label("trois couches, de l'extérieur vers l'intérieur", 19, TXT)
        hint.move_to([PANEL_CENTER_X, 0.5, 0])
        self.play(FadeIn(hint), run_time=0.5)
        self.wait(1.4)
        self.play(FadeOut(hint), run_time=0.3)

        self.packet = packet(BLUE, 0.09).move_to([self.packet_x, 2.5, 0])
        self.play(FadeIn(self.packet, scale=2), run_time=0.3)
        self.panel = None
        self.caps = VGroup()

    # --- le panneau de code de droite ---------------------------------------------

    def show_source(self, key, color):
        fname, tag, src = SOURCES[key]
        panel = EditorPanel(fname, np.array([PANEL_CENTER_X, 0.4, 0]), width=PANEL_W, height=3.45,
                            tag=tag, tag_color=color)
        view = CodeView(src, ["typescript"])
        panel.fit_code(view, max_scale=0.95)
        anims = [FadeIn(panel.chrome), FadeIn(view.group)]
        if self.panel is not None:
            anims += [FadeOut(self.panel[0].chrome), FadeOut(self.panel[1].group)]
            if self.panel[2] is not None:
                anims.append(FadeOut(self.panel[2]))
        self.play(*anims, run_time=0.6)
        self.panel = [panel, view, None]

    def mark_line(self, line, color):
        rect = highlight_rect(self.panel[1].line_box(line), color, 0.16)
        if self.panel[2] is None:
            self.play(FadeIn(rect), run_time=0.3)
        else:
            self.play(Transform(self.panel[2], rect), run_time=0.3)
            return
        self.panel[2] = rect

    def caption(self, title, sub, color):
        t = label(title, 20, color, bold=True)
        s = label(sub, 16, TXT)
        for m in (t, s):
            if m.get_width() > PANEL_W - 0.2:
                m.set_width(PANEL_W - 0.2)
        g = VGroup(t, s).arrange(DOWN, buff=0.14).move_to([PANEL_CENTER_X, -2.05, 0])
        self.play(FadeOut(self.caps), FadeIn(g, shift=0.08 * UP), run_time=0.4)
        self.caps = g

    # --- les trois couches ----------------------------------------------------------

    def couche(self, key, color, notes, chip):
        self.show_chip(chip, color)
        self.show_source(key, color)
        first_code_line = {"server": 2, "router": 2, "route": 4}[key]
        for i, (row, (title, sub)) in enumerate(zip(self.rows[key], notes)):
            y = row.get_center()[1]
            self.play(self.packet.animate.move_to([self.packet_x, y, 0]), run_time=0.45)
            self.play(row.box.animate.set_fill(color, 0.3).set_stroke(color, 2, opacity=1),
                      run_time=0.25)
            self.mark_line(first_code_line + i, color)
            self.caption(title, sub, color)
            self.wait(1.7 if key == "route" else 1.5)
            tick = label("✓", 16, color, bold=True).move_to([OUTER[1] - 0.95, y, 0])
            self.play(row.box.animate.set_fill(PANEL_BG, 1).set_stroke(color, 1, opacity=0.6),
                      FadeIn(tick), run_time=0.25)

        if key == "server":
            note = label("cette couche tourne même pour une URL sans route (404)", 16, DIM)
            note.move_to([PANEL_CENTER_X, -2.95, 0])
            self.play(FadeIn(note), run_time=0.4)
            self.wait(1.4)
            self.play(FadeOut(note), run_time=0.3)
        if key == "route":
            why = label("auth() AVANT contract() : inutile de valider le corps", 17, ACCENT, bold=True)
            why2 = label("d'une requête qu'on va rejeter en 401 (start/routes.ts)", 17, ACCENT)
            g = VGroup(why, why2).arrange(DOWN, buff=0.08).move_to([PANEL_CENTER_X, -3.15, 0])
            self.play(FadeIn(g, shift=0.08 * UP), run_time=0.5)
            self.wait(2.4)
            self.play(FadeOut(g), run_time=0.3)

    # --- le cœur -----------------------------------------------------------------------

    def coeur(self):
        self.show_chip("Le cœur : contrôleur, service, base", CORE_C)
        self.show_source("core", CORE_C)
        self.play(self.packet.animate.move_to(self.core[0].get_center()), run_time=0.5)
        self.mark_line(3, CORE_C)
        self.caption("le contrôleur ne fait que du HTTP", "il passe params.id, le corps et l'auteur au service",
                     CORE_C)
        self.wait(1.2)
        for i in range(1, 4):
            self.play(self.packet.animate.move_to(self.core[i].get_center()),
                      Indicate(self.core[i], color=CORE_C, scale_factor=1.08), run_time=0.5)
        self.caption("service.modifier : 403 avant 404, find(), save()",
                     "puis versContrat() : la projection publique (épisode 11)", CORE_C)
        self.wait(2.0)

    # --- le retour ----------------------------------------------------------------------

    def retour(self):
        self.show_chip("Le retour : contract() valide la réponse", ACCENT)
        self.show_source("retour", ACCENT)
        resp = packet(ACCENT, 0.09).move_to(self.packet.get_center())
        self.remove(self.packet)
        self.add(resp)
        contract_row = self.rows["route"][1]
        y = contract_row.get_center()[1]
        self.play(resp.animate.move_to([self.packet_x, y, 0]), run_time=0.6)
        self.play(contract_row.box.animate.set_fill(ACCENT, 0.3).set_stroke(ACCENT, 2, opacity=1),
                  run_time=0.25)
        self.mark_line(7, ACCENT)
        self.caption("la réponse est validée contre le contrat",
                     "non conforme : 500 CONTRACT_RESPONSE_VIOLATION (en production : un log)", ACCENT)
        self.wait(2.8)
        self.play(contract_row.box.animate.set_fill(PANEL_BG, 1).set_stroke(ACCENT, 1, opacity=0.6),
                  run_time=0.25)
        self.play(resp.animate.move_to([self.packet_x, 2.5, 0]), run_time=0.9)
        out = label("200  { id, email, nom, role, createdAt }", 16, ACCENT, font=MONO_FONT, bold=True)
        out.move_to([PANEL_CENTER_X, 2.47, 0])
        req_mobs = [m for m in self.mobjects if m not in self.permanent and m is not self.chip
                    and abs(m.get_center()[1] - 2.47) < 0.05 and m.get_center()[0] > 0]
        self.play(*[FadeOut(m) for m in req_mobs], FadeIn(out), FadeOut(resp), run_time=0.5)
        self.wait(1.4)
        self.clear_stage()

    # --- où chercher un bug --------------------------------------------------------------

    def ou_chercher(self):
        self.show_chip("Où chercher un bug ?")
        rows = [
            ("401  UNAUTHORIZED", "auth(), sur la route : jeton absent ou invalide", ROUTE_C),
            ("400  VALIDATION_ERROR", "contract(), à l'entrée : la requête viole le contrat", ROUTE_C),
            ("403 · 404 · 409", "le service : une règle métier (puis le handler d'erreurs)", CORE_C),
            ("500  CONTRACT_RESPONSE_VIOLATION", "contract(), au retour : regarder versContrat()", ERROR),
            ("CORS, en-têtes, JSON", "les couches serveur et routeur : start/kernel.ts", SERVER_C),
        ]
        table = VGroup()
        for code, where, color in rows:
            c = label(code, 18, color, font=MONO_FONT, bold=True)
            w = label(where, 18, TXT).next_to(c, RIGHT, buff=0.5)
            table.add(VGroup(c, w))
        width = max(r[0].get_width() for r in table)
        table.arrange(DOWN, aligned_edge=LEFT, buff=0.32)
        for r in table:
            r[1].align_to(table[0][0], LEFT).shift((width + 0.5) * RIGHT)
        table.move_to([0, -0.1, 0])
        bg = SurroundingRectangle(table, buff=0.35).set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
        self.play(FadeIn(bg), LaggedStartMap(FadeIn, table, shift=0.1 * RIGHT, lag_ratio=0.2),
                  run_time=1.8)
        self.wait(3.5)
        next_ep = label("épisode suivant : contrôleur mince, service épais  →", 15, DIM)
        next_ep.to_corner(DR, buff=0.35)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(1.5)
