# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe :** …  ·  **Membres :** Mohammed Amine Farih, …  ·  **Date :** 12/11/2026

> Travail réalisé sur macOS : les commandes Windows du sujet ont été remplacées par leurs équivalents (`$TMPDIR` pour `%TEMP%`, `ls -l` pour `dir`, `unzip -l` pour `tar -tf`, `.venv/bin/` pour `.venv\Scripts\`).

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```
FAILED tests/test_package.py::test_installed_version_matches_the_code - importlib.metadata.PackageNotFoundError: No package metadata was found for maintai
FAILED tests/test_package.py::test_command_is_declared - AssertionError: assert 'maintai-predict' in ['uvicorn', 'watchfiles', 'fastapi', 'websockets', 'pygmentize', 'jsonschema', ...]
=============== 2 failed, 25 passed, 1 warning in 2.74s ===============
```

Quels sont les deux tests qui échouent, et pourquoi ?

Les deux tests de `tests/test_package.py` échouent :
- **`test_installed_version_matches_the_code`** : `PackageNotFoundError`. Le code de `maintai` s'importe, car pytest ajoute la racine du projet au chemin (`pythonpath = .` dans `pytest.ini`). Mais `maintai` **n'est pas installé** : pip n'a aucune métadonnée pour lui, donc `importlib.metadata.version("maintai")` ne trouve rien.
- **`test_command_is_declared`** : la commande `maintai-predict` n'apparaît pas parmi les commandes installées (`console_scripts`), car elle n'est pas encore déclarée dans `pyproject.toml` et le package n'a pas été installé.

Les 25 autres tests passent : le code fonctionne, il manque seulement l'installation du package.

## 2. Sprint 1 : `pyproject.toml` et `pip install -e .`

Vos sections `dependencies` et `[project.scripts]` :

```toml
dependencies = [
    "numpy>=2.0",
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "joblib>=1.4",
    "httpx>=0.27",
]

[project.scripts]
maintai-predict = "maintai.cli:main"
```

Pourquoi `pytest` et `fastapi` ne sont-ils pas dans `dependencies` ?

`dependencies` liste seulement ce qui est **indispensable** pour utiliser le package, c'est-à-dire ce que le code de `maintai/` importe pour charger le modèle et prédire : numpy, pandas, scikit-learn, joblib, et httpx pour `client.py`. `pytest` ne sert qu'aux **développeurs**, pour lancer les tests : il est dans le groupe optionnel `dev`. `fastapi`/`uvicorn` ne servent qu'à ceux qui veulent **servir l'API** : ils sont dans le groupe `api` (et streamlit dans `ui`). On les installe seulement si besoin, par exemple `pip install "maintai[api]"`. Ainsi, quelqu'un qui veut seulement la commande `maintai-predict` n'installe ni serveur web ni outil de test.

Sortie de `pip show maintai` (les quatre premières lignes) :

```
Name: maintai
Version: 0.2.0
Summary: Prédiction de panne de machines industrielles à partir de relevés de capteurs.
Home-page:
```

(et plus bas : `Editable project location: /Users/me/AppIntel/TP/TP4`, `Requires: httpx, joblib, numpy, pandas, scikit-learn`)

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
=============== 27 passed, 1 warning in 1.82s ===============
```

Placez-vous dans un autre dossier (`cd "$TMPDIR"`) et lancez `maintai-predict 72 6 85 15000`, puis `python -c "import maintai; print(maintai.__file__)"`. Qu'affichent ces deux commandes ? Où Python trouve-t-il le code de `maintai` ?

```
$ cd "$TMPDIR"
$ maintai-predict 72 6 85 15000
Probabilité de panne : 95 % (ALERTE)
$ python -c "import maintai; print(maintai.__file__)"
/Users/me/AppIntel/TP/TP4/maintai/__init__.py
$ which maintai-predict
/Users/me/AppIntel/TP/TP4/.venv/bin/maintai-predict
```

Même hors du dossier du projet, la commande fonctionne et `maintai` s'importe. `pip install -e .` a **enregistré le package dans l'environnement virtuel** (`site-packages`). En mode éditable, pip n'y copie pas le code : il y place un **lien vers le dossier du projet**. Python trouve donc le code directement dans `TP4/maintai/`, ce que montre `maintai.__file__`.

Modifiez le message affiché par `maintai/cli.py`, puis relancez `maintai-predict` sans réinstaller. Le changement est-il visible ? Pourquoi ?

Oui. Après avoir ajouté `[MaintAI]` devant le message, sans relancer `pip install` :

```
$ maintai-predict 72 6 85 15000
[MaintAI] Probabilité de panne : 95 % (ALERTE)
```

Le package installé en mode éditable n'est qu'un **lien** vers le code source : à chaque lancement, Python lit les fichiers de `TP4/maintai/`, donc toute modification est prise en compte immédiatement. C'est l'intérêt de `-e` pendant le développement : on n'a pas à réinstaller après chaque changement.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `ls -l dist` après `python -m build` :

```
-rw-r--r--  1 me  staff  11622 Nov 12 11:37 maintai-0.2.0-py3-none-any.whl
-rw-r--r--  1 me  staff  12431 Nov 12 11:37 maintai-0.2.0.tar.gz
```

Contenu du wheel (`unzip -l dist/maintai-0.2.0-py3-none-any.whl`). Le modèle, les tests et `ui/` y sont-ils ? Pourquoi ?

```
maintai/__init__.py
maintai/cli.py
maintai/client.py
maintai/config.py
maintai/data.py
maintai/dataset.py
maintai/predict.py
maintai/train.py
maintai/api/__init__.py
maintai/api/main.py
maintai/api/schemas.py
maintai/api/security.py
maintai-0.2.0.dist-info/METADATA
maintai-0.2.0.dist-info/WHEEL
maintai-0.2.0.dist-info/entry_points.txt
maintai-0.2.0.dist-info/top_level.txt
maintai-0.2.0.dist-info/RECORD
                                    17 files
```

**Non**, ni le modèle, ni les tests, ni `ui/` ne sont dans le wheel. Il contient uniquement le **code du package `maintai/`** et ses **métadonnées** (`dist-info` : nom, version, dépendances dans `METADATA`, commande `maintai-predict` dans `entry_points.txt`).
- `pyproject.toml` indique `include = ["maintai*"]` : seul le dossier `maintai/` entre dans le package.
- Les **tests** servent aux développeurs, pas aux utilisateurs du package.
- **`ui/`** est une application qui *utilise* le package, pas une partie de la bibliothèque.
- Le **modèle** est un artefact produit par l'entraînement : il change à chaque réentraînement, peut être lourd, et est ignoré par Git (`models/`). On le distribue séparément et on indique son emplacement avec `MAINTAI_MODELS_DIR`.

Le nom `py3-none-any` signifie : Python 3, aucun code compilé, n'importe quelle plateforme. Le même fichier s'installe sur macOS, Windows et Linux.

Dans un environnement neuf (`$TMPDIR/essai`), installez le wheel et lancez `maintai-predict` :

| Étape | Ce qui s'affiche |
|---|---|
| sans `MAINTAI_MODELS_DIR` | `Modèle introuvable : …/essai/.venv/lib/python3.14/site-packages/models/model.joblib`, puis `Entraînez-le (python -m maintai.train) ou indiquez son dossier dans MAINTAI_MODELS_DIR.` *(code de sortie 1)* |
| avec `MAINTAI_MODELS_DIR` vers vos `models` | 3 avertissements `InconsistentVersionWarning: Trying to unpickle estimator StandardScaler / LogisticRegression / Pipeline from version 1.8.0 when using version 1.9.1…`, puis `Probabilité de panne : 95 % (ALERTE)` |
| après `pip install scikit-learn==1.8.0` | `Probabilité de panne : 95 % (ALERTE)`, sans aucun avertissement |

D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json` permet de le comprendre ?

Le modèle (`model.joblib`) a été **entraîné et sauvegardé avec scikit-learn 1.8.0**, la version figée dans `requirements.txt`. Dans l'environnement neuf, pip a installé le wheel avec sa dépendance `scikit-learn>=1.5` et a donc pris **la version la plus récente disponible, la 1.9.1**. Quand joblib recharge le modèle (désérialisation *pickle*), scikit-learn détecte que les objets (`StandardScaler`, `LogisticRegression`, `Pipeline`) ont été créés par une autre version. Leur structure interne a pu changer, et les résultats pourraient être faux, d'où l'avertissement.

La ligne qui permet de le comprendre :

```json
"sklearn_version": "1.8.0"
```

Installer exactement cette version (`pip install scikit-learn==1.8.0`) fait disparaître l'avertissement. **Leçon :** les `dependencies` de `pyproject.toml` donnent des versions *minimales* pour que le package s'installe partout, mais pour **utiliser un modèle entraîné**, il faut reproduire l'environnement d'entraînement. C'est le rôle de `requirements.txt` (versions exactes), et c'est pour cela que `model_info.json` enregistre la version de scikit-learn.

## 4. Questions de compréhension

1. **Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?**
   `requirements.txt` décrit un **environnement précis et reproductible** : toutes les bibliothèques du projet (y compris fastapi, streamlit, pytest, build) avec des **versions exactes** (`==`). Il sert à recréer à l'identique l'environnement de développement et d'entraînement du modèle. Les `dependencies` de `pyproject.toml` décrivent ce dont le **package** a besoin pour fonctionner, avec des **versions minimales** (`>=`). Elles sont lues automatiquement par pip à l'installation du package et doivent rester souples, pour que maintai puisse cohabiter avec d'autres bibliothèques chez l'utilisateur. Le premier est pour l'*application*, le second pour la *bibliothèque*.

2. **Quelle différence entre `pip install -e .` et `pip install dist/maintai-0.2.0-py3-none-any.whl` ?**
   `pip install -e .` installe le package en **mode éditable** : pip crée un **lien** vers le dossier du projet, sans copier le code. Les modifications du code sont visibles immédiatement, sans réinstaller : c'est le mode du **développeur**. `pip install …whl` **copie** le code contenu dans le wheel dans `site-packages` : c'est une installation figée de la version 0.2.0, indépendante du dossier source (qui n'a même pas besoin d'exister). Modifier le code source n'a alors plus d'effet tant qu'on ne reconstruit pas et ne réinstalle pas un nouveau wheel : c'est le mode de l'**utilisateur** ou du **déploiement**.

3. **Qu'est-ce qu'un « point d'entrée » (`[project.scripts]`) ? Où pip crée-t-il le fichier `maintai-predict` ?**
   Un point d'entrée associe un **nom de commande** à une **fonction Python** : `maintai-predict = "maintai.cli:main"` signifie « la commande `maintai-predict` exécute la fonction `main` du module `maintai.cli` ». À l'installation, pip crée un petit **script exécutable** dans le dossier des exécutables de l'environnement virtuel : sur macOS/Linux, `.venv/bin/maintai-predict` (ici `/Users/me/AppIntel/TP/TP4/.venv/bin/maintai-predict`, comme le montre `which maintai-predict`). Sous Windows, c'est `.venv\Scripts\maintai-predict.exe`. Ce dossier est dans le `PATH` quand l'environnement est activé, d'où la possibilité de lancer la commande depuis n'importe où, sans `python -m`.

## 5. Le rendu Git

- Lien de la pull request : …
- Le tag `tp4` existe sur GitHub : oui / non
- `git status` avant le commit : `dist/`, `build/` ou `maintai.egg-info/` apparaissaient-ils ? oui / non *(normalement non : ils sont dans `.gitignore`)*

## 6. Ce qui reste flou

…
