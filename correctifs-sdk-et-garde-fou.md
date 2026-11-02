# Deux correctifs à faire dans le socle

Ce document explique deux problèmes trouvés dans le code de `cmc-archi`, et comment les corriger.
Il est écrit pour quelqu'un qui découvre le projet : chaque problème part de zéro.

- **Partie 1** : `sdk/src/custom-instance.ts`, la fonction qui envoie toutes les requêtes HTTP des fronts.
- **Partie 2** : le garde-fou du serveur, qui vérifie que les routes respectent le contrat, mais oublie de vérifier l'authentification.

---

## Partie 1 — `customInstance`, le facteur du SDK

### Le contexte

Les fronts (le back-office web, et demain l'application mobile) n'écrivent jamais `fetch` eux-mêmes.
Ils appellent des fonctions générées par Orval, comme `listerUtilisateurs()`.
Toutes ces fonctions passent par **une seule** fonction : `customInstance`, dans `sdk/src/custom-instance.ts`.

Imagine `customInstance` comme **le facteur du SDK**. On lui donne une lettre (la requête), il :

1. écrit l'adresse complète sur l'enveloppe (l'URL) ;
2. ajoute le badge d'accès (le jeton `Authorization: Bearer ...`) ;
3. lance un chronomètre de 10 secondes : s'il n'a pas de réponse à temps, il abandonne ;
4. rapporte soit la réponse, soit **un rapport d'incident** au format `ApiError` : `{ code, message, details }`.

Ce rapport d'incident est très important. Toute l'application s'en sert pour savoir quoi faire :
afficher un message sous un champ de formulaire, demander à se reconnecter, et demain, pour le mobile,
décider s'il faut **réessayer plus tard** une requête partie sans réseau.

On a trouvé trois défauts dans ce facteur.

---

### Problème 1.1 — Le rapport « délai dépassé » n'est jamais écrit

#### Ce qui se passe

Quand le chronomètre de 10 secondes sonne, le code appelle `controller.abort()`.
`fetch` s'arrête alors en lançant une erreur du navigateur : une `DOMException` nommée `AbortError`.

Le code, dans son `catch`, fait ensuite deux vérifications **dans cet ordre** :

```ts
// Si c'est déjà une ApiError formatée
if (error?.code && error?.message) {
  throw error;                    // ← (A) on relance telle quelle
}

// Erreur de timeout
if (error.name === 'AbortError') {
  throw { code: 'TIMEOUT_ERROR', ... };   // ← (B) le rapport qu'on voudrait
}
```

L'idée de (A) : « si l'erreur a un `code` et un `message`, c'est qu'on l'a déjà fabriquée nous-mêmes ».
Mais la `DOMException` du navigateur **a elle aussi** un `code` (il vaut `20`) et un `message`
(« The operation was aborted »). Elle passe donc le test (A), et elle est relancée telle quelle.
On n'arrive **jamais** à (B).

#### L'analogie

C'est un videur qui laisse entrer « toute personne qui porte un badge ».
Il pense que seuls les employés ont un badge. Mais les visiteurs en ont un aussi, d'une autre couleur.
Résultat : il laisse passer des gens qu'il aurait dû diriger vers l'accueil.

#### Pourquoi c'est grave

Le front reçoit un objet `{ code: 20, message: "The operation was aborted" }` au lieu de
`{ code: 'TIMEOUT_ERROR', message: 'La requête a dépassé le délai...' }`.

- Le code `20` ne veut rien dire pour l'application.
- Le message affiché à l'utilisateur est en anglais et technique.
- Pour le mobile, c'est pire : la future file d'attente hors-ligne devra savoir qu'une requête a échoué
  **à cause du réseau** pour la réessayer plus tard. Un délai dépassé est exactement ce cas-là.
  Si la file ne le reconnaît pas, elle risque de jeter une saisie au lieu de la rejouer.

#### Comment le corriger

Il ne faut plus deviner « est-ce une de nos erreurs ? » en regardant si elle a un `code`.
Il faut **le savoir avec certitude**. La façon la plus simple : faire de `ApiError` une vraie classe,
et tester avec `instanceof`.

```ts
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status?: number,                       // voir le problème 1.3
    public details?: ValidationErrorDetail[],
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
```

Puis, dans le `catch` :

```ts
} catch (error: any) {
  clearTimeout(timeoutId);

  // 1. Nos propres erreurs : on les reconnaît à coup sûr.
  if (error instanceof ApiError) throw error;

  // 2. Une annulation : délai dépassé, ou annulation voulue (voir problème 1.2).
  if (error?.name === 'AbortError') {
    if (delaiDepasse) {
      throw new ApiError('TIMEOUT_ERROR', `La requête a dépassé le délai imparti de ${timeout}ms`);
    }
    throw error;   // annulation voulue : on laisse React Query la gérer
  }

  // 3. Tout le reste : le réseau n'a pas répondu.
  throw new ApiError('NETWORK_ERROR', error?.message || 'Impossible de joindre le serveur');
}
```

Et partout où le code faisait `throw { code, message } as ApiError`, on écrit `throw new ApiError(code, message)`.

> Le type `ApiError` est aujourd'hui une `interface` exportée. Le transformer en classe garde les
> mêmes champs : le code qui lit `erreur.code` ou `erreur.details` continue de marcher.

---

### Problème 1.2 — Changer de page n'annule pas la requête en cours

#### Ce qui se passe

React Query sait **annuler** une requête devenue inutile. Par exemple : l'utilisateur est sur la page 1
de la liste, la requête part, puis il clique tout de suite sur « page 2 ».
La réponse de la page 1 ne sert plus à rien. React Query le signale avec un `signal` d'annulation,
qu'Orval transmet à `customInstance` dans `config.signal`.

Mais `customInstance` fait ceci :

```ts
const response = await fetch(fullUrl.toString(), {
  ...restConfig,                 // contient le signal de React Query...
  headers: requestHeaders,
  signal: controller.signal,     // ...qui est écrasé ici par celui du chronomètre
});
```

La dernière ligne **remplace** le signal de React Query par celui du chronomètre.
La demande d'annulation de React Query n'arrive donc jamais jusqu'à `fetch`.

#### L'analogie

Tu commandes une pizza, puis tu rappelles pour annuler. Mais le livreur a débranché son téléphone
pour n'écouter que son minuteur de livraison. Il ne t'entend pas, et il livre quand même la pizza.

#### Pourquoi c'est grave

- Les requêtes inutiles continuent de consommer le réseau et la batterie.
  Sur un vieux téléphone en 4G faible, dans une calanque, ça compte (engagement « < 2 s en 4G » et
  « téléphones anciens »).
- Le serveur travaille pour rien.

#### Comment le corriger

Il faut que `fetch` écoute **les deux** : le chronomètre **et** React Query.
On garde un seul `AbortController`, et on le déclenche dans les deux cas.
On note aussi **qui** a déclenché, pour savoir si c'est un délai dépassé (problème 1.1).

```ts
const { timeout = 10000, params, headers = {}, signal: signalExterne, ...restConfig } = config;

const controller = new AbortController();
let delaiDepasse = false;

// Le chronomètre
const timeoutId = setTimeout(() => {
  delaiDepasse = true;
  controller.abort();
}, timeout);

// React Query (ou tout autre appelant) qui veut annuler
if (signalExterne) {
  if (signalExterne.aborted) controller.abort();
  else signalExterne.addEventListener('abort', () => controller.abort(), { once: true });
}

// ... puis fetch avec signal: controller.signal, comme avant.
```

> Pourquoi pas `AbortSignal.any([...])`, qui fait la même chose en une ligne ?
> Parce que cette fonction est récente et n'existe pas partout, en particulier sur certaines versions
> de React Native. La version ci-dessus marche partout.

---

### Problème 1.3 — Le numéro de statut HTTP est perdu

#### Ce qui se passe

Quand le serveur répond par une erreur (400, 401, 409, 429...), le code construit le rapport ainsi :

```ts
code: rawErrorPayload?.code || `HTTP_${response.status}`,
```

Si le serveur a mis un `code` dans sa réponse (par exemple `EMAIL_ALREADY_USED`), on garde ce code,
et le numéro de statut (`409`) **disparaît**. Il n'est stocké nulle part dans `ApiError`.

#### L'analogie

C'est un colis retourné avec l'étiquette « refusé par le destinataire »,
mais sans le tampon de la poste qui dit **pourquoi** : adresse inconnue, absent, refusé, abîmé.
Pour savoir s'il faut renvoyer le colis demain ou abandonner, il te faut le tampon.

#### Pourquoi c'est grave

Aujourd'hui, le web s'en sort, parce qu'il lit le `code` (`EMAIL_ALREADY_USED`).
Mais la future file d'attente du mobile (ADR 0006) doit trier les échecs par **statut** :

| Statut | Ce que la file doit faire |
|---|---|
| 5xx, 408, 429, pas de réseau | **réessayer plus tard** (1 min, 5, 15, 1 h, 6 h) |
| 401 | **mettre en pause** et demander à la personne de se reconnecter |
| autres 4xx | **abandonner** et montrer la saisie dans « saisies refusées » |

Sans le statut, ce tri est impossible. Un 429 (« trop de requêtes, réessaie plus tard ») qui porte
un `code` deviendrait indiscernable d'un 400 (« ta requête est fausse, inutile de réessayer »).

#### Comment le corriger

Ajouter un champ `status` à `ApiError` (déjà présent dans la classe du problème 1.1), et le remplir :

```ts
throw new ApiError(
  rawErrorPayload?.code || `HTTP_${response.status}`,
  rawErrorPayload?.message || response.statusText || 'Une erreur inattendue est survenue',
  response.status,                         // ← on garde le tampon de la poste
  details,
);
```

Pour `NETWORK_ERROR` et `TIMEOUT_ERROR`, on laisse `status` vide : aucune réponse n'est arrivée.

---

### Et pour éviter que ça revienne : des tests

Ces trois défauts ont survécu parce qu'**il n'y a aucun test** dans `sdk/` (son script `test` affiche
juste une erreur) ni dans `clients/web/`. Personne n'a jamais vérifié ce que rapporte le facteur
quand le chronomètre sonne.

On propose d'ajouter **Vitest** dans `sdk/`, avec quatre tests, en remplaçant `fetch` par un faux :

| Test | Ce qu'on simule | Ce qu'on attend |
|---|---|---|
| Délai dépassé | un `fetch` qui ne répond jamais, `timeout: 50` | `ApiError` avec `code: 'TIMEOUT_ERROR'` |
| Annulation | un `signal` externe qu'on annule pendant la requête | `fetch` reçoit bien l'annulation, pas de `TIMEOUT_ERROR` |
| Statut conservé | une réponse 409 avec `{ code: 'EMAIL_ALREADY_USED' }` | `code` **et** `status: 409` |
| Pas de réseau | un `fetch` qui lance un `TypeError` | `ApiError` avec `code: 'NETWORK_ERROR'` |

Puis ajouter `cd sdk && npm test` dans `npm run verifier`, pour que ce soit vérifié à chaque fois.

---

## Partie 2 — Le garde-fou oublie de vérifier l'authentification

### Le contexte

Dans ce projet, **le contrat OpenAPI fait foi**. Le serveur a un garde-fou au démarrage :
la fonction `comparerRoutesEtContrat`, dans `server/providers/contract_provider.ts`.
Elle compare les routes écrites dans `server/start/routes/*.ts` avec les opérations du contrat.
Si elles ne concordent pas, **le serveur refuse de démarrer**.
Le test `server/tests/functional/contract.spec.ts` fait la même vérification.

Aujourd'hui, elle vérifie trois choses pour chaque route :

1. la route déclare un `operationId` ;
2. cet `operationId` existe dans le contrat ;
3. le chemin et la méthode HTTP sont les mêmes que dans le contrat.

### Le problème

Elle ne vérifie **pas** une quatrième chose : **la route est-elle protégée comme le contrat le dit ?**

Dans le contrat, une opération qui demande d'être connecté porte un bloc `security`.
Par exemple, `contract/features/session/paths/moi.yaml` :

```yaml
operationId: monProfil
security:
  - bearerAuth: []
```

Côté serveur, c'est le middleware `auth()` qui fait respecter ça :

```ts
router
  .get('/moi', [controllers.Session, 'profil'])
  .use([middleware.auth(), middleware.contract({ operationId: 'monProfil' })])
```

Si un développeur **oublie** `middleware.auth()` :

```ts
router
  .get('/moi', [controllers.Session, 'profil'])
  .use(middleware.contract({ operationId: 'monProfil' }))   // auth() oublié
```

le garde-fou ne dit rien : l'operationId existe, le chemin et la méthode sont bons.
Le serveur démarre, les tests de contrat passent.

Pour `/moi`, on a de la chance : le contrôleur appelle `auth.getUserOrFail()`, qui renvoie quand même
un 401 si personne n'est connecté. Mais c'est une **deuxième ligne de défense par accident**, pas une règle.
Prends une future route `GET /brigades/{id}/materiel`, déclarée protégée dans le contrat, dont le contrôleur
n'a pas besoin de savoir **qui** appelle (il lit juste le matériel de la brigade). Si `auth()` est oublié,
rien ne lève de 401 : la route est **ouverte à tout le monde**.

### L'analogie

C'est un agent de sécurité qui vérifie, pour chaque porte d'un immeuble, qu'elle est bien sur le plan,
au bon étage, du bon côté du couloir. Mais il ne vérifie jamais si la porte marquée « accès réservé »
sur le plan a bien **une serrure**. Certaines pièces ont, par hasard, un coffre fermé à l'intérieur
(le `getUserOrFail()` du contrôleur). Les autres sont simplement ouvertes.

### Pourquoi c'est grave

- C'est une faille de sécurité silencieuse : rien ne la signale, ni au démarrage, ni dans les tests.
- C'est un oubli **facile** : une ligne dans un `.use([...])`. Pendant la semaine intensive de mars,
  à trente développeurs, il arrivera.
- Le reste du projet promet le contraire : « le contrat fait foi ». Un lecteur du contrat croit la
  route protégée.

Le front ne protège rien ici : un attaquant n'utilise pas notre application, il appelle l'API directement.

### Comment le corriger

On ajoute la quatrième vérification à `comparerRoutesEtContrat`. Trois petites étapes.

**Étape 1 — Retenir, pour chaque opération, si le contrat exige une connexion.**
Dans `server/app/services/contract_validator.ts`, ajouter un champ à `OperationCompilee` :

```ts
export interface OperationCompilee {
  // ... champs existants
  /** Le contrat exige une authentification (bloc `security` non vide). */
  exigeConnexion: boolean
}
```

et le remplir dans `#compiler`. Une opération est protégée si elle a son propre `security`,
ou à défaut si le contrat a un `security` global (il n'en a pas aujourd'hui, mais OpenAPI le permet) :

```ts
const securite = operation.security ?? securiteGlobale ?? []
exigeConnexion: securite.length > 0,
```

`#compiler` ne reçoit qu'une opération, pas le contrat entier. `securiteGlobale` est donc un nouveau
paramètre : la boucle de `charger()`, qui a le contrat sous la main, lui passe `contrat.security`.

> Attention au cas `security: []` (une liste vide) : en OpenAPI, ça veut dire « cette opération est
> publique, même si le contrat a une sécurité globale ». Le `?? ` ci-dessus le respecte : une liste vide
> n'est pas remplacée par la règle globale, et sa longueur est 0.

**Étape 2 — Regarder si la route porte `auth()`.**
Dans `comparerRoutesEtContrat`, on cherche déjà le middleware nommé `contract`. On cherche `auth`
de la même façon :

```ts
const aAuth = [...route.middleware.all()].some((m: any) => m?.name === 'auth')
```

**Étape 3 — Comparer, dans les deux sens.**

```ts
if (operation.exigeConnexion && !aAuth) {
  anomalies.push(
    `${operationId} — le contrat exige une connexion (security), ` +
      `mais la route n'a pas middleware.auth(). Elle est ouverte à tous.`
  )
}
if (!operation.exigeConnexion && aAuth) {
  anomalies.push(
    `${operationId} — la route exige une connexion (middleware.auth()), ` +
      `mais le contrat ne déclare pas de security. Le contrat ment aux clients.`
  )
}
```

Le second cas est moins dangereux, mais c'est quand même une incohérence : le SDK généré
n'enverrait pas de jeton, et le front recevrait des 401 incompréhensibles.

Comme ces messages vont dans `anomalies`, ils bloquent le démarrage du serveur **et** font échouer
le test `contract.spec.ts`, sans rien ajouter d'autre.

### Le test qui prouve la correction

Dans `server/tests/functional/contract.spec.ts`, ajouter un cas qui monte une route volontairement
fautive (sur un routeur de test) et vérifie que l'anomalie est bien signalée.
C'est la seule façon d'être sûr que le garde-fou attrape l'oubli, et pas seulement qu'il ne dit rien
quand tout va bien.

---

## Récapitulatif

| # | Où | Problème en une phrase | Correctif en une phrase |
|---|---|---|---|
| 1.1 | `sdk/src/custom-instance.ts` | L'erreur du navigateur se fait passer pour une des nôtres, donc `TIMEOUT_ERROR` n'est jamais produit | Faire de `ApiError` une classe et tester avec `instanceof` |
| 1.2 | `sdk/src/custom-instance.ts` | Le signal d'annulation de React Query est écrasé | Écouter les deux signaux avec un seul `AbortController` |
| 1.3 | `sdk/src/custom-instance.ts` | Le statut HTTP est perdu quand le serveur envoie un `code` | Ajouter `status` à `ApiError` |
| — | `sdk/` | Aucun test n'a vu ces trois défauts | Vitest + 4 tests, branchés dans `npm run verifier` |
| 2 | `server/providers/contract_provider.ts` | Une route déclarée protégée dans le contrat peut être publique sans alerte | Comparer `security` du contrat et `middleware.auth()` de la route |
