"""
Épisode 2 — La carte de l'architecture : plein = existe, pointillé = décidé

Une seule image mentale du système, réutilisée en ouverture des épisodes suivants.
  1. Le dépôt : six dossiers, et ce que chacun contient.
  2. Le contrat au centre : le serveur et le SDK en dérivent, rien ne remonte.
  3. Le SDK alimente le back-office (existe) et l'app mobile (à créer).
  4. Le serveur et sa base PostgreSQL.
  5. Les clients parlent au serveur en HTTP (JSON, jeton Bearer, /api/v1).
  6. Ce qui est décidé mais pas encore codé : photos sur R2, file de messages,
     email, push Expo ; et Traefik, déclaré mais qui ne route rien.
  7. Les épisodes de la série, posés sur la carte.

Sources : CLAUDE.md (Structure), contract/openapi.yaml (en-tête), docker-compose.yml,
server/start/routes.ts, docs/adr/0014, 0015, 0016, docs/adr/README.md.

Rendu vidéo :  manimgl ep02_carte_architecture.py Ep02CarteArchitecture -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


POSTGRES = "#5B9BD5"

# Disposition finale de la carte (tout est placé dès le départ)
POS = dict(
    contract=np.array([0.0, 1.85, 0]),
    server=np.array([-2.4, -0.1, 0]),
    postgres=np.array([-2.4, -2.1, 0]),
    sdk=np.array([2.6, -0.1, 0]),
    web=np.array([1.9, -2.1, 0]),
    app=np.array([4.4, -2.1, 0]),
    r2=np.array([5.85, -0.1, 0]),
    queue=np.array([-5.6, -0.1, 0]),
    email=np.array([-5.6, 1.7, 0]),
    push=np.array([-5.6, -2.0, 0]),
    traefik=np.array([-0.6, -1.3, 0]),
)

HTTP_X = -0.6      # le « tronc » vertical du bus HTTP
BUS_Y = -3.15      # le bus HTTP, sous les clients
PUSH_Y = -3.6      # la ligne des notifications push, sous le bus


def polyline(points, color, width=2.2, planned=False):
    """Une ligne brisée, pleine ou pointillée, sans pointe."""
    path = VMobject().set_points_as_corners([np.array(p) for p in points])
    if planned:
        path = dashed(path)
    return path.set_stroke(color, width, opacity=0.9 if planned else 1)


def tip_at(point, direction, color):
    tip = ArrowTip().set_fill(color, 1).set_stroke(width=0).scale(0.6)
    tip.rotate(np.arctan2(direction[1], direction[0]))
    return tip.move_to(np.array(point) - direction * tip.get_width() / 2)


def caption(text, point, color=DIM, size=14):
    return label(text, size, color).move_to(point)


class Ep02CarteArchitecture(EpisodeScene):
    EPISODE = "02"
    TITLE = "La carte de l'architecture"

    def construct(self):
        self.nodes = self.build_nodes()
        self.depot()
        self.contrat()
        self.clients()
        self.base()
        self.http()
        self.prevu()
        self.episodes()

    # --- les nœuds ----------------------------------------------------------

    def build_nodes(self):
        n = dict(
            contract=node("contract/", "OpenAPI 3.1 · écrit à la main", ACCENT, width=3.2),
            server=node("server/", "AdonisJS · valide le contrat", VIOLET, width=2.6),
            postgres=node("PostgreSQL 16", "conteneur Docker", POSTGRES, width=2.6),
            sdk=node("sdk/", "généré par Orval", GOLD, width=2.4),
            web=node("clients/web", "back-office React", BLUE, width=2.2),
            app=node("clients/app", "mobile Expo · à créer", BLUE, width=2.2, planned=True),
            r2=node("Cloudflare R2", "photos", DIM, width=1.9, planned=True,
                    title_size=19),
            queue=node("File de messages", "@adonisjs/queue", WARN, width=2.1,
                       planned=True, title_size=17, subtitle_size=13),
            email=node("Email", "fournisseur à choisir", DIM, width=2.1, planned=True,
                       title_size=19, subtitle_size=13),
            push=node("Push Expo", "notifications", DIM, width=2.1, planned=True,
                      title_size=19, subtitle_size=13),
            traefik=node("Traefik", "ne route rien", DIM, width=1.4, planned=True,
                         title_size=15, subtitle_size=11),
        )
        for key, mob in n.items():
            mob.move_to(POS[key])
        return n

    # --- 1. Le dépôt ----------------------------------------------------------

    def depot(self):
        self.show_chip("Le dépôt")
        rows = [
            ("contract/", "le contrat de l'API, écrit à la main", ACCENT, "contract"),
            ("sdk/", "client HTTP, hooks et mocks, générés", GOLD, "sdk"),
            ("server/", "le serveur AdonisJS", VIOLET, "server"),
            ("clients/web", "le back-office de l'association", BLUE, "web"),
            ("clients/app", "l'application mobile (à créer)", DIM, "app"),
            ("docs/", "contexte, décisions (ADR), exigences", DIM, None),
        ]
        tree = VGroup()
        for folder, desc, color, _ in rows:
            f = label(folder, 22, color, font=MONO_FONT, bold=True)
            d = label(desc, 18, DIM)
            tree.add(VGroup(f, d))
        for row in tree:
            row[1].next_to(row[0], RIGHT, buff=0.5)
        tree.arrange(DOWN, aligned_edge=LEFT, buff=0.24)
        width = max(r[0].get_width() for r in tree)
        for row in tree:
            row[1].align_to(tree[0][0], LEFT).shift((width + 0.6) * RIGHT)
        tree.move_to([0, -0.2, 0])
        panel = SurroundingRectangle(tree, buff=0.35).set_fill(PANEL_BG, 1).set_stroke(PANEL_STROKE, 1.5)
        self.play(FadeIn(panel), LaggedStartMap(FadeIn, tree, shift=0.15 * RIGHT, lag_ratio=0.15),
                  run_time=1.6)
        self.wait(2.2)

        # Chaque dossier rejoint sa place sur la carte
        self.show_chip("Où vit chaque morceau ?")
        anims = []
        for row, (_, _, _, key) in zip(tree, rows):
            if key is None:
                continue
            anims.append(FadeTransform(row[0].copy(), self.nodes[key]))
        self.play(FadeOut(panel), FadeOut(tree), *anims, run_time=1.6)
        self.wait(0.6)

    # --- 2. Le contrat au centre ----------------------------------------------

    def contrat(self):
        self.show_chip("Le contrat au centre")
        n = self.nodes
        self.play(Indicate(n["contract"], color=ACCENT, scale_factor=1.06), run_time=0.8)

        to_server = link(edge_point(n["contract"], DL), edge_point(n["server"], UP), ACCENT)
        to_sdk = link(edge_point(n["contract"], DR), edge_point(n["sdk"], UP), ACCENT)
        cap_server = caption("validation Ajv + types", to_server.get_center() + np.array([-1.35, 0.1, 0]))
        cap_sdk = caption("client, hooks, mocks", to_sdk.get_center() + np.array([1.3, 0.1, 0]))
        self.play(GrowArrow(to_server), GrowArrow(to_sdk), run_time=0.9)
        self.play(FadeIn(cap_server), FadeIn(cap_sdk), run_time=0.5)

        # Rien ne remonte vers le contrat
        back = link(edge_point(n["server"], UR) + 0.15 * RIGHT, edge_point(n["contract"], LEFT),
                    ERROR, planned=True)
        cross = label("✖", 30, ERROR, bold=True).move_to(back.get_center())
        rule = caption("rien ne remonte vers le contrat : on corrige le YAML, jamais le code généré",
                       [0, 2.62, 0], TXT, 16)
        self.play(ShowCreation(back), run_time=0.8)
        self.play(FadeIn(cross, scale=1.6), FadeIn(rule), run_time=0.5)
        self.wait(1.6)
        self.play(FadeOut(back), FadeOut(cross), FadeOut(rule), run_time=0.5)
        self.contract_links = VGroup(to_server, to_sdk, cap_server, cap_sdk)

    # --- 3. Le SDK alimente les clients ------------------------------------------

    def clients(self):
        self.show_chip("Le SDK alimente les clients", GOLD)
        n = self.nodes
        to_web = link(edge_point(n["sdk"], DOWN) + 0.3 * LEFT, edge_point(n["web"], UP), GOLD)
        to_app = link(edge_point(n["sdk"], DOWN) + 0.3 * RIGHT, edge_point(n["app"], UP), GOLD,
                      planned=True)
        self.play(GrowArrow(to_web), run_time=0.7)
        self.play(ShowCreation(to_app), run_time=0.7)
        note = caption("aucun fetch écrit à la main : les fronts n'appellent que le SDK",
                       [3.2, -3.0, 0], TXT, 15)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(1.6)
        self.play(FadeOut(note), run_time=0.4)
        self.sdk_links = VGroup(to_web, to_app)

    # --- 4. La base ---------------------------------------------------------------

    def base(self):
        self.show_chip("Le serveur et sa base", VIOLET)
        n = self.nodes
        top = edge_point(n["server"], DOWN) + 0.08 * DOWN
        bottom = edge_point(n["postgres"], UP) + 0.08 * UP
        db = VGroup(
            Line(top, bottom).set_stroke(POSTGRES, 2.2),
            tip_at(top, UP, POSTGRES),
            tip_at(bottom, DOWN, POSTGRES),
        )
        cap = caption("Lucid · migrations", db.get_center() + 1.05 * LEFT)
        self.play(FadeIn(n["postgres"], shift=0.2 * UP), run_time=0.6)
        self.play(GrowFromCenter(db), FadeIn(cap), run_time=0.8)
        self.wait(1.0)
        self.db_link = VGroup(db, cap)

    # --- 5. HTTP -------------------------------------------------------------------

    def http(self):
        self.show_chip("Les clients parlent au serveur en HTTP", BLUE)
        n = self.nodes
        web_bottom = edge_point(n["web"], DOWN)
        app_bottom = edge_point(n["app"], DOWN)
        server_right = edge_point(n["server"], RIGHT)

        bus_points = [
            web_bottom, [web_bottom[0], BUS_Y, 0], [HTTP_X, BUS_Y, 0],
            [HTTP_X, server_right[1], 0], server_right + 0.08 * RIGHT,
        ]
        bus = polyline(bus_points, BLUE, 2.6)
        bus_tip = tip_at(server_right + 0.08 * RIGHT, LEFT, BLUE)
        app_branch = polyline([app_bottom, [app_bottom[0], BUS_Y, 0], [web_bottom[0], BUS_Y, 0]],
                              BLUE, 2.2, planned=True)
        cap = caption("HTTP · JSON · Authorization: Bearer · /api/v1",
                      [2.2, BUS_Y + 0.25, 0], BLUE, 15)
        self.play(ShowCreation(bus), run_time=1.2)
        self.play(FadeIn(bus_tip), ShowCreation(app_branch), FadeIn(cap), run_time=0.8)

        # Quelques requêtes font l'aller-retour
        path = VMobject().set_points_as_corners([np.array(p) for p in bus_points])
        back_path = path.copy().reverse_points()
        for _ in range(2):
            go = packet(BLUE)
            ret = packet(ACCENT)
            self.play(MoveAlongPath(go, path), run_time=1.0, rate_func=linear)
            self.remove(go)
            self.play(Flash(server_right, color=BLUE, line_length=0.15, flash_radius=0.25),
                      run_time=0.3)
            self.play(MoveAlongPath(ret, back_path), run_time=1.0, rate_func=linear)
            self.remove(ret)
        self.http_links = VGroup(bus, bus_tip, app_branch, cap)

    # --- 6. Ce qui est décidé, pas encore codé ----------------------------------

    def prevu(self):
        self.show_chip("Plein = existe  ·  Pointillé = décidé, pas encore codé", DIM)
        n = self.nodes

        # Légende
        solid = Line(ORIGIN, 0.6 * RIGHT).set_stroke(TXT, 2.5)
        dash = dashed(Line(ORIGIN, 0.6 * RIGHT), num_dashes=5).set_stroke(TXT, 2.5)
        legend = VGroup(
            VGroup(solid, label("existe dans le dépôt", 15)).arrange(RIGHT, buff=0.2),
            VGroup(dash, label("décidé (ADR), pas encore codé", 15)).arrange(RIGHT, buff=0.2),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).move_to([4.9, 2.0, 0])
        self.play(FadeIn(legend), Indicate(n["app"], color=BLUE, scale_factor=1.06), run_time=0.9)

        # Photos : le téléphone envoie directement au stockage objet (ADR 0016)
        r2_link = link(edge_point(n["app"], UR), edge_point(n["r2"], DOWN), DIM, planned=True)
        r2_cap = caption("envoi direct, par URL signée", [6.0, -1.15, 0], DIM, 13)
        self.play(FadeIn(n["r2"]), ShowCreation(r2_link), FadeIn(r2_cap), run_time=1.0)
        self.wait(0.8)

        # La file de messages : le serveur publie, un worker traite plus tard
        q_link = link(edge_point(n["server"], LEFT), edge_point(n["queue"], RIGHT), WARN, planned=True)
        q_cap = caption("événements", q_link.get_center() + 0.42 * UP, WARN, 12)
        self.play(FadeIn(n["queue"]), ShowCreation(q_link), FadeIn(q_cap), run_time=1.0)
        to_email = link(edge_point(n["queue"], UP), edge_point(n["email"], DOWN), DIM, planned=True)
        to_push = link(edge_point(n["queue"], DOWN), edge_point(n["push"], UP), DIM, planned=True)
        self.play(FadeIn(n["email"]), FadeIn(n["push"]), ShowCreation(to_email), ShowCreation(to_push),
                  run_time=1.0)
        idea = caption("le serveur répond tout de suite ; l'envoi se fait en arrière-plan",
                       [-4.3, 2.62, 0], TXT, 15)
        self.play(FadeIn(idea), run_time=0.5)

        # Le push arrive sur le téléphone
        push_bottom = edge_point(n["push"], DOWN)
        app_bottom = edge_point(n["app"], DOWN)
        push_line = polyline([push_bottom, [push_bottom[0], PUSH_Y, 0], [app_bottom[0] + 0.5, PUSH_Y, 0],
                              [app_bottom[0] + 0.5, app_bottom[1] - 0.08, 0]], DIM, 1.8, planned=True)
        push_tip = tip_at([app_bottom[0] + 0.5, app_bottom[1] - 0.08, 0], UP, DIM)
        self.play(ShowCreation(push_line), FadeIn(push_tip), run_time=1.2)
        self.wait(1.4)
        self.play(FadeOut(idea), run_time=0.4)

        # Traefik : déclaré dans docker-compose, ne route rien
        self.play(FadeIn(n["traefik"], scale=0.8), run_time=0.6)
        self.play(n["traefik"].animate.set_opacity(0.45), run_time=0.6)
        self.wait(1.2)

    # --- 7. Les épisodes sur la carte -----------------------------------------------

    def episodes(self):
        self.show_chip("La carte des épisodes")
        n = self.nodes

        def badge(text, color, anchor, direction):
            t = label(text, 14, BG, bold=True)
            bg = RoundedRectangle(width=t.get_width() + 0.26, height=0.3, corner_radius=0.15)
            bg.set_fill(color, 1).set_stroke(width=0)
            t.move_to(bg)
            group = VGroup(bg, t)
            group.next_to(edge_point(anchor, direction), direction, buff=0.08)
            return group

        badges = VGroup(
            badge("épisodes 5 à 8", ACCENT, n["contract"], LEFT),
            badge("9 à 19", VIOLET, n["server"], UP),
            badge("20 à 24", BLUE, n["web"], LEFT),
            badge("25 à 38", BLUE, n["app"], RIGHT),
            badge("39", WARN, n["queue"], UP),
        )
        for b in badges:
            fit_x(b)
        self.play(LaggedStartMap(FadeIn, badges, scale=0.6, lag_ratio=0.2), run_time=1.4)
        outro = caption("cette carte ouvrira chaque épisode : on zoomera sur la zone concernée",
                        [0, 2.62, 0], TXT, 16)
        self.play(FadeIn(outro), run_time=0.6)
        self.wait(3)
