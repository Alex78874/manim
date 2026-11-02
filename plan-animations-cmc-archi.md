# Série d'onboarding « cmc-archi » : plan des animations ManimGL

## 1. État du repo (vérifié le 27/10/2026 sur `main`, 15 commits)

Le dépôt est le socle de l'application **« Brigades Vertes »** de Clean My Calanques. Il prépare la **semaine intensive du 08 au 12/03/2027**, pendant laquelle l'équipe passe de 6 à environ 30 développeurs. Plusieurs sujets que tu veux présenter n'existent pas encore dans le code. Chaque épisode porte donc un statut.

| Sujet | État | Preuve |
|---|---|---|
| Contrat OpenAPI 3.1, SDK Orval, serveur AdonisJS, back-office React | **Implémenté.** 6 opérations : seConnecter, seDeconnecter, monProfil, listerUtilisateurs, creerUtilisateur, modifierUtilisateur. 29 tests Japa | `contract/`, `sdk/`, `server/`, `clients/web/` |
| Outillage | **Implémenté.** 4 scripts Node (`setup`, `feature`, `diagnostic`, `verifier` → `scripts/*.mjs`) et 2 chaînes `npm --prefix` (`sync`, `contract`) | `package.json` racine |
| **App mobile React Native** | **Absente.** `clients/` ne contient que `web/`. CLAUDE.md:40 dit « clients/app application mobile (à créer) ». Le plan prévoit Expo + SecureStore + une file hors ligne de novembre à janvier | `docs/tmp/plan-boilerplate-speedcoding.md:76-94` |
| **Gestion réseau / hors ligne mobile** | **Surtout documentée** (ADR 0006 et son annexe). Côté serveur, une seule fonction est codée et testée : `bornerOccurredAt()`, avec 7 tests unitaires. **Aucune route réelle ne l'appelle.** S'y ajoutent deux éléments de gabarit, utilisés seulement par `npm run feature` : le schéma de contrat `UuidV7.yaml` (aucune opération actuelle ne le référence) et la colonne `supprime_le`. Côté client, `sdk/src/custom-instance.ts` produit déjà NETWORK_ERROR et TIMEOUT_ERROR | `docs/adr/0006`, `server/app/services/horodatage.ts`, `scripts/feature.mjs:165, 268-275` |
| Clé d'idempotence, pagination par curseur, photos R2, push Expo, email de réinitialisation | **Décidés (ADR acceptés), non implémentés** | ADR 0006, 0014, 0015, 0016 ; README.md:86-88 |
| **CI/CD** | **Absente, et c'est voulu.** La décision du 17/10/2026 dit : « Rang 5 — ABANDONNÉ : pas de CI, tout en local ». `npm run verifier` en tient lieu sur le poste. Le hook pre-push proposé (`.githooks/`) n'est pas fait. Il n'y a ni Dockerfile ni déploiement. Plusieurs fichiers parlent pourtant encore de « la CI » (voir section 5) | `docs/tmp/plan-boilerplate-speedcoding.md:134-147` ; pas de `.github/` ni de `.githooks/` |
| **Message queue backend** | **Absente du code et de la doc.** Pas de bullmq, Redis, worker, events, listeners ni mails : seuls les alias du starter restent dans `server/package.json`. `docker-compose.yml` ne contient que traefik et postgres. Seule trace : une question ouverte, « envoi d'un email : directement depuis le service métier, ou par un événement ? » (`docs/adr/README.md:115-116`, ADR 0014, 0015). Des tâches de fond attendent un mécanisme : purge des photos orphelines (ADR 0016), purge de l'idempotence à 30 jours (ADR 0006) | grep sur le repo |
| Traefik | **Déclaré, mais ne route rien.** Aucun label, le serveur n'est pas conteneurisé et `setup` ne démarre que postgres | `docker-compose.yml`, `scripts/setup.mjs` |
| Données de dev | **Base vide.** Pas de factories ni de seeders : setup affiche « aucun seeder pour l'instant » | `scripts/setup.mjs:267-274`, plan rang 6 |
| Tests côté client | **Aucun.** Le script `test` de sdk fait `echo Error` et le web n'a pas de script de test | `sdk/package.json:6`, `clients/web/package.json` |

À retenir pour la série : **la « file d'attente » des documents est celle du téléphone (ADR 0006), pas une message queue serveur.** Il ne faut pas mélanger les deux dans les vidéos.

## 2. Stack et paquets (rôle réel, vérifié dans le code)

**Racine (`package.json`)** : aucune dépendance et aucun workspace. Le champ `"//"` l'explique : `setup` tourne avant le premier `npm install`. Six scripts :
- 4 lancent du Node pur (`scripts/*.mjs`, avec seulement des modules `node:`) ;
- `sync` et `contract` enchaînent des `npm --prefix …` qui appellent les outils de contract, sdk et server.

`.nvmrc` vaut 24, mais `scripts/lib.mjs` n'exige que Node 22. L'ordre des paquets est codé en dur : contract → sdk → server → clients/web. Les quatre paquets sont des îlots, reliés par des artefacts :
- `contract/dist/openapi.json` sert à la fois au sdk et à la copie côté serveur ;
- `server/app/contract/openapi.json` est cette copie ;
- `sdk/dist` arrive dans le web via `file:../../sdk`.

| Partie | Paquet | Rôle réel |
|---|---|---|
| contract | `@redocly/cli` | `redocly bundle openapi.yaml -o dist/openapi.json` fusionne les YAML de `features/` en un seul JSON, l'artefact que tout le monde consomme |
| contract | `@stoplight/spectral-cli` | Lint du bundle. Le ruleset `.spectral.yaml` se limite à `extends: spectral:oas`, sans règle maison |
| sdk | `orval` | Génère depuis le bundle les fonctions fetch, les hooks React Query, les modèles et les mocks MSW + faker (`orval.config.ts` : tags-split, `client: react-query`, `mock: true`, mutator `src/custom-instance.ts`). `generate` enchaîne nettoyer, orval et tsc |
| sdk | `@tanstack/react-query`, `msw`, `@faker-js/faker`, `react` (dev + peer) | Cibles du code généré. Les mocks sortent par l'entrée séparée `@cmc/sdk/msw` |
| sdk | `typescript` | `tsc` compile vers `dist/`. Le web consomme `sdk/dist`, pas `src` |
| server | `@adonisjs/core` | Routeur, kernel, providers (dont `contract_provider.ts`), `createError`, hash, ace `codegen` |
| server | `@adonisjs/lucid` + `pg` | ORM et 4 migrations sur PostgreSQL 16. `migration:run` régénère `database/schema.ts`, **committé** (nécessaire au typecheck). Le code PG 23505 devient un 409 |
| server | `@adonisjs/auth` | Garde `api` = tokensGuard + `DbAccessTokensProvider` sans `expiresIn` : jeton opaque haché (ADR 0005). Un garde `web` (session) est configuré mais aucune route ne l'utilise |
| server | `ajv` + `ajv-formats` | **Cœur du contract-first.** Deux instances Ajv2020 dans `contract_validator.ts` : une stricte (corps, réponses) et une souple (query/params, avec coercition et défauts) |
| server | `openapi-typescript` (dev) | `sync:contract` génère `app/contract/types.ts`, qui type les services et les operationId |
| server | `luxon` | Dates, et bornage d'`occurredAt` (`horodatage.ts`) |
| server | `@japa/*` | Tests unit (7) et functional (contrat 3, session 7, utilisateurs 12). Chaque test tourne dans une transaction annulée, sur le port 3334 |
| server | `@tuyau/core` | `generateRegistry()` sert seulement à typer le client de test Japa. Ce n'est pas le client des fronts |
| server (mineurs) | `@adonisjs/cors` (ouvert en dev), `@adonisjs/shield` (HSTS, X-Frame), `@adonisjs/session` (hérité du starter), `@vinejs/vine` (quasi inutilisé : une seule transformation de date dans `start/validator.ts` ; **la validation passe par Ajv**), `reflect-metadata`, `@adonisjs/assembler`, `hot-hook`, `@poppinss/ts-exec`, `eslint` + `@adonisjs/eslint-config` (avec contrôle Prettier), `prettier`, `youch`, `pino-pretty` (non référencé) | Outillage et restes du starter kit. Les alias `#events`, `#listeners`, `#mails`, `#policies` et `#abilities` sont orphelins |
| clients/web | `@cmc/sdk` (`file:../../sdk`) | Seule porte vers l'API : `configureSdk`, hooks, types, `@cmc/sdk/msw`. Aucun `fetch` écrit à la main |
| clients/web | `react` 19, `react-dom`, `@tanstack/react-query` | UI et cache (QueryClient avec `retry: false` et `staleTime` de 30 s) |
| clients/web | `msw`, `@faker-js/faker` (dev) | Front sans serveur si `DEV && VITE_USE_MOCKS=true`. Erreurs simulées avec `VITE_MOCK_ERRORS` |
| clients/web | `vite` 8 + `@vitejs/plugin-react` | Dev sur :5173 et build. `resolve.dedupe` et `optimizeDeps.exclude` contournent les pièges du SDK lié par `file:` |
| clients/web (mineurs) | `typescript`, `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals`, `@types/*` | Typecheck et lint (étapes 5 et 6 du verifier) |

Absents, à dire aux nouveaux : `expo`, `react-native`, `expo-sqlite`, NetInfo, SecureStore, toute bibliothèque UUIDv7, `bullmq`, Redis, un mailer, `@adonisjs/bouncer`, `c8`, et tout runner de test côté client.

## 3. Épisodes, dans l'ordre pédagogique

Chaque épisode ne réutilise que des notions vues avant lui. La série se découpe en deux saisons :
- **Saison 1** (épisodes 1 à 33) : ce qui existe, plus les règles hors ligne **non négociables** que le gabarit génère déjà.
- **Saison 2** (épisodes 34 à 40) : conception du client mobile et briques prévues, à produire au fil des ADR et du code.

### Bloc A — Le décor

**1. Le métier, la contrainte et l'échelle** · 60-75 s · documenté · Manim : moyen
- Objectif : donner le vocabulaire et les deux contraintes qui justifient l'architecture (pas de réseau, 30 développeurs).
- Scénario :
  - Sur une carte stylisée, des bénévoles se regroupent en brigade, avec une étoile pour la référente.
  - Un ramassage produit un bilan (participants, kg, photos). Les compteurs défilent : 601 membres, 528 ramassages, 5,6 t.
  - **Les barres de réseau tombent à zéro dans la calanque** : « la saisie sans réseau est un critère de recette ». Un badge « en attente d'envoi » sert de teaser de la file.
  - Une frise de sept. 2026 à juin 2027 (27/11 specs, 08-12/03 semaine intensive, 24/06 livraison). 6 devs deviennent 30, et une règle floue se divise en 30 flèches.
  - Fin : les engagements (70 % de tests sur le métier, < 2 s en 4G, vieux téléphones, RGPD).
- Sources : `docs/contexte-projet.md:21-96, 165-210, 233-248`, `docs/vocabulaire.md`, `CLAUDE.md:7-9`.

**2. La carte de l'architecture : plein = existe, pointillé = décidé** · 60-90 s · implémenté + prévu · Manim : **fort**
- Objectif : une seule image mentale du système. Ce « plan de métro » sera réutilisé en ouverture des épisodes suivants.
- Scénario :
  - `contract/openapi.yaml` s'allume au centre, puis des flèches partent vers `server/` (AdonisJS) et `sdk/` (Orval).
  - `sdk/` alimente `clients/web` en trait plein et `clients/app` en **pointillé**, étiqueté « à créer ».
  - `server/` se relie à PostgreSQL 16 (docker). Les flèches HTTP Bearer `/api/v1` vont des clients au serveur.
  - En pointillé : R2, push Expo, fournisseur d'email, et une case « événements / file ? ». Traefik est grisé : « déclaré, ne route rien ».
- Sources : `contract/openapi.yaml:1-26`, `CLAUDE.md:33-42`, `docker-compose.yml`, ADR 0014/0015/0016, `docs/adr/README.md:115-116`.

**3. Quatre îlots sans workspace, reliés par des artefacts** · 30 s · implémenté · Manim : moyen
- Objectif : répondre à « comment fonctionne le repo ».
- Scénario :
  - Quatre `package.json` flottent séparément, chacun avec son `npm ci`.
  - Trois ponts s'animent : le bundle `dist/openapi.json`, la copie dans `server/app/contract/`, puis `sdk/dist` → `file:` → web, avec un panneau « à reconstruire ».
  - La racine reste vide : « setup tourne avant tout npm install ».
- Sources : `package.json` (champ `"//"`), `clients/web/package.json:13`, `server/scripts/sync-contract.mjs`, README.md:158-159.

### Bloc B — Le repo au quotidien et le contract-first

**4. Les cinq commandes, puis `npm run setup`** · 75 s · implémenté · Manim : **fort**
- Objectif : la carte des outils, puis le premier jour.
- Scénario :
  - `setup`, `feature`, `sync`, `diagnostic` et `verifier` apparaissent, chacune avec son moment.
  - Écran scindé. À gauche, la console de setup : ✓ Node, .env créés, APP_KEY, `npm ci` ×4 dans l'ordre, sablier `pg_isready` (60 s au plus), sync, migrations, « aucun seeder pour l'instant ».
  - À droite, l'arborescence se peuple au même rythme. Fin sur « Prêt à coder. », devant une base vide.
  - Encart de 10 s : les deux `.env` à accorder (ce que vérifie `diagnostic`).
- Sources : `CLAUDE.md:25-31`, `scripts/setup.mjs`, `scripts/lib.mjs`, `scripts/diagnostic.mjs`.

**5. Un YAML, quatre consommateurs, et le fil des EXG** · 60 s · implémenté · Manim : **fort**
- Objectif : poser le modèle mental du contract-first. Une seule source est écrite à la main, le reste est dérivé. C'est un zoom de la carte de l'épisode 2.
- Scénario :
  - Des flèches sortent du YAML vers `dist/openapi.json`, `types.ts` et Ajv côté serveur, puis vers les hooks, le client et les mocks côté SDK.
  - Une flèche inverse (code → YAML) tente de remonter et se brise : « un type partagé absent du contrat = bug du contrat ».
  - Second plan : un fil `EXG-USR-004` relie `docs/specs/utilisateurs.md`, la description YAML et le libellé du test.
- Sources : `docs/adr/0001`, `docs/specs/utilisateurs.md:8-27`, `server/tests/functional/utilisateurs.spec.ts`.

**6. Anatomie de `contract/` : suivre les `$ref`** · 60 s · implémenté · Manim : **fort**
- Objectif : savoir où écrire un chemin, un schéma ou une réponse partagée.
- Scénario :
  - Deux panneaux IDE. Le curseur suit `/utilisateurs` → `paths/utilisateurs.yaml` → `CreationUtilisateur.yaml` → `_shared/responses/BadRequest.yaml` → `ApiError.yaml`.
  - L'arborescence `features/{session,utilisateurs,_shared}` se colore à chaque saut.
  - Fin sur les conventions : operationId en camelCase, `additionalProperties: false`, EXG dans la description, 400 et non 422, ordre alphabétique, même profondeur de `$ref`.
  - Note : Spectral ne vérifie aucune de ces conventions (ruleset `spectral:oas` seul).
- Sources : `contract/openapi.yaml:16-25, 43-85`, `contract/features/utilisateurs/paths/utilisateurs.yaml`, `contract/.spectral.yaml`.

**7. `npm run sync` : la chaîne de génération, et pourquoi elle n'est pas versionnée** · 90-105 s · implémenté · Manim : **fort**
- Objectif : savoir ce que produit la commande à lancer après chaque `git pull`, et pourquoi un clone frais ne compile pas.
- Scénario :
  - Quatre stations s'allument :
    1. `redocly bundle` puis `spectral lint` ;
    2. nettoyer, Orval (`endpoints/…`, `*.msw.ts`, `model/`), puis tsc → `dist/` ;
    3. `sync-contract.mjs` puis openapi-typescript → `types.ts` ;
    4. `node ace codegen` → `.adonisjs/`.
  - Chaque fichier généré porte un cadenas « gitignored ».
  - ADR 0010 : deux branches modifient `model/index.ts` et un diff rouge se remplit. Une fois les dossiers sortis de git, un clone frais échoue sur « Cannot find module '#contract/types' », puis `sync` le répare.
  - Exception à dire : `server/database/schema.ts` reste **committé** (voir épisode 15).
  - Encart : un tag renommé sans nettoyage laisse un `export *` mort, et tsc passe au rouge.
- Sources : `package.json` (script `sync`), `sdk/orval.config.ts`, `server/scripts/sync-contract.mjs`, `docs/adr/0010`, `.gitignore:12-21`, commit `30d6d92`, plan:51.

**8. Un operationId, quatre noms (et un seul grep)** · 45-60 s · implémenté · Manim : **fort**
- Objectif : le nommage sert d'outil de navigation.
- Scénario :
  - `listerUtilisateurs` devient, par TransformMatchingStrings : `listerUtilisateurs()`, `useListerUtilisateurs()`, `getListerUtilisateursMockHandler`, `middleware.contract({ operationId: 'listerUtilisateurs' })`, `UtilisateursController.lister`, `utilisateursService.lister`.
  - `grep -r listerUtilisateurs` fait tout s'allumer.
  - Ligne de 5 s : ce qui reste en anglais et pourquoi (`email`, `password`, `createdAt`, `items/total/page/limit`, `EMAIL_ALREADY_USED`).
- Sources : `docs/vocabulaire.md:58-80` et section « Ce qui reste en anglais », `docs/adr/0008`, `server/start/routes/utilisateurs.ts`, `sdk/src/msw.ts`.
- Attention : lancer `npm run sync` avant de capturer les noms générés. L'historique `30d6d92^` contient encore les noms anglais.

### Bloc C — Le serveur AdonisJS

**9. Le serveur refuse de démarrer, et ce qu'il ne vérifie pas** · 75 s · implémenté · Manim : **fort**
- Objectif : « toute route déclare son operationId » est une impossibilité technique. Il faut aussi en montrer les limites.
- Scénario :
  - À gauche, `start/routes/utilisateurs.ts`. À droite, la console de `npm run dev`.
  - Le curseur efface `.use(middleware.contract(...))`. Les routes et les opérations forment un diagramme de Venn, et l'orpheline clignote.
  - La console affiche en rouge le `logger.fatal` « Le contrat et les routes ne concordent pas », puis exit 1.
  - Variantes : un operationId mal orthographié, `/users/{id}` contre `/utilisateurs/{id}`.
  - Une opération sans route ne donne qu'un `logger.warn` jaune en dev. Hors dev ou avec `CI=true`, elle devient bloquante : renvoyer à l'épisode 30, puisqu'il n'y a pas de CI.
  - Fin : la même fonction tourne dans `contract.spec.ts`.
  - **Encart de 10 s, « ce qui n'est pas vérifié »** : seuls l'operationId, le chemin et la méthode sont comparés. Une route que le YAML dit `security` peut être servie sans `middleware.auth()` sans aucune alerte. La liste HORS_CONTRAT est vide et doit le rester, et `router.resource()` est refusé.
  - Attention : aucun log « N opérations compilées » n'existe. Un démarrage réussi ne journalise rien du garde-fou, donc une telle ligne serait une illustration et non une vraie sortie.
- Sources : `server/providers/contract_provider.ts:53-198`, `server/tests/functional/contract.spec.ts`, `server/start/routes.ts` (en-tête), `contract/features/session/paths/moi.yaml:14`.

**10. Le voyage d'une requête : l'oignon des middlewares** · 90 s · implémenté · Manim : **fort**
- Objectif : savoir où vit chaque responsabilité, donc où chercher un bug.
- Scénario :
  - `PATCH /api/v1/utilisateurs/:id` traverse trois couches.
  - Serveur : force_json → container_bindings → cors.
  - Routeur : bodyparser → session → shield → initialize_auth → silent_auth.
  - Route : `auth()` puis `contract()`. On ne valide pas un corps destiné à un 401.
  - Puis contrôleur, service, Lucid et PostgreSQL. Au retour, la réponse repasse par `contract()`. La ligne de `start/kernel.ts` est surlignée à chaque étape.
- Sources : `server/start/kernel.ts:25-56`, `server/start/routes.ts`, `server/app/middleware/*`.

**11. Contrôleur mince, service épais, projection unique (ADR 0004)** · 60 s · implémenté · Manim : **fort**
- Objectif : savoir où écrire une règle métier, et introduire `versContrat` avant l'épisode 12.
- Scénario :
  - Un contrôleur de 40 lignes se vide vers `utilisateurs_service.ts` et finit à 3 lignes.
  - Zoom sur `versContrat`, qui copie champ par champ : `password` est barré à la frontière.
  - Une couche « repository » apparaît puis est barrée (alternative écartée).
- Sources : `docs/adr/0004`, `server/app/controllers/utilisateurs_controller.ts`, `server/app/services/utilisateurs_service.ts:73-85`.

**12. Le middleware de contrat dans les deux sens (pièce maîtresse)** · 2 min · implémenté · Manim : **fort**
- Objectif : distinguer 400 (faute du client) et 500 (bug du serveur), et voir le YAML s'exécuter.
- Scénario :
  - A) `?page=2` devient le nombre 2 et `limit` reçoit 20 par défaut. `?limite=5` donne un 400.
  - B) Un `POST` avec `role: 'administrateur'` donne 400 VALIDATION_ERROR avec `details[{path:'/role'}]`. Le contrôleur n'est jamais atteint (EXG-USR-004).
  - C) `versContrat(u)` est remplacé par le modèle entier : 500 CONTRACT_RESPONSE_VIOLATION.
  - D) En `inProduction`, un simple `logger.error`, et la réponse part.
  - Encart : 403 et 409 sortent par le handler, sans validation.
  - Les messages Ajv s'affichent en anglais (voir section 5).
- Sources : `server/app/middleware/contract_middleware.ts:31-92`, `server/app/services/contract_validator.ts:136-311`, `server/app/exceptions/handler.ts:15-19`, `server/tests/functional/utilisateurs.spec.ts:127-143`.

**13. Le contrat valide la FORME, le service valide le MÉTIER** · 45 s · implémenté · Manim : **fort**
- Objectif : la première décision quand on écrit une fonctionnalité : « cette règle va-t-elle dans le YAML ou dans le service ? ».
- Scénario :
  - Les cartes EXG-USR-001 à 008 et EXG-AUTH-001 à 004 tombent dans deux bacs, « contrat » (5 sur 8 pour utilisateurs) et « service ».
  - Fin sur EXG-AUTH-004 : « le contrat sait dire qu'un 401 existe, pas qu'il doit être indiscernable d'un autre ».
- Sources : `docs/specs/utilisateurs.md:8-27`, `docs/specs/session.md:61-77`, `server/app/services/utilisateurs_service.ts:13-14`.

**14. Les erreurs côté serveur, et « ne rien révéler »** · 60 s · implémenté · Manim : moyen
- Objectif : un seul endroit décide de la forme des erreurs, et deux règles de sécurité qu'on « corrigerait » de bonne foi.
- Scénario :
  - `EmailDejaUtilise` (createError, 409) remonte au handler et ressort en `{code, message}`.
  - `E_UNAUTHORIZED_ACCESS` devient UNAUTHORIZED. Un 5xx donne youch en dev et INTERNAL_ERROR en prod.
  - Deux 401 se superposent exactement : mauvais mot de passe et email inconnu (EXG-AUTH-004).
  - Dans `modifier()`, le 403 passe avant le 404. Le mauvais ordre permet d'énumérer les comptes.
- Sources : `server/app/exceptions/handler.ts:30-66`, `server/app/services/session_service.ts:31-59`, `server/app/services/utilisateurs_service.ts:183-208`.

**15. Deux sources de types : migrations → `schema.ts` → modèle, et le contrat** · 45 s · implémenté · Manim : **fort**
- Objectif : voir l'autre chaîne de génération, celle de la base.
- Scénario :
  - Rail du bas : une migration, puis `migration:run`, puis `database/schema.ts` (« DO NOT EDIT », committé), puis `UtilisateurSchema`, puis le modèle Lucid, qui ne déclare pas ses colonnes.
  - Rail du haut : YAML, puis `types.ts`.
  - Les deux rails convergent dans `versContrat`.
  - Note : `npm run feature` ne génère pas le modèle, c'est une étape manuelle.
- Sources : `server/app/models/utilisateur.ts:7-18`, `server/database/schema.ts:1-5`, `scripts/feature.mjs:323`, README.md:169, plan:51.

**16. Les tests Japa : traçabilité EXG et stratégie** · 60 s · implémenté · Manim : moyen
- Objectif : écrire un test qui porte l'EXG et ne pollue pas la base, et connaître la stratégie.
- Scénario :
  - Un test se déroule : BEGIN (`withGlobalTransaction`), `creerUtilisateur` écrit directement en base, requête HTTP sur le port 3334, assertions, ROLLBACK.
  - La console lance un filtre sur le **titre complet**, ou `--files=session`. Le titre est « EXG-AUTH-004 — email inconnu et mot de passe erroné sont indiscernables ». À tester avant de filmer, car `--tests` filtre probablement sur le titre exact.
  - Plan final : unit contre functional, « un invariant métier a droit aux deux tests », 70 % exigé et non mesuré (pas de c8), `grep TODO-EXG`, **zéro test côté sdk et web**.
- Sources : `server/tests/bootstrap.ts`, `server/tests/helpers.ts:72-121`, `server/tests/functional/session.spec.ts:114`, `server/.env.test`, plan:190-206, `sdk/package.json:6`.

**17. Concurrence : la contrainte d'unicité plutôt qu'un SELECT** · 60 s · implémenté · Manim : **fort**
- Objectif : le motif à recopier pour toute règle d'unicité.
- Scénario :
  - Une timeline à deux pistes. Mauvaise version : SELECT, SELECT, INSERT, INSERT, donc deux comptes.
  - Bonne version : INSERT dans un savepoint, puis 23505 et 409 EMAIL_ALREADY_USED.
  - Sans savepoint, la transaction de l'appelant (celle du test, vue à l'épisode 16) passe en « aborted ».
  - Encart : avec la suppression douce (épisode 29), la contrainte doit ignorer les lignes supprimées.
  - Précision : le test EXG-USR-003 est séquentiel, la course est une illustration.
- Sources : `server/app/services/utilisateurs_service.ts:116-177`, `server/tests/functional/utilisateurs.spec.ts:108-125`, ADR 0013:55-57.

**18. Qui a le droit ? Rôle global contre référent·e (ADR 0009)** · 30-40 s · documenté (+ 403/404 codé) · Manim : moyen
- Objectif : ne jamais tester le rôle global pour un droit de brigade.
- Scénario :
  - La même personne porte une étoile dans la brigade du Panier et n'est qu'un simple point ailleurs. La même requête reçoit deux réponses différentes.
  - Une case `estReferentDe()` en pointillé : la décision n'est pas encore consignée.
  - Pas de bouncer, et les alias `#policies` sont orphelins.
- Sources : `docs/adr/0009:21-47`, `docs/adr/README.md:117-119`, `server/package.json:33-34`.

**19. Le jeton opaque sans expiration (ADR 0005)** · 60-75 s · implémenté · Manim : **fort**
- Objectif : un choix contre-intuitif, expliqué par le hors ligne (teaser de l'épisode 1).
- Scénario :
  - `verifyCredentials` s'exécute en temps constant. `oat_…` est rendu une fois (`release()`), et seule l'empreinte reste en base.
  - Deux appareils sont connectés. Le téléphone se déconnecte, et le navigateur obtient toujours 200 sur `/moi`.
  - Contrefactuel : un JWT de 15 min devant une file de 5 h.
- Sources : `server/app/services/session_service.ts:61-87`, `server/app/models/utilisateur.ts:19`, `docs/adr/0005`, `server/tests/functional/session.spec.ts:49-73`.

### Bloc D — Le back-office web et le SDK

**20. Développer sans serveur : MSW et l'ordre de démarrage** · 75 s · implémenté · Manim : **fort**
- Objectif : le front est productif dès le merge du contrat.
- Scénario :
  - Navigateur, Service Worker en bouclier, serveur éteint.
  - Les blocs de `main.tsx` s'allument : `configureSdk`, puis `await worker.start()`, puis `createRoot`. Des noms faker défilent.
  - Avec `VITE_USE_MOCKS=false`, la même requête atteint Adonis et répond **un vrai 200** : `listerUtilisateurs` et `creerUtilisateur` sont des routes publiques, donc aucun jeton n'est nécessaire. Aucun caractère du composant ne change.
  - Variante : le mauvais ordre de démarrage.
  - Encart : `import.meta.env.DEV` élimine msw et faker du build.
- Sources : `clients/web/src/main.tsx:8-83`, `clients/web/.env.example`, `sdk/src/msw.ts`, `server/start/routes/utilisateurs.ts`.

**21. Du hook à `fetch` : customInstance et le cache React Query** · 90 s · implémenté · Manim : **fort**
- Objectif : qui fait quoi côté client, et le pont vers le mobile.
- Scénario :
  - La clé `['/utilisateurs', params]` est calculée. Le cache est vide, donc `customInstance` s'exécute : URL, Content-Type, Bearer si `getToken`, chronomètre de 10 s.
  - Arbre des retours, qui aboutit toujours à une ApiError : 2xx, non-ok `{code, message, details}`, NETWORK_ERROR, SDK_NOT_CONFIGURED.
  - Cache servi en moins de 30 s. `invalidateQueries(['/utilisateurs'])` après une création.
- Sources : `sdk/src/custom-instance.ts`, `clients/web/src/utilisateurs/*.tsx`, `clients/web/src/main.tsx:28-38`.
- Attention : la feuille TIMEOUT_ERROR est probablement morte (section 5, point 4), et aucun runner de test ne permet de le vérifier. Il faut la corriger ou la retirer avant de filmer.

**22. Le bug du `/api/v1` invisible** · 45 s · implémenté · Manim : **fort**
- Objectif : une vraie histoire de bug, qui montre la limite des mocks à joker.
- Scénario :
  - `new URL('/utilisateurs', 'http://localhost:3333/api/v1')` : le `/` initial efface `/api/v1`.
  - En mode mocks, `'*/utilisateurs'` intercepte quand même, ce qui donne une coche verte trompeuse. Avec le vrai serveur, 404.
  - La correction par concaténation répond 200.
  - Encart : `PREFIXE_API`, `.prefix()` et `VITE_API_URL` doivent rester d'accord.
- Sources : `sdk/src/custom-instance.ts:53-66`, plan:255-262, `server/start/routes.ts:26-48`.

**23. Les erreurs du contrat jusqu'au message sous le champ** · 60 s · implémenté · Manim : **fort** (suite directe de l'épisode 14)
- Scénario :
  - `VITE_MOCK_ERRORS=true` place `handlersDErreur` en tête : la première correspondance gagne.
  - Branche A : un email contenant « deja » donne 409, et le formulaire teste `code === 'EMAIL_ALREADY_USED'`.
  - Branche B : 400 avec `details`. `erreursParChamp` transforme `/email` en `email`, et chaque message se pose sous son input.
  - Plan final : `role` est absent de `CreationUtilisateur`, et TypeScript souligne un `role:'administrateur'`.
- Sources : `clients/web/src/mocks/erreurs.ts`, `clients/web/src/utilisateurs/formulaire-utilisateur.tsx:5-50`, `contract/features/_shared/schemas/ApiError.yaml`.

**24. Le contrat casse la compilation (synthèse)** · 45 s · implémenté · Manim : **fort**
- Objectif : le contrat est garanti à la compilation, et le test complète ce que le compilateur ne voit pas.
- Scénario :
  - Cas 1 : `telephone` (required) est ajouté à `Utilisateur.yaml`, puis `npm run sync`. **Seul `versContrat` est souligné en rouge.** Une fois corrigé, `npm test` fait échouer **à l'exécution** le test des clés exactes. Rien ne bouge côté web : un champ de réponse ne casse pas le front.
  - Cas 2 : un champ required est ajouté à `CreationUtilisateur`. Cette fois, le formulaire web est souligné.
  - Fin sur la phrase du README : « le compilateur désigne exactement ce qu'il y a à corriger ».
- Sources : `server/app/services/utilisateurs_service.ts:73-85`, `server/tests/functional/utilisateurs.spec.ts:254`, `clients/web/src/utilisateurs/formulaire-utilisateur.tsx`, `README.md:29-41`.
- À faire : vérifier le cas 2 par un vrai `tsc` avant de filmer.

### Bloc E — Les règles hors ligne non négociables (déjà dans le gabarit)

**25. Pourquoi le hors-ligne change le contrat** · 45 s · documenté · Manim : **fort**
- Objectif : montrer le problème avant les solutions.
- Scénario :
  - Lire hors ligne est facile : la liste « chargée à 13h52 » reste affichée.
  - Écrire est le vrai problème : « Bilan Sugiton 12 kg » reste en attente, et la file le rejoue **cinq heures plus tard**.
  - Quatre pannes s'affichent, chacune avec son épisode : état écrasé (26), id inconnu (27), mauvaise date (28), ligne supprimée invisible (29).
- Sources : ADR 0006:84-139, `CLAUDE.md:52-61`.

**26. Intention relative contre état calculé (ADR 0007)** · 75 s · documenté · Manim : **fort**
- Scénario :
  - Deux téléphones lisent `stock: 15`. Avec `PATCH {stock:12}` envoyé deux fois, le serveur affiche 12 alors que 6 pinces sont sorties.
  - Avec `POST /materiels/{id}/retraits {quantite:3}` deux fois, le résultat est 9.
  - Suite : le 409 qui arrive cinq heures plus tard. Pour la dernière place d'une sortie, A s'inscrit hors ligne à 9h, B en ligne à 11h, et A reçoit le 409 en rejouant.
  - Les quatre ressources arbitrées par le serveur, et la question ouverte « liste d'attente ou signalement ? ».
  - Encart : les actions nommées `/annulation`, et la syntaxe `:annuler` écartée.
- Sources : `docs/adr/0007`, ADR 0006:101-120, 294-301 et annexe, `CLAUDE.md:52-53`.

**27. UUIDv7 fourni par le client (ADR 0012)** · 75 s · contrat + gabarit, aucune opération actuelle · Manim : **fort**
- Scénario :
  - Un id v7 se fabrique : préfixe horodaté, « 7 », `[89ab]`. Trois participants pointent déjà vers lui ; avec un id serveur, les flèches pointent vers « ??? ».
  - Dans un B-tree, les v4 tombent au hasard et les v7 s'ajoutent en fin.
  - La regex de `UuidV7.yaml` refuse un v4 en 400, ce que vérifie le test généré.
  - Bandeau : « référencé uniquement par le gabarit `npm run feature` ».
- Sources : `docs/adr/0012`, `contract/features/_shared/schemas/UuidV7.yaml:28-30`, `scripts/feature.mjs:141-174, 474-502`.

**28. `occurredAt` contre `createdAt`, et la borne serveur** · 45-60 s · fonction codée et testée, non branchée · Manim : **fort**
- Scénario :
  - Saisie à 14h (`occurredAt`), enregistrement à 19h (`createdAt`) : les statistiques sont justes ou fausses selon l'horodatage retenu.
  - Une NumberLine de −30 j à +60 s : 2099 et J−31 sont refusés (HORS_BORNES), +59 s est accepté, « hier » est ILLISIBLE.
  - Les deux `if` de `bornerOccurredAt()` s'allument, avec le paramètre `maintenant` injectable.
  - Bandeau : « appelée seulement par le service généré ».
- Sources : `server/app/services/horodatage.ts`, `server/tests/unit/horodatage.spec.ts`, ADR 0006 §4.3, `scripts/feature.mjs:298, 352`.

**29. Rien n'est supprimé : suppression douce (ADR 0013)** · 60 s · colonne dans le gabarit, filtre à écrire · Manim : **fort**
- Scénario :
  - Synchro delta. Avec une suppression franche, le téléphone garde un fantôme. Avec `supprime_le`, la ligne revient marquée.
  - Anonymisation d'un compte : il reste `{id, supprimeLe}`, et les bilans gardent leurs kg. Seules les photos sont réellement détruites.
  - Fin : dans le service généré, `.whereNull('supprime_le')` n'apparaît **que dans un TODO commenté**, et `lister()` renvoie une liste vide. C'est au développeur d'écrire la requête : « la faute la plus facile à commettre ».
  - Rappel de l'encart sur l'unicité (épisode 17).
- Sources : `docs/adr/0013`, `scripts/feature.mjs:268-275, 321-338`.

### Bloc F — Une fonctionnalité de bout en bout (le « CI » actuel)

**30. `npm run verifier` : la seule barrière** · 60 s · implémenté · Manim : **fort**
- Scénario :
  - Pré-vol `migration:status`, puis 7 étapes par coût croissant, chacune avec ✓ et sa durée.
  - Un `$ref` cassé arrête tout à l'étape 1, avec le remède `→ cd contract && npm run validate`.
  - Bandeau : « pas de CI (décision du 17/10/2026). Ceci est la barrière, et rien n'oblige à la lancer. »
  - Ne pas recopier « Tests 22 passed » de l'en-tête : il y a 29 tests.
- Sources : `scripts/verifier.mjs:35-129`, plan:134-147.

**31. Le cycle d'une fonctionnalité, et la réalité de mars** · 45 s · implémenté + organisation · Manim : moyen
- Scénario :
  - Trois couloirs : spec, front, back. Spec puis YAML, puis une PR de YAML seul. Au merge, le front (sur mocks) et le back démarrent ensemble.
  - L'avertissement jaune de l'épisode 9 s'éteint à la livraison.
  - Second plan, le calendrier en V : contrat écrit avant le 27/11, **gelé** pendant la semaine de mars (CODEOWNERS prévu, non créé). Le point d'entrée d'un renfort est : contrat déjà là, puis sync, migration, modèle, service et tests.
- Sources : `docs/adr/0001` (Conséquences), `docs/contexte-projet.md:182-185, 198-201`, plan:208-220, `server/providers/contract_provider.ts:172-185`.

**32. `npm run feature ramassages` : la tranche verticale** · 90 s · implémenté · Manim : **fort**
- Scénario :
  - L'arbre fait pousser 10 fichiers : 3 schémas, 1 path, migration, service, contrôleur, routes, test, spec.
  - Les trois fichiers-listes (`openapi.yaml`, `server/start/routes.ts`, `sdk/src/msw.ts`) reçoivent chacun une ligne **à sa place alphabétique**.
  - Comparaison A/B, corrigée :
    - `brigades` et `sorties` tombent à des places séparées par `session` : git fusionne seul.
    - `brigades` et `ramassages` s'insèrent au **même endroit**, avant `session` : conflit `<<<<<<<`, qui se résout en gardant les deux lignes.
    - Message : l'alphabétique réduit les conflits sans les supprimer.
  - Encart « `utilisateurs` ≠ gabarit » : `gen_random_uuid()`, ni `supprime_le` ni `occurredAt`. Ne pas copier `utilisateurs` pour une ressource hors ligne.
  - Fin : la liste des 7 étapes, puis un verifier vert. Compter les tests en vrai avant d'afficher un chiffre.
- Sources : `scripts/feature.mjs:91-706` (insertions 537-598), README « Créer une fonctionnalité » et « Les cinq fichiers partagés » (README.md:178-193), `server/database/migrations/1761885935168_create_users_table.ts:25`, `scripts/feature.mjs:260-264`.

**33. (bonus) Récapitulatif : la carte, repassée en couleur** · 20 s · Manim : moyen
- La carte de l'épisode 2 réapparaît, avec chaque zone étiquetée par son numéro d'épisode. Elle sert de générique de fin de saison 1.

### Saison 2 — Bloc G : le mobile et le réseau (conception)

Chaque épisode de ce bloc porte le bandeau **« conception acceptée, non codée »**.

**34. Le voyage d'une saisie hors ligne, de « Valider » au 201** · 90 s · documenté · Manim : **fort** (épisode pivot)
- Scénario :
  - Écriture optimiste dans le cache. Une ligne s'insère dans « FILE (SQLite) » : id, operationId=creerBilan, payload, cleIdempotence, occurredAt, essais, statut.
  - Le téléphone redémarre et la ligne est toujours là.
  - Une tâche de fond réveille la file, qui appelle `creerBilan()` puis `customInstance`. Réponse 201, et le badge passe à la coche verte.
- Sources : ADR 0006:84-139, `sdk/src/custom-instance.ts`.

**35. L'aiguillage à quatre voies, l'ordre par agrégat et la cascade** · 75 s · documenté · Manim : **fort**
- Scénario :
  - Quatre voies dès le départ :
    - 2xx → réconcilier ;
    - 5xx, NETWORK_ERROR, 408 ou 429 → retenter à 1 min, 5, 15, 1 h, 6 h ;
    - **401 → pause** (la file reste intacte et l'app demande de se reconnecter, ADR 0014) ;
    - autres 4xx → LETTRE MORTE et écran « saisies refusées ».
  - Contre-exemple : sans lettre morte, les essais montent jusqu'à 47.
  - Deux sous-files R1 et B7 : la création de R1 prend un 403, ses inscriptions se grisent, et B7 continue.
- Sources : ADR 0006:135-153, 270-281, ADR 0005:32-38, ADR 0014:53-56.

**36. La clé d'idempotence : la réponse perdue en route** · 60 s · **prévu** · Manim : **fort**
- Scénario :
  - Sans clé, le 201 se perd, le rejeu crée deux bilans.
  - Avec `Idempotency-Key`, la table (cle, operationId, statut, reponse, cree_le) renvoie la première réponse.
  - Purge à 30 jours, qui renvoie à l'épisode 39.
- Sources : ADR 0006:160-175, ADR 0012:51-57, README.md:86-88.

**37. Photos : le bilan d'abord, la photo directement vers R2 (ADR 0016)** · 60-75 s · **prévu** · Manim : **fort**
- Scénario :
  - En multipart, 5 Mo bloquent le bilan.
  - Bonne version : bilan JSON (201), WebP, URL signée, envoi direct à R2, confirmation. Une coupure à l'étape 4 ne rejoue que l'étape 4.
  - Les photos orphelines sont ramassées par une tâche de fond (épisode 39).
- Sources : ADR 0016:20-52, ADR 0006:223-235.

**38. Retour du réseau : synchro delta et curseur** · 60 s · documenté · Manim : **fort**
- Scénario :
  - Avec page=1 puis page=2, une insertion en tête fait sauter la ligne 20. Avec un curseur, rien n'est sauté.
  - Rappel des pierres tombales (épisode 29).
  - Note : le gabarit génère encore page/limit.
- Sources : ADR 0006:237-268, `scripts/feature.mjs:192-207`.

### Bloc H — Asynchrone backend (à produire après décision)

**39. Notifications et tâches de fond : la liste fait foi, et la question de la file** · 60 s · **prévu** · Manim : moyen aujourd'hui, fort une fois l'ADR écrit
- Scénario :
  - Un ramassage annulé ajoute une ligne `notifications` et envoie un push Expo. Le push échoue trois fois, mais la liste est à jour au lancement suivant.
  - Deux options étiquetées « question ouverte » : A, appel direct ; B, événement → file → worker avec retries, sur la même logique que l'épisode 35.
  - Les tâches en attente d'un mécanisme : photos orphelines, purge d'idempotence, limite des demandes de réinitialisation.
- Sources : ADR 0015:22-82, `docs/adr/README.md:115-116`, ADR 0014:48-60, ADR 0016:51-52.
- **Attendre l'ADR « message queue »** (pg-boss sur Postgres, Redis + BullMQ, ou autre) avant d'animer l'option B.

### Bloc I — CI/CD cible (à reporter)

**40. La barrière de demain : hook pre-push, puis CI** · 45 s · **absent** · Manim : moyen
- Scénario envisageable :
  - `.githooks/pre-push` lance le verifier.
  - En CI : un runner vierge, `setup --sans-docker` + postgres, puis `CI=true npm run verifier`. Le garde-fou de l'épisode 9 devient strict.
  - Couverture c8 ≥ 70 % sur `app/services`, et `main` protégée.
- Sources : plan:134-173, `server/providers/contract_provider.ts:178`.
- **Ne pas produire tant que rien n'est commité.** D'ici là, l'épisode 30 couvre le sujet.

### Saison 1 minimale recommandée (environ 20 min)

1, 2, 4, 5, 7, 9, 10, 11, 12, 16, 20, 21, 25, 26, 27, 28, 29, 30, 32. Ce sont les fondamentaux, plus tout ce que `CLAUDE.md:52-66` rend non négociable.

Bonus à forte valeur : 3, 6, 8, 13, 15, 17, 22, 23, 24, 31. Bonus secondaires : 14, 18, 19, 33.

## 4. Ce qui n'a pas besoin de Manim

| Sujet | Meilleur support | Pourquoi |
|---|---|---|
| Le bilan, fait unique, et tout le reste en projection (ADR 0011) | Slide « ce qu'on stocke / ce qu'on calcule », ou 20 s à la fin de l'épisode 1 | Aucun code, aucun lien avec le hors ligne |
| AdonisJS plutôt qu'Express (ADR 0002) | Slide / tableau | Comparatif, sans mécanisme à montrer |
| Registre des ADR, et « un ADR ne se réécrit pas » | Lien vers `docs/adr/README.md` | Index de référence |
| Règle « la doc se met à jour dans la même PR » et carte des documents | Fiche, `CLAUDE.md:70-94` | Règle de process, sans flux à montrer |
| Conventions de nommage, les cinq fichiers partagés et leurs conflits | README (déjà présent) | Aide-mémoire. La mécanique est couverte par l'épisode 32 |
| Environnement local (ports 5432 / 3333 / 3334 / 5173, deux `.env`) | Schéma draw.io | Une carte des ports se relit. 10 s dans l'épisode 4 suffisent |
| `npm run diagnostic` | Démo live ou capture | Checklist statique, déjà évoquée dans l'épisode 4 |
| Base vide, absence de seeders et factories | Une phrase dans l'épisode 4 + section 5 | Un manque à signaler, sans mécanisme à animer |
| Sécurité HTTP (shield, CORS, scrypt) | Tableau | Des réglages, sans flux |
| Variables `VITE_*`, presets ESLint/TS | Tableau du README | Référence. Les variables apparaissent déjà dans les épisodes 20 et 23 |
| Pièges du SDK lié par `file:` | FAQ du README | Dépannage ponctuel |
| Exclusions ESLint | Encart README | Une phrase suffit |
| Historique des 4 migrations | Frise statique | Bonus de 30 s au mieux |
| Deux jetons opposés (session / réinitialisation, ADR 0014) | Tableau | Seul l'effet sur la file est animé (épisode 35) |
| Pourquoi pas WatermelonDB, PowerSync ou un CRDT | Slide des alternatives | Argumentaire, pas mécanisme |
| Convention de commits | `CONTRIBUTING.md` (à créer) | Rien n'est outillé |
| Feuille de route du boilerplate (rangs 1 à 7) | Frise ou Kanban | Change souvent |
| Déploiement (Traefik, `node ace build`, Verdaccio) | Rien pour l'instant | Rien n'existe. Seul « le contrat est copié dans `build/` via metaFiles » est réel |
| Message queue (option B détaillée) | ADR, puis schéma draw.io | Animer une architecture non décidée la figerait |

## 5. Points à trancher avec l'équipe

1. **CI : abandonnée ou prévue ?** Le plan acte l'abandon le 17/10/2026. Pourtant plusieurs fichiers supposent qu'elle existe :
   - `CLAUDE.md:30` (« tout ce que la CI vérifie ») et `scripts/verifier.mjs:6` ;
   - `scripts/setup.mjs:300` ;
   - `contract_provider.ts` (« c'est ce que la CI observe ») et `contract.spec.ts` (`process.env.CI`) ;
   - plan:51 et plan:215.

   Il faut décider ce que dit l'épisode 30 (« ceci est la CI » ou « ceci en attendant »), si l'épisode 40 sera produit, et si le hook pre-push sera fait.
2. **Message queue backend** : aucune trace dans le code ni dans un ADR. Il faut un ADR avant l'épisode 39 (appel direct ou événement, et quelle technologie). Faut-il y rattacher la purge d'idempotence et les photos orphelines ?
3. **App mobile** : le bloc G anime une conception. Faut-il attendre le squelette Expo (novembre à janvier) ? Plusieurs choix ne sont pas faits : tâche de fond, détection réseau, génération d'UUIDv7. L'ADR 0006 cite WorkManager et BGTaskScheduler alors que la pile visée est Expo.
4. **Défauts de `sdk/src/custom-instance.ts`**, à corriger ou assumer avant les épisodes 21 et 35 :
   - Une `DOMException` AbortError a un `code` (20) et un `message`. Le test `if (error?.code && error?.message) throw error` la relance donc avant la branche TIMEOUT_ERROR, qui est probablement morte.
   - `signal: controller.signal` écrase le `signal` de React Query : changer de page n'annule pas le fetch.
   - Le statut HTTP est perdu dès qu'un `code` existe. La future file doit pourtant distinguer 408, 429 et 401.
   - **Il n'existe aucun runner de test dans sdk/ ni dans web/** pour vérifier tout cela : faut-il en ajouter un ?
5. **Auth côté web** : `configureSdk` est appelé sans `getToken`, et il n'y a ni écran de connexion ni routeur. Le web n'utilise que des routes publiques (lister, créer), donc les épisodes 20 et 21 fonctionnent contre le vrai serveur. En revanche, aucun écran web ne montre une route protégée.
6. **Le garde-fou ne compare pas `security` et `middleware.auth()`** : une route déclarée protégée dans le YAML peut être publique sans alerte. Faut-il l'ajouter à `comparerRoutesEtContrat`, ou se contenter de l'encart de l'épisode 9 ?
7. **Idempotence et curseur** : décidés, à porter au contrat avant le 27/11/2026. Le gabarit génère encore page/limit (incohérent avec ADR 0006 §6). `occurredAt` y est facultatif, et `supprimeLe` n'est pas exposé dans le schéma public.
8. **CLAUDE.md:19-21 est inexact** : il range `server/database/schema.ts` parmi les fichiers « non versionnés », alors que le plan (ligne 51) et le README (ligne 189) le gardent committé. C'est une correction de doc, pas une décision.
9. **Mars : qui lance `npm run feature` ?** Le contrat est censé être gelé (CODEOWNERS non créé), mais le générateur crée des squelettes de contrat. Faut-il générer toutes les tranches avant mars ?
10. **Autorisation** : la fonction unique `estReferentDe()` n'est pas encore consignée, et rien n'est outillé (pas de bouncer). C'est à décider avant F02.
11. **Chiffres périmés** à ne pas recopier : `verifier.mjs` cite « Tests 22 passed » (il y en a 29) ; le plan parle de « huit fichiers » (le générateur en crée 10).
12. **Restes du starter kit qui égarent** : `@vinejs/vine`, `@adonisjs/session` et le garde `web`, `@tuyau/core` (un second typage des routes), les alias `#events`, `#listeners`, `#mails`, `#policies` et `#abilities`, `pino-pretty`, Traefik. Faut-il les retirer, ou les signaler dans l'épisode 2 ?
13. **Spectral sans règles maison** : les conventions de l'épisode 6 ne sont vérifiées par aucun outil. Faut-il le dire à l'écran, ou écrire les règles d'abord ?
14. **Code généré absent du clone** : il faut lancer `npm run sync` avant de capturer les épisodes 7, 8 et 21. L'historique `30d6d92^` contient encore les noms anglais.
15. **Dette contractuelle (ADR 0002)** : deux livrables décrivent encore Express, et l'amendement est dû avant le 27/11/2026. Une vidéo de stack ne doit pas contredire un document validé sans le signaler.
16. **Messages d'erreur Ajv en anglais** (« must NOT have additional properties »), alors que le contrat annonce des messages en français. Ils seront visibles dans les épisodes 12 et 23.
17. **Données de dev** : sans seeders ni factories, la pagination et le curseur ne se testent pas sur des volumes réalistes (rang 6 du plan). Faut-il les livrer avant mars ?
18. **Filtre de test Japa** : vérifier si `--tests` accepte une sous-chaîne avant de montrer une commande dans l'épisode 16. Sinon, utiliser le titre complet ou `--files`.