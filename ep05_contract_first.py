"""
Épisode 5 — Un YAML, quatre consommateurs, et le fil des EXG

Le modèle mental du contract-first : une seule source est écrite à la main,
tout le reste en est dérivé. C'est un zoom sur le nœud « contract/ » de la
carte de l'épisode 2.
  1. Zoom sur la carte : le contrat au centre.
  2. Une source, quatre dérivés : le YAML est assemblé en dist/openapi.json,
     puis le serveur en tire la validation Ajv et types.ts, le SDK (Orval) en
     tire le client + les hooks React Query et les mocks MSW.
  3. Rien ne remonte : une flèche code → YAML se brise. « Un type partagé
     absent du contrat est un bug du contrat » : on corrige le YAML, puis
     `npm run sync` régénère tout.
  4. Le fil des EXG : EXG-USR-004 est recopié tel quel dans la spécification,
     la description de l'opération et le libellé du test ; un grep suffit à
     retrouver tous les endroits qui le portent.

Sources : docs/adr/0001-contrat-openapi-source-unique.md, contract/openapi.yaml
(en-tête), contract/package.json, sdk/orval.config.ts, sdk/src/msw.ts,
server/scripts/sync-contract.mjs, server/package.json (sync:contract),
server/app/services/contract_validator.ts, server/app/services/utilisateurs_service.ts,
clients/web/src/utilisateurs/utilisateurs-page.tsx, .gitignore,
docs/specs/utilisateurs.md, contract/features/utilisateurs/paths/utilisateurs.yaml,
server/tests/functional/utilisateurs.spec.ts.

Rendu vidéo :  manimgl ep05_contract_first.py Ep05ContractFirst -w
"""

import sys
from pathlib import Path

# manimgl n'ajoute pas le dossier du script au chemin d'import : on le fait
# pour pouvoir importer les briques partagées de cmc_style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmc_style import *  # noqa: E402


LEAF_Y = -1.45
LEAF_X = (-5.25, -1.75, 1.75, 5.25)
DIVIDER_Y = 1.25


def caption(text, point, color=DIM, size=15):
    return label(text, size, color).move_to(point)


def code_panel(filename, source, lexer, center, width, height, tag=None, tag_color=DIM,
               gutter=False):
    """Un EditorPanel et son CodeView, déjà ajusté."""
    panel = EditorPanel(filename, center, width=width, height=height, tag=tag, tag_color=tag_color)
    view = CodeView(source, [lexer], gutter=gutter)
    panel.fit_code(view, max_scale=1.0)
    return panel, view


class Ep05ContractFirst(EpisodeScene):
    EPISODE = "05"
    TITLE = "Un YAML, quatre consommateurs"

    def construct(self):
        self.zoom()
        self.derives()
        self.rien_ne_remonte()
        self.fil_exg()

    # --- 1. Zoom sur la carte ---------------------------------------------------

    def zoom(self):
        self.show_chip("Zoom sur la carte de l'épisode 2")
        contract = node("contract/", "OpenAPI 3.1 · écrit à la main", ACCENT, width=3.2)
        server = node("server/", "AdonisJS", VIOLET, width=2.4)
        sdk = node("sdk/", "généré par Orval", GOLD, width=2.4)
        contract.move_to([0, 1.6, 0])
        server.move_to([-2.6, -0.6, 0])
        sdk.move_to([2.6, -0.6, 0])
        arrows = VGroup(
            link(edge_point(contract, DL), edge_point(server, UP), ACCENT),
            link(edge_point(contract, DR), edge_point(sdk, UP), ACCENT),
        )
        self.play(FadeIn(contract), FadeIn(server), FadeIn(sdk), run_time=0.8)
        self.play(*[GrowArrow(a) for a in arrows], run_time=0.7)
        cap = caption("on entre dans le nœud du contrat : qu'est-ce qui en dérive, exactement ?",
                      [0, -2.2, 0], TXT, 18)
        self.play(FadeIn(cap), Indicate(contract, color=ACCENT, scale_factor=1.06), run_time=0.9)
        self.wait(1.8)
        self.play(FadeOut(VGroup(server, sdk, arrows, cap)),
                  contract.animate.move_to([0, 2.05, 0]).set_opacity(0), run_time=0.7)
        self.remove(contract)

    # --- 2. Une source, quatre dérivés ------------------------------------------

    def derives(self):
        self.show_chip("Une seule source, quatre dérivés")

        yaml = node("contract/openapi.yaml", "+ contract/features/**/*.yaml", ACCENT, width=4.4,
                    title_size=21)
        yaml.move_to([0, 2.05, 0])
        hand = label("écrit à la main", 15, ACCENT, bold=True)
        hand.next_to(yaml, RIGHT, buff=0.35)

        # La ligne de partage : au-dessus, écrit à la main ; en dessous, dérivé
        divider = dashed(Line([-6.85, DIVIDER_Y, 0], [6.85, DIVIDER_Y, 0]), num_dashes=70)
        divider.set_stroke(DIM, 1.2, opacity=0.7)
        derived_lbl = label("dérivé : régénéré par npm run sync, non versionné, jamais édité",
                            14, DIM).move_to([0, DIVIDER_Y - 0.22, 0])
        derived_lbl.align_to([-6.85, 0, 0], LEFT)

        self.play(FadeIn(yaml, shift=0.15 * DOWN), run_time=0.7)
        self.play(FadeIn(hand, shift=0.1 * LEFT), run_time=0.5)
        self.wait(0.6)

        bundle = node("contract/dist/openapi.json", "le bundle : un seul JSON", TXT, width=3.9,
                      title_size=19)
        bundle.move_to([0, 0.3, 0])
        to_bundle = link(edge_point(yaml, DOWN), edge_point(bundle, UP), ACCENT)
        tool = label("redocly bundle  ·  spectral lint", 14, DIM, font=MONO_FONT)
        tool.next_to(to_bundle, RIGHT, buff=0.25)
        self.play(ShowCreation(divider), FadeIn(derived_lbl), run_time=0.8)
        self.play(GrowArrow(to_bundle), FadeIn(bundle, shift=0.1 * DOWN), FadeIn(tool), run_time=0.9)
        self.wait(0.8)

        specs = [
            ("Ajv", "contract_validator.ts", VIOLET, "validerRequete(operationId, …)"),
            ("types.ts", "openapi-typescript", VIOLET, "components['schemas']['Utilisateur']"),
            ("client + hooks", "Orval · endpoints/", GOLD, "useListerUtilisateurs({ page, … })"),
            ("mocks MSW", "Orval · *.msw.ts", GOLD, "getListerUtilisateursMockHandler"),
        ]
        roles = [
            "valide requêtes et réponses",
            "type les services",
            "les fronts n'appellent qu'eux",
            "le front tourne sans serveur",
        ]
        leaves, arrows, examples, roles_mobs = VGroup(), VGroup(), VGroup(), VGroup()
        for x, (title, sub, color, example), role in zip(LEAF_X, specs, roles):
            leaf = node(title, sub, color, width=3.2, title_size=20, subtitle_size=14)
            leaf.move_to([x, LEAF_Y, 0])
            leaves.add(leaf)
            arrows.add(link(edge_point(bundle, DOWN), edge_point(leaf, UP), color))
            ex = label(example, 14, TXT, font=MONO_FONT)
            if ex.get_width() > 3.25:
                ex.set_width(3.25)
            ex.next_to(leaf, DOWN, buff=0.22)
            examples.add(ex)
            roles_mobs.add(label(role, 14, DIM).next_to(ex, DOWN, buff=0.14))

        # Les deux familles : côté serveur, côté SDK
        def bracket(x0, x1, y, text, color):
            line = Line([x0, y, 0], [x1, y, 0]).set_stroke(color, 2)
            ends = VGroup(*[Line([x, y, 0], [x, y + 0.12, 0]).set_stroke(color, 2) for x in (x0, x1)])
            t = label(text, 17, color, font=MONO_FONT, bold=True).next_to(line, DOWN, buff=0.12)
            return VGroup(line, ends, t)

        server_br = bracket(-6.85, -0.15, -3.25, "server/", VIOLET)
        sdk_br = bracket(0.15, 6.85, -3.25, "sdk/", GOLD)
        copy_note = label("via une copie : server/app/contract/openapi.json", 13, DIM)
        copy_note.next_to(server_br[2], RIGHT, buff=0.3)

        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.15),
                  LaggedStartMap(FadeIn, leaves, shift=0.1 * DOWN, lag_ratio=0.15), run_time=1.4)
        self.play(FadeIn(server_br), FadeIn(sdk_br), FadeIn(copy_note), run_time=0.6)
        self.play(LaggedStartMap(FadeIn, examples, lag_ratio=0.2),
                  LaggedStartMap(FadeIn, roles_mobs, lag_ratio=0.2), run_time=1.2)
        self.wait(2.6)

        # Une génération : le YAML descend jusqu'aux quatre dérivés
        self.pulse(yaml, bundle, leaves)
        self.wait(1.4)

        self.tree = dict(yaml=yaml, bundle=bundle, leaves=leaves, arrows=arrows,
                         to_bundle=to_bundle, divider=divider)

    def pulse(self, yaml, bundle, leaves):
        """Des paquets descendent du YAML vers le bundle, puis vers chaque dérivé."""
        p = packet(ACCENT)
        self.play(MoveAlongPath(p, Line(edge_point(yaml, DOWN), edge_point(bundle, UP))),
                  run_time=0.6, rate_func=linear)
        self.remove(p)
        dots, anims = [], []
        for leaf, color in zip(leaves, (VIOLET, VIOLET, GOLD, GOLD)):
            d = packet(color)
            dots.append(d)
            anims.append(MoveAlongPath(d, Line(edge_point(bundle, DOWN), edge_point(leaf, UP))))
        self.play(*anims, run_time=0.8, rate_func=linear)
        for d in dots:
            self.remove(d)
        self.play(*[Indicate(l, color=TXT, scale_factor=1.04) for l in leaves], run_time=0.6)

    # --- 3. Rien ne remonte -------------------------------------------------------

    def rien_ne_remonte(self):
        self.show_chip("Rien ne remonte vers le contrat", ERROR)
        t = self.tree
        hooks = t["leaves"][2]

        # Quelqu'un ajoute un champ « à la main », côté code, et voudrait le remonter
        start = np.array([3.15, edge_point(hooks, UP)[1] + 0.06, 0])
        end = np.array([3.15, edge_point(t["yaml"], DOWN)[1] + 0.25, 0])
        attempt = link(start, end, ERROR, planned=True)
        who = label("« j'ajoute le champ directement dans le code »", 16, ERROR)
        who.move_to([5.05, 0.3, 0])
        fit_x(who)
        self.play(ShowCreation(attempt), FadeIn(who), run_time=1.1)

        # La flèche se brise sur la ligne de partage
        brk = np.array([3.15, DIVIDER_Y, 0])
        low = DashedLine(start, brk - 0.08 * UP, dash_length=0.09).set_stroke(ERROR, 2.2)
        high = VGroup(DashedLine(brk + 0.08 * UP, end, dash_length=0.09).set_stroke(ERROR, 2.2),
                      attempt[1].copy())
        cross = label("✖", 34, ERROR, bold=True).move_to(brk)
        self.remove(attempt)
        self.add(low, high)
        self.play(FadeIn(cross, scale=1.8),
                  high.animate.shift(0.35 * UP).set_opacity(0),
                  low.animate.shift(0.3 * DOWN).rotate(8 * DEGREES).set_opacity(0.25),
                  run_time=0.8)
        self.remove(high)

        rule = label("un type partagé absent du contrat = un bug du contrat", 22, TXT, bold=True)
        rule.move_to([0, -3.35, 0])
        sub = label("ADR 0001 : on corrige le YAML, jamais le code dérivé", 16, DIM)
        sub.next_to(rule, DOWN, buff=0.12)
        bottom = [m for m in self.mobjects if m.get_center()[1] < -3.0 and m not in self.permanent]
        self.play(*[m.animate.set_opacity(0.0) for m in bottom], run_time=0.4)
        self.play(FadeIn(rule, shift=0.1 * UP), FadeIn(sub), run_time=0.7)
        self.wait(3.0)

        # Le bon geste : on modifie le YAML, et la régénération redescend
        self.play(FadeOut(low), FadeOut(cross), FadeOut(who), run_time=0.4)
        fix = label("✔ on modifie le YAML  →  npm run sync", 17, ACCENT, bold=True)
        fix.next_to(t["yaml"], LEFT, buff=0.35)
        fit_x(fix)
        self.play(FadeIn(fix, shift=0.1 * RIGHT),
                  Indicate(t["yaml"], color=ACCENT, scale_factor=1.06), run_time=0.8)
        self.pulse(t["yaml"], t["bundle"], t["leaves"])
        self.wait(2.2)
        self.clear_stage()

    # --- 4. Le fil des EXG -------------------------------------------------------

    def fil_exg(self):
        self.show_chip("Le fil des EXG", GOLD)

        spec_src = (
            "| ID          | Exigence                                         | …\n"
            "| EXG-USR-004 | Le rôle n'est jamais attribuable à l'inscription | …"
        )
        yaml_src = (
            "  description: >\n"
            "    EXG-USR-004 — Le rôle n'est pas attribuable ici (absent du schéma de\n"
            "  operationId: creerUtilisateur"
        )
        test_src = (
            "test(\"EXG-USR-004 — un `role` envoyé à l'inscription fait échouer la requête en 400\", …\n"
            "  …  role: 'administrateur',\n"
            "  reponse.assertStatus(400)"
        )
        rows = [
            ("docs/specs/utilisateurs.md", spec_src, "markdown", "1 · la spécification", 1.6, 2, 2),
            ("contract/features/utilisateurs/paths/utilisateurs.yaml", yaml_src, "yaml",
             "2 · le contrat", 1.85, 2, 4),
            ("server/tests/functional/utilisateurs.spec.ts", test_src, "typescript",
             "3 · le test", 1.85, 1, 6),
        ]
        top = 2.72
        panels, views, marks = [], [], []
        for fname, src, lexer, tag, h, line, col in rows:
            center = np.array([0.15, top - h / 2, 0])
            panel, view = code_panel(fname, src, lexer, center, 13.3, h, tag=tag, tag_color=GOLD)
            panels.append(panel)
            views.append(view)
            marks.append(view.span_box(line, col, len("EXG-USR-004")))
            top -= h + 0.14

        for panel, view in zip(panels, views):
            self.play(FadeIn(panel.chrome), FadeIn(view.group, shift=0.05 * UP), run_time=0.6)
            self.wait(0.7)

        # Le même identifiant, surligné aux trois endroits, relié par un fil
        rects = VGroup(*[highlight_rect(b, GOLD, 0.22) for b in marks])
        self.play(flash(marks, GOLD, 0.35), run_time=1.05)
        self.play(LaggedStartMap(FadeIn, rects, lag_ratio=0.3), run_time=0.8)
        # Le fil court dans la marge gauche des panneaux ; chaque attache passe
        # SOUS la ligne de texte, pour ne rien barrer.
        thread_x = panels[0].box.get_left()[0] + 0.14
        pts = [r.get_corner(DL) + 0.03 * DOWN for r in rects]
        anchors = [np.array([thread_x, p[1], 0]) for p in pts]
        thread = Line(anchors[0], anchors[-1]).set_stroke(GOLD, 3)
        knots = VGroup(*[
            VGroup(Line(a, p).set_stroke(GOLD, 2.5), Dot(a, radius=0.06).set_fill(GOLD, 1))
            for a, p in zip(anchors, pts)
        ])
        self.play(ShowCreation(thread), FadeIn(knots), run_time=1.2)
        why = label("un identifiant stable, recopié littéralement de la spec au test",
                    18, TXT).move_to([0, -3.0, 0])
        why2 = label("la spec dit où l'exigence est tenue : ici, par le contrat (role absent + additionalProperties: false)",
                     15, DIM).next_to(why, DOWN, buff=0.14)
        fit_x(why2)
        self.play(FadeIn(why, shift=0.1 * UP), FadeIn(why2), run_time=0.7)
        self.wait(3.2)

        # Et pour tout retrouver : un grep
        self.play(*[FadeOut(m) for m in self.mobjects
                    if m not in self.permanent and m is not self.chip], run_time=0.6)
        console = EditorPanel("terminal", np.array([0, 0.2, 0]), width=12.6, height=3.6,
                              tag="à la racine du dépôt")
        out = (
            '$ grep -rl "EXG-USR-004" --exclude-dir=node_modules . | sort\n'
            "./clients/web/src/utilisateurs/formulaire-utilisateur.tsx\n"
            "./contract/features/utilisateurs/paths/utilisateurs.yaml\n"
            "./contract/features/utilisateurs/schemas/CreationUtilisateur.yaml\n"
            "./docs/specs/utilisateurs.md\n"
            "./server/app/services/utilisateurs_service.ts\n"
            "./server/tests/functional/utilisateurs.spec.ts"
        )
        view = CodeView(out, ["bash"], gutter=False)
        console.fit_code(view, max_scale=1.0)
        self.play(FadeIn(console.chrome), run_time=0.5)
        self.play(FadeIn(view.lines[0]), run_time=0.5)
        self.play(LaggedStartMap(FadeIn, view.lines[1:], shift=0.1 * RIGHT, lag_ratio=0.2), run_time=1.4)
        hits = [view.line_box(i) for i in (3, 5, 7)]
        self.play(flash(hits, GOLD, 0.3), run_time=0.9)
        hit_rects = VGroup(*[highlight_rect(b, GOLD, 0.14) for b in hits])
        self.play(FadeIn(hit_rects), run_time=0.4)
        self.wait(1.0)
        outro = label("la spec, le contrat, le service, le test, et même le formulaire web : un seul grep",
                      17, TXT).move_to([0, -2.65, 0])
        fit_x(outro)
        self.play(FadeIn(outro, shift=0.1 * UP), run_time=0.6)
        next_ep = label("épisode suivant : les cinq outils du contrat, au travail  →", 15, DIM)
        next_ep.to_corner(DR, buff=0.35)
        self.play(FadeIn(next_ep), run_time=0.5)
        self.wait(3.0)
