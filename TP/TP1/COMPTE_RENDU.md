# Compte rendu · TP1 : une API de prédiction pour MaintAI

**Groupe :** …  ·  **Membres :** Mohammed Amine Farih, …  ·  **Date :** 12/11/2026

---

## 1. Mise en place

Dernière ligne de `python -m pytest`, juste après la mise en place (rien n'est encore écrit) :

```
FAILED tests/test_api.py::test_predict_returns_probability - assert 422 == 200
FAILED tests/test_api.py::test_high_risk_reading_raises_alert - KeyError: 'alert'
FAILED tests/test_api.py::test_503_when_model_missing - assert 422 == 503
=============== 3 failed, 10 passed, 1 warning in 1.28s ===============
```

Dans `tests/test_api.py`, 4 tests sur 7 passent déjà alors que rien n'est écrit. Lesquels ? Pour les deux tests qui attendent un code 422, expliquez pourquoi ils passent « pour une mauvaise raison ».

Les 4 tests qui passent sont `test_health`, `test_out_of_range_value_is_rejected`, `test_missing_field_is_rejected` et `test_openapi_documents_predict`.

Les deux tests qui attendent 422 passent pour une mauvaise raison. `SensorReading` ne déclare encore aucun champ et sa configuration contient `extra="forbid"` : chaque champ envoyé est donc considéré comme « en trop ». L'API renvoie 422 à **toutes** les requêtes, même aux relevés valides, comme le montre `test_predict_returns_probability` (`assert 422 == 200`). Ces deux tests ne prouvent donc pas que les bornes ou les champs obligatoires sont vérifiés : ils obtiennent 422 parce que tout est refusé.

## 2. Le schéma d'entrée (`maintai/api/schemas.py`)

| Variable | Type | Minimum (`ge`) | Maximum (`le`) | Justification physique (pas le min / max des données) |
|---|---|---|---|---|
| `temperature_c` | float | -40 | 150 | Plage de fonctionnement d'un moteur industriel, du démarrage par grand froid à la surchauffe extrême. Au-delà, c'est le capteur qui est en défaut. |
| `vibration_mm_s` | float | 0 | 50 | Une vitesse de vibration ne peut pas être négative. La norme ISO 10816 classe une machine comme dangereuse dès environ 11 mm/s : 50 laisse une marge large. |
| `load_pct` | float | 0 | 100 | C'est un pourcentage de la capacité nominale. |
| `runtime_hours` | float | 0 | 100 000 | Un compteur d'heures ne peut pas être négatif. 100 000 h représentent environ 11 ans de fonctionnement continu. |

Après avoir écrit `schemas.py` seul, que donne `python -m pytest`, et quel est le message d'erreur des tests qui échouent ? Pourquoi est-ce un bon signe ?

```
FAILED tests/test_api.py::test_predict_returns_probability - NotImplementedError
FAILED tests/test_api.py::test_high_risk_reading_raises_alert - NotImplementedError
FAILED tests/test_api.py::test_503_when_model_missing - NotImplementedError
=============== 3 failed, 10 passed, 1 warning in 1.92s ===============
```

Les tests échouent toujours, mais avec `NotImplementedError` au lieu de 422. C'est bon signe : le schéma accepte désormais les relevés valides (on voit `reading = SensorReading(temperature_c=60.0, ...)` dans la trace). La requête franchit donc la validation Pydantic et atteint la fonction `predict()`, qui n'est pas encore écrite. Les tests de 422 passent maintenant pour la bonne raison : les bornes et les champs obligatoires sont réellement vérifiés.

## 3. La fonction `predict()` (`maintai/api/main.py`)

Votre code :

```python
    predictor = state.get("predictor")
    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Modèle non chargé : lancez python -m maintai.train puis redémarrez l'API",
        )
    return PredictionOut(**predictor.predict(reading.model_dump()))
```

Pourquoi répondre **503** et pas 500 quand le modèle manque ?

500 (Internal Server Error) signifie une erreur inattendue, un bug dans le code. Ici, le code fonctionne : c'est le service qui est temporairement indisponible, parce que le modèle n'a pas encore été entraîné ou chargé. 503 (Service Unavailable) dit exactement cela au client : la requête est correcte, mais le service n'est pas prêt, il faut réessayer plus tard. Le message `detail` indique en plus comment régler le problème.

Pourquoi le modèle est-il chargé **une seule fois**, au démarrage, et pas à chaque requête ?

Lire `model.joblib` sur le disque et le désérialiser prend du temps. Le faire à chaque requête ralentirait toutes les réponses et gaspillerait des ressources. Chargé une fois en mémoire au démarrage (fonction `lifespan`), le modèle est réutilisé par toutes les requêtes et répond immédiatement. En plus, un modèle absent est détecté dès le lancement, et `/health` le signale (`model_loaded: false`).

## 4. Les tests

Dernière ligne de `python -m pytest` à la fin du TP :

```
=============== 13 passed, 1 warning in 1.07s ===============
```

## 5. L'API en marche

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health` | 200 OK | `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict` avec `{"temperature_c": 72.5, "vibration_mm_s": 6.1, "load_pct": 85, "runtime_hours": 15000}` | 200 OK | `{"failure_probability":0.9553,"alert":true,"threshold":0.3,"model_version":"2026-11-12T09:59:28Z"}` |
| `POST /v1/predict` avec une température de 500 | 422 Unprocessable Content | `{"detail":[{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150","input":500,"ctx":{"le":150.0}}]}` |
| `POST /v1/predicte` (faute de frappe dans l'adresse) | 404 Not Found | `{"detail":"Not Found"}` |

Dans `/docs`, où voit-on les bornes que vous avez choisies ?

En bas de la page `/docs`, dans la section **Schemas**, en dépliant `SensorReading`. Chaque champ y affiche son type, sa description et ses bornes (`minimum` / `maximum`, par exemple `<= 150` pour `temperature_c`). On les voit aussi dans l'onglet **Schema** du corps de requête de `POST /v1/predict`, et dans le fichier `/openapi.json` que FastAPI génère à partir du schéma Pydantic.

## 6. Questions de compréhension

1. **REST et FastAPI : quelle est la différence ?**
   REST est un **style d'architecture** : des ressources identifiées par des URL, manipulées avec les verbes HTTP (GET, POST…), des réponses sans état, des codes de statut standard. FastAPI est un **framework Python** qui permet de construire une API qui suit ce style. REST, c'est la façon de faire ; FastAPI, c'est l'outil.

2. **Le schéma Pydantic sert à trois choses. Lesquelles ?**
   - **Valider** les entrées : types, champs obligatoires, bornes, refus des champs en trop. Une requête invalide reçoit un 422 avant d'atteindre le modèle.
   - **Convertir** le JSON reçu en objet Python typé (`reading.temperature_c`), puis en dictionnaire pour le modèle (`model_dump()`).
   - **Documenter** l'API : FastAPI génère automatiquement `/docs` et `/openapi.json` à partir du schéma, avec les bornes, les descriptions et l'exemple.

3. **Dans `http://localhost:8000/v1/predict`, que désignent `localhost`, `8000` et `/v1/predict` ?**
   `localhost` est la **machine** qui héberge l'API, ici notre propre ordinateur (127.0.0.1). `8000` est le **port**, la « porte » sur laquelle le serveur uvicorn écoute. `/v1/predict` est le **chemin** de la route, qui désigne la ressource ou l'action demandée.

4. **Pourquoi `/v1` dans l'adresse ?**
   C'est le **numéro de version** de l'API. Si un jour on change le contrat (nouveau champ obligatoire, format de réponse différent), on publie `/v2` sans casser les clients qui utilisent encore `/v1`. Les deux versions peuvent coexister pendant la migration.

5. **Dans la commande `uvicorn maintai.api.main:app`, que désignent `maintai.api.main` et `app` ?**
   `maintai.api.main` est le **module Python** à importer, c'est-à-dire le fichier `maintai/api/main.py`. `app` est la **variable** de ce module qui contient l'application FastAPI (`app = FastAPI(...)`). Uvicorn importe le module, récupère cet objet et le sert sur le port 8000.

## 7. Le rendu Git

- Lien de la pull request : …
- Le tag `tp1` existe sur GitHub : oui / non
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  …

## 8. Ce qui reste flou

…
