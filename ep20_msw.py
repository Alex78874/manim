"""
Épisode 20 — Développer sans serveur : MSW et l'ordre de démarrage

Le front est productif dès le merge du contrat.
  1. Sans serveur : un Service Worker (MSW) intercepte les requêtes et répond avec les mocks
     générés depuis le contrat (données faker aléatoires).
  2. main.tsx, un ordre non négociable : configureSdk, puis await worker.start(), puis createRoot.
     Variante : le mauvais ordre (la 1re requête part avant que le worker soit prêt).
  3. VITE_USE_MOCKS=false : la même requête atteint Adonis et reçoit un vrai 200, sans jeton
     (lister et créer sont publiques). Le composant ne change pas d'un caractère.
  Encart : import.meta.env.DEV élimine msw et faker du build de production.

Sources : clients/web/src/main.tsx, clients/web/.env.example, sdk/src/msw.ts,
clients/web/src/mocks/erreurs.ts (joker d'origine), clients/web/src/utilisateurs/utilisateurs-page.tsx,
server/start/routes/utilisateurs.ts, server/config/cors.ts (origine ouverte en dev).

Illustration : les lignes du tableau en mode mocks (valeurs faker inventées pour l'image).

Rendu vidéo :  manimgl ep20_msw.py Ep20Msw -w
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
        print(f"[code_panel] {filename} : code petit (échelle {scale:.2f})", file=sys.stderr)
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


def shield(height=1.7, color=GOLD):
    w = height * 0.72
    pts = [
        [-w / 2, height / 2, 0], [w / 2, height / 2, 0], [w / 2, 0.05 * height, 0],
        [0, -height / 2, 0], [-w / 2, 0.05 * height, 0],
    ]
    body = Polygon(*[np.array(p) for p in pts]).set_fill(color, 0.15).set_stroke(color, 2.5)
    txt = label("MSW", 18, color, font=MONO_FONT, bold=True).move_to(body).shift(0.12 * UP)
    return VGroup(body, txt)


def table_rows(rows, width, size=14):
    """Lignes de tableau façon back-office : nom, email, rôle."""
    out = VGroup()
    for nom, email, role in rows:
        r = VGroup(
            label(nom, size, TXT, font=MONO_FONT),
            label(email, size, DIM, font=MONO_FONT),
            label(role, size, ACCENT, font=MONO_FONT),
        )
        r[0].move_to([0, 0, 0], aligned_edge=LEFT)
        r[1].move_to([width * 0.32, 0, 0], aligned_edge=LEFT)
        r[2].move_to([width * 0.76, 0, 0], aligned_edge=LEFT)
        out.add(r)
    out.arrange(DOWN, buff=0.16, aligned_edge=LEFT)
    return out


# Données faker : ILLUSTRATION. Orval génère des valeurs aléatoires selon le type du
# contrat : une chaîne sans format (nom) donne des lettres au hasard, un format email
# un email plausible, une énumération une de ses valeurs.
FAKER_ROWS = [
    ("kQwhTzLpaRmx", "Destin_Kub@hotmail.com", "benevole"),
    ("BnVtrEoqWslZ", "Maribel.Lind@yahoo.com", "commercant"),
    ("pXcYdmUeHgaT", "Alek.Wiza@gmail.com", "administrateur"),
    ("ZrfLqoNkxCbe", "Joy_Kuhn38@gmail.com", "benevole"),
]
FAKER_ROWS_2 = [
    ("TgmWyaRbcLqe", "Lonnie.Hahn@yahoo.com", "administrateur"),
    ("vEpQzsKoiNtw", "Ima_Bode12@hotmail.com", "benevole"),
    ("HuoXkaDmrWzy", "Rory.Pagac@gmail.com", "benevole"),
    ("cJnBsLtqVeYo", "Ewald_Ryan@yahoo.com", "commercant"),
]


# ---------------------------------------------------------------------------
# Extraits (copiés du dépôt, raccourcis par « … »)
# ---------------------------------------------------------------------------

MAIN_TSX = """\
configureSdk({ baseUrl: import.meta.env.VITE_API_URL })
…
async function demarrerLesMocks(): Promise<void> {
  if (!import.meta.env.DEV) return
  if (import.meta.env.VITE_USE_MOCKS !== 'true') return
  const { setupWorker } = await import('msw/browser')
  const { handlers } = await import('@cmc/sdk/msw')
  …
  const worker = setupWorker(...aJouter, ...handlers)
  await worker.start({ onUnhandledFrame: 'warn' })
}

demarrerLesMocks().then(() => {
  createRoot(document.getElementById('root')!).render(…)
})"""

ENV_TRUE = """\
VITE_API_URL=http://localhost:3333/api/v1
VITE_USE_MOCKS=true
VITE_MOCK_ERRORS=false"""

ENV_FALSE = """\
VITE_API_URL=http://localhost:3333/api/v1
VITE_USE_MOCKS=false
VITE_MOCK_ERRORS=false"""

ROUTES = """\
router
  .get('/utilisateurs', [controllers.Utilisateurs, 'lister'])
  .use(middleware.contract({ operationId: 'listerUtilisateurs' }))"""

COMPOSANT = """\
const requete = useListerUtilisateurs({ page, limit: PAR_PAGE, ...(role ? { role } : {}) })"""

BUILD = """\
if (!import.meta.env.DEV) return
if (import.meta.env.VITE_USE_MOCKS !== 'true') return"""


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep20Msw(EpisodeScene):
    EPISODE = "20"
    TITLE = "Développer sans serveur : MSW"

    def construct(self):
        self.sans_serveur()
        self.ordre()
        self.vrai_serveur()
        self.encart_build()

    # --- le décor partagé : navigateur, bouclier, serveur ----------------------------------

    def decor(self):
        nav = browser(5.0, 3.4).move_to([-3.7, -0.3, 0])
        url = label("localhost:5173", 14, DIM, font=MONO_FONT)
        url.next_to(nav[2], RIGHT, buff=0.3)
        head = VGroup(label("Nom", 14, DIM, bold=True), label("Email", 14, DIM, bold=True),
                      label("Rôle", 14, DIM, bold=True))
        x0 = nav[0].get_left()[0] + 0.3
        for h, f in zip(head, (0, 0.32, 0.76)):
            h.move_to([x0 + 4.4 * f, 0.85, 0], aligned_edge=LEFT)
        server = node("server/", "AdonisJS · :3333", VIOLET, width=2.5, height=1.4)
        server.move_to([5.25, -0.3, 0])
        return nav, url, head, server, x0

    # --- 1. Sans serveur -----------------------------------------------------------------------

    def sans_serveur(self):
        self.show_chip("Le front tourne sans serveur", GOLD)
        nav, url, head, server, x0 = self.decor()
        off = label("éteint", 16, ERROR, bold=True).next_to(server, DOWN, buff=0.2)
        self.play(FadeIn(nav), FadeIn(url), FadeIn(head), run_time=0.7)
        self.play(FadeIn(server), run_time=0.5)
        self.play(server.animate.set_opacity(0.3), FadeIn(off), run_time=0.6)

        sh = shield().move_to([1.5, -0.3, 0])
        sw = label("Service Worker", 15, GOLD).next_to(sh, DOWN, buff=0.15)
        self.play(DrawBorderThenFill(sh[0]), FadeIn(sh[1]), FadeIn(sw), run_time=0.9)

        # Une requête part, le bouclier répond
        start = nav[0].get_right() + 0.1 * RIGHT
        req = label("GET */utilisateurs", 14, BLUE, font=MONO_FONT).move_to([-0.12, 0.2, 0])
        pk = packet(BLUE, 0.09).move_to(start)
        self.add(pk)
        self.play(pk.animate.move_to(sh.get_left()), FadeIn(req), run_time=0.8, rate_func=linear)
        self.play(Flash(sh.get_left(), color=GOLD, line_length=0.15, flash_radius=0.3), run_time=0.4)
        back = packet(GOLD, 0.09).move_to(sh.get_left())
        self.remove(pk)
        self.add(back)
        self.play(back.animate.move_to(start), run_time=0.7, rate_func=linear)
        self.remove(back)

        rows = table_rows(FAKER_ROWS, 4.4)
        rows.move_to([x0, 0.6, 0], aligned_edge=UL)
        rows.set_x(x0 + rows.get_width() / 2)
        self.play(LaggedStartMap(FadeIn, rows, shift=0.1 * DOWN, lag_ratio=0.25), run_time=1.2)
        fake = label("données faker, aléatoires : générées depuis les types du contrat", 15, DIM)
        fake.next_to(nav, DOWN, buff=0.25)
        fit_x(fake)
        self.play(FadeIn(fake), run_time=0.5)
        self.wait(1.2)
        # On recharge : d'autres valeurs, toujours à la forme du contrat
        rows2 = table_rows(FAKER_ROWS_2, 4.4)
        rows2.move_to(rows, aligned_edge=UL)
        reload = label("↻ on recharge la page", 14, GOLD).next_to(url, RIGHT, buff=0.4)
        self.play(FadeIn(reload), FadeOut(rows, shift=0.1 * DOWN), run_time=0.5)
        self.play(LaggedStartMap(FadeIn, rows2, shift=0.1 * DOWN, lag_ratio=0.25), run_time=1.0)
        note = VGroup(
            label("Les mocks sortent du même contrat que le serveur :", 18, TXT),
            label("le front est productif dès le merge du YAML.", 18, GOLD, bold=True),
        ).arrange(DOWN, buff=0.1).move_to([0, 2.15, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.wait(3.2)
        self.clear_stage()

    # --- 2. L'ordre de démarrage ------------------------------------------------------------------

    def ordre(self):
        self.show_chip("main.tsx : un ordre non négociable", BLUE)
        _, cv, code = code_panel("clients/web/src/main.tsx", MAIN_TSX, "tsx",
                                 -2.55, 2.55, 8.6, max_scale=0.72, gutter=False)
        self.play(FadeIn(code), run_time=0.7)

        steps = [
            ("1", "configurer le SDK", "il ne lit pas l'environnement", [1], ACCENT),
            ("2", "démarrer MSW, et ATTENDRE", "await worker.start()", [10], GOLD),
            ("3", "seulement ensuite, monter React", "createRoot dans le .then", [13, 14], BLUE),
        ]
        cards = VGroup()
        hls = VGroup()
        for k, (num, title, sub, lines, color) in enumerate(steps):
            disc = Circle(radius=0.22).set_fill(color, 1).set_stroke(width=0)
            n = label(num, 18, BG, bold=True).move_to(disc)
            txt = VGroup(label(title, 17, color, bold=True), label(sub, 14, DIM)).arrange(
                DOWN, aligned_edge=LEFT, buff=0.06)
            card = VGroup(VGroup(disc, n), txt).arrange(RIGHT, buff=0.2)
            card.move_to([4.6, 1.7 - k * 1.05, 0], aligned_edge=LEFT).set_x(2.25 + card.get_width() / 2)
            new = VGroup(*[highlight_rect(cv.line_box(i), color, 0.16) for i in lines])
            self.play(FadeIn(card, shift=0.1 * LEFT), FadeOut(hls), FadeIn(new), run_time=0.6)
            self.wait(2.3)
            cards.add(card)
            hls = new
        self.play(FadeOut(hls), run_time=0.3)

        # Variante : le mauvais ordre
        bad = VGroup(
            label("Dans le mauvais ordre :", 17, ERROR, bold=True),
            label("React monte, la 1re requête part", 15, TXT),
            label("avant que le worker soit prêt,", 15, TXT),
            label("vers :3333 où rien n'écoute.", 15, TXT),
            label("Elle échoue, et on cherche longtemps.", 15, DIM),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        bad.move_to([4.6, -2.2, 0])
        fit_x(bad)
        box = SurroundingRectangle(bad, buff=0.2).set_stroke(ERROR, 1.5).set_fill(ERROR, 0.06)
        self.play(FadeIn(box), FadeIn(bad), run_time=0.7)
        self.wait(4.2)
        self.clear_stage()

    # --- 3. Le vrai serveur -----------------------------------------------------------------------

    def vrai_serveur(self):
        self.show_chip("Brancher le vrai serveur : une variable", VIOLET)
        _, ev, env = code_panel("clients/web/.env", ENV_TRUE, "bash", -3.55, 2.5, 6.6,
                                max_scale=0.75, gutter=False)
        _, ev2, env2 = code_panel("clients/web/.env", ENV_FALSE, "bash", -3.55, 2.5, 6.6,
                                  max_scale=0.75, gutter=False)
        self.play(FadeIn(env), run_time=0.6)
        hl = highlight_rect(ev.line_box(2), GOLD)
        self.play(FadeIn(hl), run_time=0.4)
        self.wait(1.0)
        self.play(FadeOut(hl), FadeTransform(env, env2), run_time=0.8)
        hl2 = highlight_rect(ev2.line_box(2), VIOLET)
        restart = caption("puis on relance npm run dev", [-3.55, env2.get_bottom()[1] - 0.3, 0], DIM, 14)
        self.play(FadeIn(hl2), FadeIn(restart), run_time=0.4)

        # La requête atteint Adonis
        nav = browser(3.0, 1.9).move_to([-3.55, -1.95, 0])
        nav_lbl = label("back-office", 15, BLUE).move_to(nav[0]).shift(0.15 * DOWN)
        server = node("server/", "AdonisJS · :3333", VIOLET, width=2.6, height=1.3)
        server.move_to([4.4, -1.95, 0])
        self.play(FadeIn(nav), FadeIn(nav_lbl), FadeIn(server), run_time=0.6)
        a = nav[0].get_right() + 0.1 * RIGHT
        b = server.get_left() + 0.1 * LEFT
        path = Line(a, b).set_stroke(BLUE, 2, opacity=0.5)
        req = label("GET /api/v1/utilisateurs", 15, BLUE, font=MONO_FONT).next_to(path, UP, buff=0.12)
        pk = packet(BLUE, 0.09).move_to(a)
        self.add(path, pk)
        self.play(pk.animate.move_to(b), FadeIn(req), run_time=1.0, rate_func=linear)
        self.remove(pk)
        self.play(Indicate(server, color=VIOLET, scale_factor=1.05), run_time=0.5)
        back = packet(ACCENT, 0.09).move_to(b)
        self.add(back)
        ok = badge("200", ACCENT, 17).next_to(path, DOWN, buff=0.15)
        self.play(back.animate.move_to(a), FadeIn(ok), run_time=1.0, rate_func=linear)
        self.remove(back)

        public = VGroup(
            label("un VRAI 200, sans jeton :", 17, TXT, bold=True),
            label("lister et créer sont des routes publiques", 15, DIM),
            label("(pas de middleware.auth() sur elles)", 15, DIM),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).move_to([3.6, 1.55, 0])
        _, _, routes = code_panel("server/start/routes/utilisateurs.ts", ROUTES, "typescript",
                                  3.6, 0.85, 6.6, max_scale=0.62, gutter=False)
        self.play(FadeIn(public), run_time=0.6)
        self.play(FadeIn(routes), run_time=0.6)
        self.wait(2.4)
        empty = caption("base vide au départ : la liste l'est aussi, jusqu'à la première inscription",
                        [0, -3.45, 0], DIM, 15)
        self.play(FadeIn(empty), run_time=0.5)
        self.wait(2.2)

        # Le composant n'a pas changé d'un caractère
        self.play(*[FadeOut(m) for m in (env2, hl2, restart, public, routes)], run_time=0.5)
        _, _, comp = code_panel("clients/web/src/utilisateurs/utilisateurs-page.tsx", COMPOSANT, "tsx",
                                0, 2.45, 13.4, max_scale=0.8, gutter=False)
        same = label("identique avec les mocks et avec le serveur : aucun caractère ne change",
                     18, ACCENT, bold=True).move_to([0, comp.get_bottom()[1] - 0.4, 0])
        fit_x(same)
        self.play(FadeIn(comp), run_time=0.6)
        self.play(FadeIn(same), run_time=0.5)
        self.wait(3.4)
        self.clear_stage()

    # --- Encart : rien de tout ça en production ------------------------------------------------------

    def encart_build(self):
        self.show_chip("Encart : msw et faker absents du build", GOLD)
        _, bv, code = code_panel("clients/web/src/main.tsx", BUILD, "tsx", 0, 2.4, 9.0,
                                 max_scale=0.85, gutter=False)
        self.play(FadeIn(code), run_time=0.6)
        hl = highlight_rect(bv.line_box(1), GOLD)
        self.play(FadeIn(hl), run_time=0.4)

        left = VGroup(
            label("import.meta.env.DEV", 18, GOLD, font=MONO_FONT, bold=True),
            label("constante remplacée au BUILD", 16, TXT),
            label("en production : false", 16, TXT),
            label("→ branche morte, chunks jamais générés", 16, ACCENT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).move_to([-3.4, -1.3, 0])
        right = VGroup(
            label("VITE_USE_MOCKS seul", 18, DIM, font=MONO_FONT, bold=True),
            label("lu à l'exécution", 16, TXT),
            label("le bundler ne peut rien prouver", 16, TXT),
            label("→ 1,1 Mo de msw et faker embarqués", 16, ERROR),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).move_to([3.4, -1.3, 0])
        self.play(FadeIn(left, shift=0.1 * UP), run_time=0.7)
        self.wait(2.0)
        self.play(FadeIn(right, shift=0.1 * UP), run_time=0.7)
        self.wait(1.5)
        rule = label("pour qu'un bundler élimine du code, la condition doit être connue au BUILD",
                     18, GOLD).move_to([0, -3.25, 0])
        fit_x(rule)
        self.play(FadeIn(rule), run_time=0.6)
        next_ep = label("épisode suivant : du hook à fetch  →", 16, DIM).to_corner(DR, buff=0.4)
        self.play(FadeIn(next_ep), run_time=0.4)
        self.wait(3.5)
