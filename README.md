# cmc-archi — animations

Les vidéos explicatives de l'architecture **cmc-archi**, écrites avec [ManimGL](https://github.com/3b1b/manim). Un script par épisode, rendu en 1920×1080, 30 i/s.

Les vidéos ne sont pas dans le dépôt : on les rend avec les commandes ci-dessous.

## Prérequis

| Outil | Version | Pourquoi |
|---|---|---|
| Python | 3.10 ou plus | ManimGL |
| FFmpeg | toute version récente | écrire les `.mp4` |
| Police **DejaVu Sans Mono** | — | tous les blocs de code |
| Pilote graphique OpenGL 3.3 | — | ManimGL dessine avec le GPU |

**LaTeX n'est pas nécessaire** : aucun script n'utilise `Tex`.

Sous Windows, avec `winget` :

```powershell
winget install -e --id Python.Python.3.10
winget install -e --id Gyan.FFmpeg
```

DejaVu n'a pas de paquet `winget` : télécharge l'archive `dejavu-fonts-ttf-*.zip` sur [dejavu-fonts.github.io](https://dejavu-fonts.github.io/Download.html), ouvre le dossier `ttf`, sélectionne les fichiers `DejaVuSansMono*.ttf`, puis clic droit → **Installer pour tous les utilisateurs**.

Sous macOS : `brew install python@3.10 ffmpeg font-dejavu`.
Sous Debian/Ubuntu : `sudo apt install python3 python3-venv ffmpeg fonts-dejavu libgl1`.

Ouvre un **nouveau** terminal après l'installation, puis vérifie :

```powershell
python --version
ffmpeg -version
```

## Installation

```powershell
git clone https://github.com/<ton-compte>/cmc-archi-animations.git
cd cmc-archi-animations

python -m venv env
.\env\Scripts\Activate.ps1        # macOS / Linux : source env/bin/activate
pip install -r requirements.txt
```

Si PowerShell refuse d'activer l'environnement (« l'exécution de scripts est désactivée »), lance une fois :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

> ManimGL est installé depuis la branche `master` de GitHub, pas depuis PyPI : la version 1.7.2 publiée sur PyPI a un `Text` / `MarkupText` cassé. L'installation peut donc prendre une ou deux minutes.

## Rendre une vidéo

```powershell
manimgl ep05_contract_first.py Ep05ContractFirst -w
```

La vidéo est écrite dans `videos\Ep05ContractFirst.mp4`.

| Option | Effet |
|---|---|
| *(aucune)* | ouvre une fenêtre et joue l'animation en direct, sans fichier |
| `-w` | écrit le `.mp4` en 1080p |
| `-w -l` | rendu rapide en 480p, pour vérifier une mise en page |
| `-w -o` | écrit le fichier puis l'ouvre |
| `-s` | n'enregistre que la dernière image (`.png`) |
| `-n 12` | commence à la 12ᵉ animation (pratique pour retravailler une fin) |

Rendre tous les épisodes d'un coup (PowerShell) :

```powershell
Get-ChildItem ep*.py | ForEach-Object {
    $cls = (Select-String $_ -Pattern '^class (Ep\w+)\(EpisodeScene\)').Matches[0].Groups[1].Value
    manimgl $_.Name $cls -w
}
```

Compte environ 1 à 2 minutes par épisode.

## Les épisodes

Le noyau de 20 minutes (les numéros manquants sont hors du noyau et n'ont pas de script) :

| Épisode | Script | Classe | Sujet |
|---|---|---|---|
| 01 | `ep01_le_projet.py` | `Ep01LeProjet` | Le projet |
| 02 | `ep02_carte_architecture.py` | `Ep02CarteArchitecture` | La carte de l'architecture |
| 04 | `ep04_setup.py` | `Ep04Setup` | Les cinq commandes, puis `npm run setup` |
| 05 | `ep05_contract_first.py` | `Ep05ContractFirst` | Un YAML, quatre consommateurs |
| 05b | `ep05b_outils_du_contrat.py` | `Ep05bOutilsDuContrat` | Les cinq outils du contrat (Redocly, Spectral, Orval, openapi-typescript, Ajv) |
| 07 | `ep07_sync.py` | `Ep07Sync` | `npm run sync` : la chaîne de génération |
| 09 | `ep09_garde_fou.py` | `Ep09GardeFou` | Le garde-fou de démarrage |
| 10 | `ep10_middlewares.py` | `Ep10Middlewares` | Le voyage d'une requête |
| 11 | `ep11_controleur_service.py` | `Ep11ControleurService` | Contrôleur mince, service épais |
| 12 | `ep12_contrat_deux_sens.py` | `Ep12ContratDeuxSens` | Le contrat dans les deux sens |
| 16 | `ep16_tests_japa.py` | `Ep16TestsJapa` | Les tests Japa |
| 20 | `ep20_msw.py` | `Ep20Msw` | Développer sans serveur : MSW |
| 21 | `ep21_hook_fetch.py` | `Ep21HookFetch` | Du hook à `fetch` |
| 25 | `ep25_hors_ligne_contrat.py` | `Ep25HorsLigneContrat` | Pourquoi le hors-ligne change le contrat |
| 26 | `ep26_intention_vs_etat.py` | `Ep26IntentionVsEtat` | Intention relative contre état calculé |
| 27 | `ep27_uuidv7.py` | `Ep27Uuidv7` | UUIDv7 fourni par le client |
| 28 | `ep28_occurred_at.py` | `Ep28OccurredAt` | `occurredAt` contre `createdAt` |
| 29 | `ep29_suppression_douce.py` | `Ep29SuppressionDouce` | Rien n'est supprimé |
| 30 | `ep30_verifier.py` | `Ep30Verifier` | `npm run verifier` : la barrière |
| 32 | `ep32_feature.py` | `Ep32Feature` | `npm run feature` : la tranche verticale |

Hors série : `prettier_vs_eslint.py` → classe `PrettierVsESLint`.

## Organisation du dépôt

```
cmc_style.py                     briques communes : couleurs, EpisodeScene, CodeView, EditorPanel…
ep*.py                           un script par épisode
prettier_vs_eslint.py            vidéo hors série (autonome, n'utilise pas cmc_style)
plan-animations-cmc-archi.md     le plan détaillé de chaque épisode et ses sources dans cmc-archi
correctifs-sdk-et-garde-fou.md   note pour les juniors sur le SDK et le garde-fou
requirements.txt
```

Pour écrire un nouvel épisode, crée `epNN_sujet.py`, importe `cmc_style` et hérite d'`EpisodeScene` en définissant `EPISODE` et `TITLE` : le titre, le style et les transitions sont fournis.

## Problèmes fréquents

- **`manimgl` introuvable** : l'environnement virtuel n'est pas activé (`.\env\Scripts\Activate.ps1`).
- **`FileNotFoundError` / ffmpeg** au moment d'écrire la vidéo : FFmpeg n'est pas dans le `PATH`. Ouvre un nouveau terminal après l'installation.
- **Le code s'affiche dans une police de remplacement** : DejaVu Sans Mono n'est pas installée.
- **Erreur OpenGL au lancement** (machine virtuelle, bureau à distance) : mets à jour le pilote graphique ; sous Linux sans écran, lance avec `xvfb-run manimgl …`.
