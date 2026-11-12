"""Interface Streamlit de MaintAI : explorer les données, puis demander une prédiction à l'API.

Lancement (depuis la racine du projet) : python -m streamlit run ui/app.py
"""
import httpx
import pandas as pd
import streamlit as st

from maintai.client import APIError, MaintaiClient
from maintai.config import FEATURES, get_settings

st.set_page_config(page_title="MaintAI", page_icon="🔧")
st.title("MaintAI · prédiction de panne")


@st.cache_data
def charger(path) -> pd.DataFrame:
    # Lu une seule fois : Streamlit relance tout le script à chaque clic
    return pd.read_csv(path)


with st.sidebar:
    url = st.text_input("URL de l'API", "http://localhost:8000")
    cle = st.text_input("Clé API", type="password")

onglet_donnees, onglet_prediction = st.tabs(["Données", "Prédiction"])

# Sprint 1 : explorer les données
with onglet_donnees:
    df = charger(get_settings().data_path)

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


# Sprint 2 : demander une prédiction à l'API
with onglet_prediction:
    with st.form("releve"):
        releve = {
            "temperature_c": st.slider("Température (°C)", -40.0, 150.0, 72.0),
            "vibration_mm_s": st.slider("Vibration (mm/s)", 0.0, 50.0, 6.0),
            "load_pct": st.slider("Charge (%)", 0.0, 100.0, 85.0),
            "runtime_hours": st.number_input("Heures de fonctionnement", 0, 100_000, 15000),
        }
        envoye = st.form_submit_button("Prédire")

    if envoye:
        try:
            resultat = MaintaiClient(url, api_key=cle).predict(releve)
        except APIError as e:
            # L'API a répondu, mais a refusé (401 mauvaise clé, 422 relevé invalide, 503 modèle absent)
            st.warning(f"L'API a refusé la requête (code {e.status_code}) : {e.detail}")
        except httpx.HTTPError:
            # Pas de réponse du tout : serveur arrêté, mauvaise URL, délai dépassé
            st.error(f"API injoignable à {url} : vérifiez qu'uvicorn est lancé.")
        else:
            pct = round(resultat["failure_probability"] * 100)
            st.metric("Probabilité de panne", f"{pct} %")
            if resultat["alert"]:
                st.error(f"ALERTE : risque de panne au-dessus du seuil de {resultat['threshold']:.0%}. "
                         "Planifiez une intervention.")
            else:
                st.success(f"Fonctionnement normal : risque sous le seuil de {resultat['threshold']:.0%}.")
