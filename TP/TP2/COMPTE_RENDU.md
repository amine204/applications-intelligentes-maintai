# Compte rendu · TP2 : tester, sécuriser et appeler l'API MaintAI

**Groupe :** …  ·  **Membres :** Mohammed Amine Farih, …  ·  **Date :** 12/11/2026

---

## 1. Activité 1 : casser son API (dans `TP/TP1`)

Vos cinq requêtes, le code que vous aviez **prévu**, puis le code **obtenu** :

| Requête | Ce qui ne va pas | Code prévu | Code obtenu |
|---|---|---|---|
| 1 | champ manquant (`load_pct` absent) | … | 422 |
| 2 | valeur absurde (`vibration_mm_s` = -5) | … | 422 |
| 3 | texte au lieu d'un nombre (`temperature_c` = "chaud") | … | 422 |
| 4 | champ en trop (`"couleur": "rouge"`) | … | 422 |
| 5 | mauvaise route (`POST /v1/predir`) | … | 404 |

Une de vos prévisions était-elle fausse ? Laquelle, et pourquoi ?

… *(à adapter selon vos prévisions)* Les deux surprises les plus fréquentes :
- **Texte au lieu d'un nombre → 422, pas 400 ni 500.** Pydantic tente de convertir `"chaud"` en `float`, échoue, et renvoie une erreur de validation propre. Le serveur ne plante pas. À noter : `"72"` entre guillemets serait accepté, car Pydantic sait le convertir en 72.0.
- **Champ en trop → 422, pas 200.** Par défaut, Pydantic ignore les champs inconnus. C'est `extra="forbid"` dans `SensorReading` qui les fait refuser, ce qui permet de détecter une faute de frappe dans un nom de champ.

FastAPI distingue donc seulement deux cas : **404** quand l'adresse n'existe pas (la requête n'atteint pas notre code), et **422** quand l'adresse existe mais que le corps ne respecte pas le contrat du schéma.

Dernière ligne de `python -m pytest` avec `tests/test_casser.py` (dans `TP/TP1`) :

```
=============== 18 passed, 1 warning in 1.30s ===============
```

À quoi sert `@pytest.mark.parametrize` ? Combien de tests pytest compte-t-il pour votre fonction, et pourquoi ?

`@pytest.mark.parametrize` permet d'écrire **une seule fonction de test** et de l'exécuter **avec plusieurs jeux de données** : ici `(route, body, expected)`. pytest compte **5 tests** pour `test_casser`, un par cas de la liste (`test_casser[champ_manquant]`, `test_casser[valeur_absurde]`, `test_casser[texte]`, `test_casser[champ_en_trop]`, `test_casser[mauvaise_route]`). Chaque cas réussit ou échoue indépendamment, et on évite de recopier cinq fois le même code. Le projet passe ainsi de 13 à 18 tests.

## 2. ruff

Sortie de `ruff check .` dans `TP/TP1` :

```
UP017 [*] Use `datetime.UTC` alias
  --> maintai/train.py:58:36
   |
58 |         "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
   |                                    ^^^^^^^^^^^^
help: Convert to `datetime.UTC` alias

Found 1 error.
[*] 1 fixable with `--fix`.
```

Quelle différence entre `ruff check .` et `python -m pytest` ? Que vérifie chacun ?

`ruff` est un **linter** : il lit le code **sans l'exécuter** et vérifie sa **forme** (style, imports inutilisés, syntaxe dépassée, erreurs probables). Ici, il signale que `timezone.utc` peut s'écrire `UTC` depuis Python 3.11. Ce n'est pas un bug, c'est une modernisation, corrigeable automatiquement avec `ruff check . --fix`. `pytest` **exécute** le code et vérifie son **comportement** : l'API renvoie-t-elle le bon code et la bonne prédiction ? Un code peut passer tous les tests et être mal écrit, ou être bien écrit et faux : les deux vérifications sont complémentaires.

## 3. Mise en place du TP2 (dans `TP/TP2`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
FAILED tests/test_security.py::test_missing_key_is_rejected - AssertionError: assert 200 == 401
FAILED tests/test_security.py::test_wrong_key_is_rejected - assert 200 == 401
=============== 2 failed, 16 passed, 1 warning in 0.82s ===============
```

Quels sont les deux tests qui échouent, et que reçoivent-ils au lieu de 401 ?

`test_missing_key_is_rejected` (requête sans clé) et `test_wrong_key_is_rejected` (requête avec une fausse clé). Ils reçoivent **200 OK** au lieu de 401 : l'API n'est pas encore protégée et répond à n'importe qui.

## 4. La clé API (sprint 1)

Votre fonction `require_api_key()` (`maintai/api/security.py`) :

```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""
    expected = get_settings().api_key
    if expected is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MAINTAI_API_KEY n'est pas configurée sur le serveur",
        )
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé API absente ou invalide")
```

Votre ligne `router = ...` dans `maintai/api/main.py` :

```python
router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
```

Après avoir écrit `security.py` seul (sans toucher au router), combien de tests échouent ? Pourquoi ?

Toujours **2 tests**, les mêmes, qui reçoivent toujours 200 au lieu de 401. La fonction `require_api_key()` existe, mais elle n'est **branchée sur aucune route** : FastAPI ne l'appelle jamais. Écrire une vérification ne suffit pas, il faut la déclarer comme dépendance des routes à protéger. C'est ce que fait `dependencies=[Depends(require_api_key)]` sur le router `/v1`.

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
=============== 18 passed, 1 warning in 1.12s ===============
```

Requêtes envoyées avec `curl` (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health`, sans clé | 200 | `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict`, relevé normal, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, fausse clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, bonne clé | 200 | `{"failure_probability":0.9553,"alert":true,"threshold":0.3,"model_version":"2026-11-12T10:36:02Z"}` |
| `POST /v1/predict`, 500 °C, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, 500 °C, bonne clé | 422 | `{"detail":[{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150","input":500,"ctx":{"le":150.0}}]}` |

500 °C sans clé et 500 °C avec la clé ne donnent pas le même code. Pourquoi ?

La dépendance `require_api_key` est exécutée **avant** la validation du corps de la requête. Sans clé, la requête est rejetée dès l'authentification (**401**) et le relevé n'est jamais examiné. Avec la bonne clé, l'authentification réussit, puis Pydantic valide le relevé et refuse 500 °C (**422**). Cet ordre est aussi plus sûr : un client non authentifié n'apprend rien sur le format attendu par l'API.

Relancez uvicorn **sans** `--env-file .env` et envoyez un relevé avec votre clé. Quel code obtenez-vous, et pourquoi ce n'est pas 401 ?

On obtient **500 Internal Server Error** (`"POST /v1/predict HTTP/1.1" 500 Internal Server Error` dans les logs). Sans `--env-file .env`, la variable `MAINTAI_API_KEY` n'est pas définie : le serveur n'a **aucune clé de référence**. `require_api_key` renvoie alors 500 (« MAINTAI_API_KEY n'est pas configurée sur le serveur »). Ce n'est pas 401, car 401 signifierait que le **client** s'est trompé de clé ; ici, la faute vient du **serveur** mal configuré. Accepter la requête serait dangereux, car l'API serait ouverte à tous.

## 5. La page web (sprint 2)

Votre code `fetch` (le contenu du `addEventListener` dans `web/index.html`) :

```javascript
document.getElementById("go").addEventListener("click", async () => {
  const reading = Object.fromEntries(FEATURES.map(f => [f, Number(document.getElementById(f).value)]));
  try {
    const resp = await fetch(`${document.getElementById("url").value}/v1/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": document.getElementById("key").value },
      body: JSON.stringify(reading),
    });
    const data = await resp.json();
    if (!resp.ok) {
      show("err", `Erreur ${resp.status} : ${JSON.stringify(data.detail)}`);
      return;
    }
    const pct = (data.failure_probability * 100).toFixed(0);
    show(data.alert ? "alert" : "ok", `Probabilité de panne : ${pct} % (${data.alert ? "ALERTE" : "normal"})`);
  } catch (e) {
    show("err", "API injoignable (serveur arrêté ou origine refusée par CORS) : " + e.message);
  }
});
```

Ce qu'affiche la page (servie sur le port 5500) :

| Essai | Ce qu'affiche la page |
|---|---|
| relevé normal, bonne clé | Probabilité de panne : 95 % (ALERTE), sur fond rouge |
| 500 °C, bonne clé | Erreur 422 : [{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150","input":500,"ctx":{"le":150}}], sur fond orange |
| relevé normal, fausse clé | Erreur 401 : "Clé API absente ou invalide", sur fond orange |

**Expérience CORS.** Servez la page sur le port 5501. Que dit la page, et que dit la console (F12) ?

La page affiche : « API injoignable (serveur arrêté ou origine refusée par CORS) : Failed to fetch ».

La console indique :
```
Access to fetch at 'http://localhost:8000/v1/predict' from origin 'http://localhost:5501' has been
blocked by CORS policy: Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
Failed to load resource: net::ERR_FAILED   :8000/v1/predict
```

Avant d'envoyer le POST, le navigateur envoie une requête **OPTIONS** (le *preflight*) pour demander à l'API si l'origine `http://localhost:5501` a le droit de l'appeler. Cette origine n'est pas dans `MAINTAI_CORS_ORIGINS` (seul le port 5500 y figure). L'API ne renvoie donc pas d'en-tête `Access-Control-Allow-Origin`, et le navigateur **bloque** la requête : le POST n'est jamais envoyé.

Pourquoi `curl` obtient-il une réponse alors que la page du port 5501 est bloquée ?

Le CORS est une règle **appliquée par le navigateur**, pas par le serveur. Il protège l'utilisateur : sans lui, un site malveillant ouvert dans un onglet pourrait appeler d'autres API en son nom. `curl` n'est pas un navigateur : il n'envoie pas de preflight et ignore ces règles. Le CORS ne protège donc **pas** l'API contre un client quelconque ; c'est la **clé API** qui assure ce rôle.

## 6. Les tests de l'activité 1 dans le TP2

Copiez `test_casser.py` dans `TP/TP2/tests`. Sans `headers=HEADERS`, combien de tests échouent, et avec quel code ? Lequel des cinq cas passe quand même, et pourquoi ?

```
FAILED tests/test_casser.py::test_casser[champ_manquant] - assert 401 == 422
FAILED tests/test_casser.py::test_casser[valeur_absurde] - assert 401 == 422
FAILED tests/test_casser.py::test_casser[texte] - assert 401 == 422
FAILED tests/test_casser.py::test_casser[champ_en_trop] - assert 401 == 422
=============== 4 failed, 19 passed, 1 warning in 0.88s ===============
```

**4 tests échouent**, tous avec **401** au lieu de 422 : sans clé, `require_api_key` refuse la requête avant que le relevé soit validé. Le cas **`mauvaise_route`** passe quand même avec 404 : `/v1/predir` ne correspond à aucune route, donc FastAPI répond 404 sans exécuter aucune dépendance. La vérification de la clé ne s'applique qu'aux routes qui existent dans le router `/v1`.

Dernière ligne de `python -m pytest` avec `headers=HEADERS` (`HEADERS = {"X-API-Key": "test-key"}`) :

```
=============== 23 passed, 1 warning in 1.02s ===============
```

## 7. Questions de compréhension

1. **Quelle différence entre 401 et 422 ? Et entre 401 et 403 ?**
   **401 Unauthorized** : le client n'est pas authentifié, sa clé est absente ou fausse ; on ne sait pas qui il est. **422 Unprocessable Content** : le client est authentifié, mais les **données** envoyées ne respectent pas le schéma (champ manquant, hors bornes…). **403 Forbidden** : le client est **identifié**, mais il n'a **pas le droit** d'accéder à cette ressource (par exemple un utilisateur normal sur une route d'administration). 401 veut dire « qui es-tu ? », 403 « je sais qui tu es, mais c'est interdit ».

2. **Pourquoi la clé n'est-elle ni dans le code ni dans Git ? Que contiennent `.env` et `.env.example`, et lequel est commité ?**
   Tout ce qui est dans Git est copié chez chaque personne qui clone le dépôt et reste dans l'historique, même après suppression. Une clé commitée est donc compromise. La clé est lue dans une **variable d'environnement**. `.env` contient les **vraies valeurs** (`MAINTAI_API_KEY=…`, `MAINTAI_CORS_ORIGINS=…`) : il reste sur la machine et est ignoré par `.gitignore`. `.env.example` contient les **mêmes variables avec des valeurs factices** (`changez-moi`) : il sert de modèle et **c'est lui qui est commité**.

3. **Pourquoi la clé voyage-t-elle dans un en-tête et pas dans l'URL ?**
   Les URL sont enregistrées un peu partout : historique du navigateur, logs du serveur et des proxys (on voit les URL dans les logs d'uvicorn), favoris, en-tête `Referer` envoyé à d'autres sites. Une clé dans l'URL fuiterait facilement. Les en-têtes ne sont pas journalisés par défaut, et l'en-tête `X-API-Key` est l'emplacement prévu pour ce type d'information.

4. **Que fait `secrets.compare_digest` de plus qu'un simple `==` ?**
   `==` s'arrête au **premier caractère différent** : comparer une clé dont le premier caractère est faux est un peu plus rapide que comparer une clé presque juste. En mesurant ces temps de réponse, un attaquant pourrait deviner la clé caractère par caractère (*timing attack*). `secrets.compare_digest` compare en **temps constant**, quel que soit l'endroit de la différence, et ne laisse donc fuiter aucune information.

5. **Qu'est-ce qu'une « origine » ? `http://localhost:5500` et `http://localhost:8000` sont-elles la même origine ?**
   Une origine est le triplet **protocole + hôte + port** (`http` + `localhost` + `5500`). Deux URL sont de même origine seulement si les trois sont identiques. `http://localhost:5500` et `http://localhost:8000` ont le même protocole et le même hôte, mais **pas le même port** : ce sont **deux origines différentes**. C'est pour cela que la page (5500) a besoin que l'API (8000) l'autorise via le CORS.

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp2` existe sur GitHub : oui / non
- `git status` avant le commit : le fichier `.env` apparaissait-il ? oui / non *(normalement non, car il est dans `.gitignore`)*
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  …

## 9. Ce qui reste flou

…
