"""
Épisode 21 — Du hook à fetch : customInstance et le cache React Query

Qui fait quoi côté client, et le pont vers le mobile.
  1. Le hook calcule une clé ['/utilisateurs', params] ; le cache est vide, customInstance part.
  2. customInstance dans l'ordre du code : l'URL (concaténée), le chronomètre de 10 s,
     les en-têtes (JSON, Bearer si getToken), puis fetch.
  3. Ce qui revient : des données (2xx), ou une ApiError { code, message, details? } —
     erreur HTTP normalisée, NETWORK_ERROR, SDK_NOT_CONFIGURED.
  4. Le cache : staleTime 30 s, retry false ; invalidateQueries(['/utilisateurs']) après une création.

Défauts connus de custom-instance.ts (voir correctifs-sdk-et-garde-fou.md) : la branche
TIMEOUT_ERROR n'est PAS montrée comme fonctionnelle (seulement une mention discrète), le signal de
React Query n'est pas évoqué, la perte du statut HTTP est dite telle quelle.

Sources : sdk/src/custom-instance.ts, clients/web/src/main.tsx (l. 26-38),
clients/web/src/utilisateurs/utilisateurs-page.tsx, clients/web/src/utilisateurs/formulaire-utilisateur.tsx.
Le code généré par Orval n'est pas dans le dépôt : l'appel à customInstance est montré sous forme
schématique, la forme de la clé vient du commentaire de formulaire-utilisateur.tsx.

Rendu vidéo :  manimgl ep21_hook_fetch.py Ep21HookFetch -w
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


def box_text(lines, color, width=None, size=16, mono=True, fill=0.08):
    """Une boîte arrondie contenant quelques lignes (la 1re en couleur)."""
    texts = VGroup(*[
        label(t, size if k == 0 else size - 2, color if k == 0 else DIM,
              font=MONO_FONT if (mono and k == 0) else UI_FONT, bold=(k == 0))
        for k, t in enumerate(lines)
    ]).arrange(DOWN, buff=0.08)
    w = width or texts.get_width() + 0.5
    if texts.get_width() > w - 0.3:
        texts.set_width(w - 0.3)
    box = RoundedRectangle(width=w, height=texts.get_height() + 0.4, corner_radius=0.12)
    box.set_fill(color, fill).set_stroke(color, 1.6)
    texts.move_to(box)
    group = VGroup(box, texts)
    group.box = box
    return group


# ---------------------------------------------------------------------------
# Extraits (copiés du dépôt, raccourcis par « … »)
# ---------------------------------------------------------------------------

COMPOSANT = """\
const requete = useListerUtilisateurs({ page, limit: PAR_PAGE, ...(role ? { role } : {}) })"""

S_URL = """\
const base = apiBaseUrl || (typeof window !== 'undefined' ? window.location.origin : '');
…
const fullUrl = estAbsolue
  ? new URL(url)
  : new URL(`${base.replace(/\\/+$/, '')}/${url.replace(/^\\/+/, '')}`);
if (params) {
  … fullUrl.searchParams.append(key, String(value)) …
}"""

S_TIMER = """\
const { timeout = 10000, params, headers = {}, ...restConfig } = config;
…
// 2. Gestion du timeout via AbortController
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), timeout);"""

S_HEADERS = """\
const requestHeaders = new Headers(headers);
if (!requestHeaders.has('Content-Type') && restConfig.body && !(restConfig.body instanceof FormData)) {
  requestHeaders.set('Content-Type', 'application/json');
}
if (getAuthToken) {
  const token = await getAuthToken();
  if (token && !requestHeaders.has('Authorization')) {
    requestHeaders.set('Authorization', `Bearer ${token}`);
  }
}"""

QUERY_CLIENT = """\
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 30_000,
    },
  },
})"""

INVALIDATE = """\
onSuccess: () => {
  void queryClient.invalidateQueries({ queryKey: ['/utilisateurs'] })
  …
},"""


# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------

class Ep21HookFetch(EpisodeScene):
    EPISODE = "21"
    TITLE = "Du hook à fetch"

    def construct(self):
        self.cle()
        self.custom_instance()
        self.retours()
        self.cache()

    # --- 1. La clé de cache ------------------------------------------------------------------

    def cle(self):
        self.show_chip("Le hook calcule une clé", BLUE)
        _, _, comp = code_panel("clients/web/src/utilisateurs/utilisateurs-page.tsx", COMPOSANT, "tsx",
                                0, 2.5, 13.4, max_scale=0.85, gutter=False)
        self.play(FadeIn(comp), run_time=0.6)

        y = -0.2
        key = box_text(["['/utilisateurs', { page: 1, limit: 5 }]", "la clé du cache"], BLUE, size=18)
        key.move_to([-3.9, y, 0])
        cache = box_text(["cache React Query", "vide"], GOLD, mono=False, size=18)
        cache.move_to([0.85, y, 0])
        ci = box_text(["customInstance()", "le seul client HTTP du SDK"], ACCENT, size=18)
        ci.move_to([5.05, y, 0])
        a1 = Arrow(comp.get_bottom() + np.array([-3.9, -0.05, 0]), key.get_top(), buff=0.1,
                   thickness=2.5).set_color(BLUE)
        a1.set_x(-3.9)
        self.play(GrowArrow(a1), FadeIn(key, shift=0.1 * DOWN), run_time=0.8)
        orval = caption("clé générée par Orval : le chemin, puis les paramètres", [-3.9, y - 0.85, 0],
                        DIM, 14)
        self.play(FadeIn(orval), run_time=0.5)
        self.wait(1.8)

        a2 = link(edge_point(key, RIGHT), edge_point(cache, LEFT), DIM)
        self.play(GrowArrow(a2), FadeIn(cache), run_time=0.7)
        miss = label("absente", 16, WARN, bold=True).next_to(cache, DOWN, buff=0.2)
        self.play(FadeIn(miss), Indicate(cache, color=WARN, scale_factor=1.04), run_time=0.7)
        a3 = link(edge_point(cache, RIGHT), edge_point(ci, LEFT), ACCENT)
        self.play(GrowArrow(a3), FadeIn(ci), run_time=0.7)
        call = label("customInstance('/utilisateurs', { params: { page: 1, limit: 5 }, … })",
                     17, TXT, font=MONO_FONT).move_to([0, -2.3, 0])
        fit_x(call)
        schem = caption("appel fait par le code généré (non versionné) : forme schématique",
                        [0, -2.75, 0], DIM, 14)
        self.play(FadeIn(call), FadeIn(schem), run_time=0.6)
        self.wait(3.2)
        self.clear_stage()

    # --- 2. customInstance, étape par étape --------------------------------------------------

    def custom_instance(self):
        self.show_chip("customInstance, dans l'ordre du code", ACCENT)

        labels = [("1", "l'URL", ACCENT), ("2", "le chronomètre", GOLD),
                  ("3", "les en-têtes", VIOLET), ("4", "fetch", BLUE)]
        cards = VGroup()
        for num, txt, color in labels:
            disc = Circle(radius=0.2).set_fill(color, 1).set_stroke(width=0)
            n = label(num, 16, BG, bold=True).move_to(disc)
            cards.add(VGroup(VGroup(disc, n), label(txt, 18, color, bold=True)).arrange(RIGHT, buff=0.15))
        cards.arrange(RIGHT, buff=0.9).move_to([0, 2.3, 0])
        arrows = VGroup(*[
            Arrow(cards[i].get_right(), cards[i + 1].get_left(), buff=0.15, thickness=2).set_color(DIM)
            for i in range(3)
        ])
        self.play(LaggedStartMap(FadeIn, cards, lag_ratio=0.2), FadeIn(arrows), run_time=1.0)
        for c in cards:
            c.set_opacity(0.35)

        def show(i, src, notes):
            cards[i].set_opacity(1)
            _, v, panel = code_panel("sdk/src/custom-instance.ts", src, "typescript",
                                     0, 1.75, 13.4, max_scale=0.8, gutter=False)
            ns = VGroup(*notes).arrange(DOWN, buff=0.14).move_to([0, panel.get_bottom()[1] - 0.75, 0])
            self.play(Indicate(cards[i], scale_factor=1.08, color=labels[i][2]), FadeIn(panel),
                      run_time=0.7)
            return v, panel, ns

        # 1. URL
        v, panel, ns = show(0, S_URL, [
            label("http://localhost:3333/api/v1/utilisateurs?page=1&limit=5", 18, ACCENT, font=MONO_FONT),
            label("on CONCATÈNE : new URL('/utilisateurs', base) effacerait /api/v1 (épisode 22)", 15, DIM),
        ])
        hl = highlight_rect(v.line_box(5), ACCENT, 0.12)
        self.play(FadeIn(hl), FadeIn(ns), run_time=0.6)
        self.wait(3.4)
        self.play(FadeOut(panel), FadeOut(ns), FadeOut(hl), run_time=0.5)

        # 2. Chronomètre
        v, panel, ns = show(1, S_TIMER, [
            label("au bout de 10 s, controller.abort() coupe la requête", 17, TXT),
            label("ce que devient alors l'erreur : voir correctifs-sdk-et-garde-fou.md", 14, DIM),
        ])
        hl = highlight_rect(v.line_box(5), GOLD, 0.12)
        self.play(FadeIn(hl), FadeIn(ns), run_time=0.6)
        self.wait(3.2)
        self.play(FadeOut(panel), FadeOut(ns), FadeOut(hl), run_time=0.5)

        # 3. En-têtes
        v, panel, ns = show(2, S_HEADERS, [
            label("JSON si un corps est envoyé ; Bearer seulement si l'appli a fourni getToken", 17, TXT),
            label("le back-office n'appelle configureSdk qu'avec baseUrl : pas de jeton aujourd'hui",
                  14, DIM),
        ])
        hl = VGroup(highlight_rect(v.line_box(3), VIOLET, 0.12), highlight_rect(v.line_box(8), VIOLET, 0.12))
        self.play(FadeIn(hl), FadeIn(ns), run_time=0.6)
        self.wait(3.6)
        self.play(FadeOut(panel), FadeOut(ns), FadeOut(hl), run_time=0.5)

        # 4. fetch
        cards[3].set_opacity(1)
        go = label("fetch(fullUrl, { …, headers })", 22, BLUE, font=MONO_FONT).move_to([0, 0.4, 0])
        self.play(Indicate(cards[3], scale_factor=1.08, color=BLUE), FadeIn(go, shift=0.1 * DOWN),
                  run_time=0.7)
        nxt = caption("et voici ce qui peut en revenir", [0, -0.3, 0], DIM, 16)
        self.play(FadeIn(nxt), run_time=0.4)
        self.wait(1.4)
        self.clear_stage()

    # --- 3. Toujours une ApiError ----------------------------------------------------------------

    def retours(self):
        self.show_chip("Ce qui revient : des données, ou une ApiError", VIOLET)

        root = box_text(["customInstance()"], ACCENT).move_to([-5.3, 0.3, 0])
        branches = [
            ("2xx", "response.json()  (204 → {})", ACCENT, 2.1),
            ("non-ok", "{ code, message, details } du corps", WARN, 0.92),
            ("fetch rejeté", "réseau coupé, serveur absent", ERROR, -0.26),
            ("pas de baseUrl", "ni window (React Native)", DIM, -1.44),
        ]
        leaves = [
            ("ListeUtilisateurs", "dans requete.data", ACCENT),
            ("VALIDATION_ERROR, EMAIL_ALREADY_USED…", "le code du serveur, sinon HTTP_<statut>", WARN),
            ("NETWORK_ERROR", "message : celui de l'erreur fetch", ERROR),
            ("SDK_NOT_CONFIGURED", "levée avant tout fetch", DIM),
        ]
        self.play(FadeIn(root), run_time=0.5)
        rows = VGroup()
        for (cond, how, color, y), (leaf, sub, lcolor) in zip(branches, leaves):
            c = box_text([cond, how], color, width=4.0, size=18).move_to([-1.6, y, 0])
            l = box_text([leaf, sub], lcolor, width=4.4, size=18).move_to([3.45, y, 0])
            a = link(edge_point(root, RIGHT), edge_point(c, LEFT), color, width=1.8)
            b = link(edge_point(c, RIGHT), edge_point(l, LEFT), color, width=1.8)
            rows.add(VGroup(a, c, b, l))
        for r in rows:
            self.play(GrowArrow(r[0]), FadeIn(r[1]), run_time=0.5)
            self.play(GrowArrow(r[2]), FadeIn(r[3], shift=0.1 * RIGHT), run_time=0.5)
            self.wait(1.4)

        # Pas de Brace (il passe par LaTeX, absent) : un crochet dessiné à la main
        target = VGroup(*[rows[i][3] for i in (1, 2, 3)])
        x, top, bot = target.get_right()[0] + 0.12, target.get_top()[1], target.get_bottom()[1]
        err_brace = VMobject().set_points_as_corners([
            np.array([x, top, 0]), np.array([x + 0.15, top, 0]), np.array([x + 0.15, bot, 0]),
            np.array([x, bot, 0]),
        ]).set_stroke(VIOLET, 2.5)
        api = label("ApiError", 18, VIOLET, font=MONO_FONT, bold=True).next_to(err_brace, RIGHT, buff=0.1)
        api_box = VGroup(err_brace, api)
        if api_box.get_right()[0] > 6.95:
            api_box.shift((api_box.get_right()[0] - 6.95) * LEFT)
        self.play(ShowCreation(err_brace), FadeIn(api), run_time=0.6)
        notes = VGroup(
            label("Une seule forme côté front : { code, message, details? } dans requete.error.", 17, TXT),
            label("Le statut HTTP, lui, n'est pas conservé : le front teste le code, jamais le statut.",
                  15, DIM),
        ).arrange(DOWN, buff=0.12).move_to([0, -2.8, 0])
        self.play(FadeIn(notes), run_time=0.6)
        self.wait(4.0)
        self.clear_stage()

    # --- 4. Le cache ---------------------------------------------------------------------------

    def cache(self):
        self.show_chip("Le cache : 30 s de fraîcheur, puis on invalide", GOLD)
        _, _, qc = code_panel("clients/web/src/main.tsx", QUERY_CLIENT, "tsx", -4.1, 2.5, 5.3,
                              max_scale=0.75, gutter=False)
        self.play(FadeIn(qc), run_time=0.6)

        keys = [
            "['/utilisateurs', { page: 1, limit: 5 }]",
            "['/utilisateurs', { page: 2, limit: 5 }]",
            "['/utilisateurs', { page: 1, limit: 5, role: 'benevole' }]",
        ]
        cache_box = RoundedRectangle(width=7.4, height=2.5, corner_radius=0.15)
        cache_box.set_fill(GOLD, 0.05).set_stroke(GOLD, 1.5).move_to([3.25, 1.25, 0])
        cache_title = label("cache React Query", 16, GOLD, bold=True)
        cache_title.move_to(cache_box.get_top() + 0.3 * DOWN)
        entries = VGroup()
        for k, text in enumerate(keys):
            t = label(text, 14, TXT, font=MONO_FONT)
            dot = Dot(radius=0.07).set_fill(ACCENT, 1)
            state = label("fraîche", 13, ACCENT)
            row = VGroup(dot, t, state).arrange(RIGHT, buff=0.18)
            entries.add(row)
        entries.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        if entries.get_width() > 6.8:
            entries.set_width(6.8)
        entries.move_to(cache_box).shift(0.2 * DOWN)
        entries.align_to(cache_box, LEFT).shift(0.25 * RIGHT)
        self.play(FadeIn(cache_box), FadeIn(cache_title), run_time=0.5)
        self.play(LaggedStartMap(FadeIn, entries, lag_ratio=0.3), run_time=1.0)

        # Revenir sur la page 1 en moins de 30 s : servi par le cache
        hit = VGroup(
            label("on revient sur la page 1 en moins de 30 s :", 17, TXT),
            label("servie depuis le cache, aucun appel réseau", 17, ACCENT, bold=True),
        ).arrange(DOWN, buff=0.1).move_to([3.15, -0.5, 0])
        self.play(Indicate(entries[0], color=ACCENT, scale_factor=1.05), FadeIn(hit), run_time=0.8)
        retry = caption("retry: false → une erreur s'affiche tout de suite, sans 3 essais muets",
                        [-4.1, qc.get_bottom()[1] - 0.35, 0], DIM, 14)
        self.play(FadeIn(retry), run_time=0.5)
        self.wait(3.0)

        # Après une création : on invalide tout le préfixe
        self.play(FadeOut(hit), run_time=0.4)
        _, iv, inv = code_panel("clients/web/src/utilisateurs/formulaire-utilisateur.tsx", INVALIDATE, "tsx",
                                0, -1.0, 13.0, max_scale=0.75, gutter=False)
        self.play(FadeIn(inv, shift=0.1 * UP), run_time=0.6)
        hl = highlight_rect(iv.line_box(2), GOLD, 0.14)
        self.play(FadeIn(hl), run_time=0.4)
        stale = []
        for row in entries:
            new_state = label("périmée → rechargée", 13, WARN).move_to(row[2], aligned_edge=LEFT)
            stale.append(AnimationGroup(row[0].animate.set_fill(WARN, 1), Transform(row[2], new_state)))
        self.play(LaggedStart(*stale, lag_ratio=0.25), run_time=1.2)
        why = caption("le préfixe ['/utilisateurs'] touche toutes les pages et tous les filtres d'un coup",
                      [0, inv.get_bottom()[1] - 0.35, 0], TXT, 16)
        self.play(FadeIn(why), run_time=0.5)
        self.wait(2.4)
        bridge = caption("le même SDK, la même customInstance : demain, l'app mobile et sa file hors ligne",
                         why.get_center(), GOLD, 16)
        self.play(FadeOut(why), FadeIn(bridge), run_time=0.6)
        next_ep = label("épisode suivant : pourquoi le hors-ligne change le contrat  →", 15, DIM).to_corner(DR, buff=0.25)
        self.play(FadeIn(next_ep), run_time=0.4)
        self.wait(3.5)
