"""Activité 1 : casser l'API. Chaque mauvaise requête doit être refusée avec le bon code."""
import pytest

HEADERS = {}
VALID = {"temperature_c": 72.5, "vibration_mm_s": 6.1, "load_pct": 85, "runtime_hours": 15000}


@pytest.mark.parametrize(
    "route, body, expected",
    [
        ("/v1/predict", {k: v for k, v in VALID.items() if k != "load_pct"}, 422),
        ("/v1/predict", {**VALID, "vibration_mm_s": -5}, 422),
        ("/v1/predict", {**VALID, "temperature_c": "chaud"}, 422),
        ("/v1/predict", {**VALID, "couleur": "rouge"}, 422),
        ("/v1/predir", VALID, 404),
    ],
    ids=["champ_manquant", "valeur_absurde", "texte", "champ_en_trop", "mauvaise_route"],
)
def test_casser(client, route, body, expected):
    r = client.post(route, json=body, headers=HEADERS)
    assert r.status_code == expected
