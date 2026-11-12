# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** …  ·  **Membres :** Mohammed Amine Farih, …  ·  **Date :** 12/11/2026

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
FAILED tests/test_client.py::test_client_returns_prediction - NotImplementedError: TP3 sprint 2 : MaintaiClient.predict
FAILED tests/test_client.py::test_client_wrong_key_raises_401 - NotImplementedError: TP3 sprint 2 : MaintaiClient.predict
FAILED tests/test_client.py::test_client_bad_reading_raises_422 - NotImplementedError: TP3 sprint 2 : MaintaiClient.predict
FAILED tests/test_ui.py::test_ui_shows_the_data - IndexError: list index out of range
FAILED tests/test_ui.py::test_ui_shows_the_prediction - IndexError: list index out of range
=============== 5 failed, 18 passed, 1 warning in 2.07s ===============
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

- **`tests/test_client.py`** (3 tests) : `NotImplementedError: TP3 sprint 2 : MaintaiClient.predict`. La méthode `predict()` du client Python n'est pas encore écrite.
- **`tests/test_ui.py`** (2 tests) : `IndexError: list index out of range`. Les tests lisent les indicateurs de l'interface (`at.metric[0]`, `at.metric[-1]`), mais l'application n'affiche encore aucun `st.metric` : la liste est vide.

Les 18 autres tests (API, sécurité, données, entraînement) passent, car le code des TP1 et TP2 est déjà en place.

## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'

Traceback:
File "/Users/me/AppIntel/TP/TP3/ui/app.py", line 9, in <module>
    from maintai.client import APIError, MaintaiClient
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

Avec `python -m streamlit run ui/app.py`, la page s'affiche normalement : le titre « MaintAI · prédiction de panne », la barre latérale (URL de l'API, clé API) et les onglets « Données » et « Prédiction ».

Pour exécuter `import maintai`, Python cherche un dossier `maintai` dans la liste de dossiers `sys.path`. `streamlit run ui/app.py` y ajoute le **dossier du script**, `ui/`, mais pas le dossier courant ; or le package `maintai/` se trouve à la **racine du projet**, pas dans `ui/`. `python -m streamlit ...` lance Streamlit comme un module : `python -m` ajoute le **dossier courant** (la racine du projet) à `sys.path`, et `import maintai` fonctionne. En plus, `python -m` garantit d'utiliser le Python de l'**environnement virtuel actif** : la commande `streamlit` seule avait lancé ici une autre installation (`/Library/Frameworks/Python.framework/...`).

## 3. Sprint 1 : l'onglet « Données »

Votre code de l'onglet « Données » (de `c1, c2, c3 = ...` jusqu'au nuage de points) :

```python
    # 1. Trois indicateurs côte à côte
    c1, c2, c3 = st.columns(3)
    c1.metric("Relevés", len(df))
    c2.metric("Taux de panne", f"{df.failure.mean():.1%}")
    c3.metric("Température moyenne", f"{df.temperature_c.mean():.1f} °C")

    # 2. Choix d'une variable
    variable = st.selectbox("Variable à étudier", FEATURES)

    # 3. Taux de panne par tranche de la variable choisie
    tranches = pd.cut(df[variable], bins=10)
    taux = df.groupby(tranches, observed=True)["failure"].mean()
    taux.index = [round(t.mid, 1) for t in taux.index]  # milieu de tranche : axe x numérique et trié
    st.subheader(f"Taux de panne par tranche de {variable}")
    st.bar_chart(taux, x_label=variable, y_label="taux de panne")

    # 4. Nuage de points température / vibration, coloré par panne
    st.subheader("Température et vibration")
    points = df.assign(etat=df.failure.map({0: "normal", 1: "panne"}))
    st.scatter_chart(points, x="temperature_c", y="vibration_mm_s", color="etat")
```

| Indicateur | Valeur affichée |
|---|---|
| Relevés | 5000 |
| Taux de panne | 13.6% |
| Température moyenne | 59.8 °C |

Choisissez `vibration_mm_s` dans la liste. Comment évolue le taux de panne quand la vibration augmente ?

Le taux de panne **augmente très fortement** avec la vibration. Il est presque nul pour les faibles vibrations (environ 2 % autour de 1 mm/s), puis monte rapidement (environ 30 % vers 5–6 mm/s, environ 65 % vers 8 mm/s), et atteint 100 % au-delà d'environ 12 mm/s. La vibration est la variable la plus liée à la panne. La température suit la même tendance, mais moins nettement (de presque 0 % sous 40 °C à environ 37 % au-delà de 80 °C).

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal, et qu'est-ce que cela montre sur le fonctionnement de Streamlit ?

« relance » s'affiche dans le terminal **à chaque interaction** : changement de variable dans la liste, déplacement d'un curseur… Streamlit **réexécute tout le script `app.py` de haut en bas** à chaque action de l'utilisateur. Contrairement à une page JavaScript, il n'y a pas de fonction appelée au clic : c'est le script entier qui est relancé, et la page est redessinée à partir du nouveau résultat.

À quoi sert `@st.cache_data` sur la fonction `charger` ?

Comme tout le script est relancé à chaque clic, `pd.read_csv` relirait le fichier CSV à chaque interaction. `@st.cache_data` **mémorise** le résultat de `charger(path)` : au premier appel, le fichier est lu ; aux appels suivants avec le même argument, Streamlit renvoie directement le DataFrame déjà en mémoire. L'application reste rapide même si le fichier est gros.

## 4. Sprint 2 : l'onglet « Prédiction »

Votre méthode `predict` (`maintai/client.py`) :

```python
    def predict(self, reading: dict) -> dict:
        """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        r = self.http.post("/v1/predict", json=reading, headers=headers)
        if r.status_code != 200:
            raise APIError(r.status_code, r.json().get("detail"))
        return r.json()
```

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
=============== 23 passed, 1 warning in 1.86s ===============
```

Avec l'API lancée (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Essai | Ce qu'affiche Streamlit |
|---|---|
| valeurs par défaut, bonne clé | Probabilité de panne : **95 %**, puis un bandeau rouge « ALERTE : risque de panne au-dessus du seuil de 30%. Planifiez une intervention. » |
| valeurs par défaut, fausse clé | Bandeau jaune « L'API a refusé la requête (code 401) : Clé API absente ou invalide » |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | Bandeau rouge « API injoignable à http://localhost:8000 : vérifiez qu'uvicorn est lancé. » |

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?

Parce que ce n'est **pas le navigateur** qui appelle l'API. Le navigateur parle seulement au serveur Streamlit (port 8501) ; c'est le **code Python de Streamlit, côté serveur**, qui envoie la requête à l'API avec `httpx`, via `MaintaiClient`. Le CORS est une règle appliquée **uniquement par les navigateurs** quand une page d'une origine appelle une autre origine. Un programme Python, comme `curl`, n'est pas soumis au CORS.

## 5. Questions de compréhension

1. **Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?**
   Dans la page du TP2, c'est le **navigateur** de l'utilisateur qui envoie la requête, avec `fetch` en JavaScript. C'est pour cela que le CORS s'applique et que la clé est saisie dans la page. Dans Streamlit, c'est le **serveur Streamlit**, en Python (`MaintaiClient` avec `httpx`), qui envoie la requête. Le navigateur ne fait qu'afficher la page générée par Streamlit et ne contacte jamais l'API directement.

2. **Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?**
   Parce que le test passe au client un `TestClient` de FastAPI à la place d'un vrai client HTTP (`MaintaiClient(api_key="test-key", http=client)`). Ce `TestClient` appelle l'application FastAPI **directement en mémoire**, sans réseau ni serveur. Le code de `MaintaiClient.predict` est exactement le même ; seul le « transport » change. On peut ainsi tester le client vite, de façon fiable et sans dépendre d'un serveur lancé à côté. C'est de l'injection de dépendance : le paramètre `http` du constructeur.

3. **Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un client ? Et pour l'application d'un technicien de maintenance ? Pourquoi ?**
   - **Démonstration à un client : Streamlit.** On obtient en quelques lignes de Python une interface propre avec des graphiques, des indicateurs, des curseurs et une exploration des données, sans écrire de HTML, de CSS ni de JavaScript. C'est idéal pour montrer rapidement ce que fait le modèle et itérer pendant la démo.
   - **Application d'un technicien : la page HTML/JS**, ou plus largement une vraie application web ou mobile. Elle est légère et rapide à charger, elle fonctionne sur téléphone ou tablette sur le terrain, et on contrôle totalement l'ergonomie (gros boutons, peu d'informations). Elle consomme peu de ressources serveur, alors que Streamlit relance tout le script à chaque clic et garde une session par utilisateur, ce qui supporte moins bien de nombreux utilisateurs simultanés. Streamlit reste un excellent outil de prototype et d'outil interne pour data scientists ; une interface dédiée convient mieux à un outil de production utilisé tous les jours.

## 6. Le rendu Git

- Lien de la pull request : …
- Le tag `tp3` existe sur GitHub : oui / non
- `git status` avant le commit : `.env`, `data/` ou `models/` apparaissaient-ils ? oui / non *(normalement non : ils sont dans `.gitignore`)*

## 7. Ce qui reste flou

…
