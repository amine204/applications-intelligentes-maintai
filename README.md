# Applications intelligentes · MaintAI

Travaux pratiques du module « Développement et déploiement d'applications intelligentes » (cycle ingénieur IA & Data, EMSI).

**MaintAI** prédit la panne d'une machine à partir de quatre relevés de capteurs (température, vibration, charge, heures de fonctionnement), puis expose ce modèle de plusieurs façons, un TP après l'autre.

| TP | Dossier | Contenu |
|---|---|---|
| TP1 | [`TP/TP1`](TP/TP1) | API FastAPI de prédiction, schéma Pydantic avec bornes physiques, tests pytest |
| TP2 | [`TP/TP2`](TP/TP2) | Tests « casser l'API », ruff, clé API (`X-API-Key`), page web HTML/JS, expérience CORS |
| TP3 | [`TP/TP3`](TP/TP3) | Client Python `MaintaiClient` et interface Streamlit (exploration des données, prédiction) |
| TP4 | [`TP/TP4`](TP/TP4) | Package Python installable : `pyproject.toml`, `pip install -e .`, commande `maintai-predict`, wheel |

Chaque dossier est un projet autonome avec son `README.md`, son `requirements.txt` et son `COMPTE_RENDU.md`.

```bash
cd TP/TP4
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python -m maintai.dataset && python -m maintai.train
python -m pytest
maintai-predict 72 6 85 15000
```

Auteur : Mohammed Amine Farih
