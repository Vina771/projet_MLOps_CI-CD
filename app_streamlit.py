"""
Projet 11 - Analyse des Discours Politiques
Dashboard Streamlit - Version sans donnees CSV
Fonctionne uniquement avec best_model.pkl + tfidf_vectorizer.pkl
Auteur : Vina RAHARITSIFA - M1 I2AD - INSI
Lancement :
    streamlit run app_streamlit.py
"""

import json
import os
import re
import urllib.error
import urllib.request
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import nltk
from pathlib import Path
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Telechargement automatique du modele si absent (Streamlit Cloud)
try:
    from setup_models import download_models

    download_models()
except Exception:
    pass

for r in ["punkt", "stopwords", "wordnet", "omw-1.4", "punkt_tab"]:
    nltk.download(r, quiet=True)


# =============================================================
# CONFIG
# =============================================================

st.set_page_config(
    page_title="Projet 11 - Sentiment Analysis",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .section-title {
        font-size: 1.2rem; font-weight: bold; color: #2c3e50;
        padding: 0.4rem 0; border-bottom: 2px solid #3498db;
        margin-bottom: 1rem;
    }
    .result-box {
        padding: 1.2rem 1.5rem; border-radius: 10px;
        text-align: center; font-size: 1.4rem; font-weight: bold;
        margin: 1rem 0;
    }
    .positive { background: #d5f5e3; color: #1e8449; border: 2px solid #2ecc71; }
    .negative { background: #fadbd8; color: #922b21; border: 2px solid #e74c3c; }
    .neutral  { background: #eaecee; color: #566573; border: 2px solid #95a5a6; }
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================
# CHEMINS
# =============================================================

BASE_DIR = Path(".")
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
MODEL_PATH = MODELS_DIR / "best_model.pkl"
TFIDF_PATH = MODELS_DIR / "tfidf_vectorizer.pkl"
REPORT_CSV = REPORTS_DIR / "comparaison_modeles.csv"
REPORT_TXT = REPORTS_DIR / "rapport_modelisation.txt"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "5"))


# =============================================================
# PREPROCESSING
# =============================================================

lemmatizer = WordNetLemmatizer()
STOP_WORDS = set(stopwords.words("english")) - {
    "not",
    "no",
    "never",
    "against",
    "war",
    "peace",
    "trump",
    "biden",
    "ukraine",
    "russia",
    "nato",
    "election",
    "vote",
    "democrat",
    "republican",
}
LABEL_NAMES = ["negative", "neutral", "positive"]
COLORS = {"positive": "#2ecc71", "neutral": "#95a5a6", "negative": "#e74c3c"}


def clean_and_tokenize(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = re.sub(r"^RT\s+", "", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    tokens = word_tokenize(text)
    tokens = [
        lemmatizer.lemmatize(t) for t in tokens if t not in STOP_WORDS and len(t) > 2
    ]
    return " ".join(tokens)


@st.cache_resource(show_spinner="Chargement du modele...")
def load_model():
    if MODEL_PATH.exists() and TFIDF_PATH.exists():
        return joblib.load(MODEL_PATH), joblib.load(TFIDF_PATH)
    return None, None


def softmax(x):
    """Convertit les scores de decision_function en probabilites."""
    e = np.exp(x - np.max(x))
    return e / e.sum()


def predict(text, model, tfidf):
    tokens = clean_and_tokenize(text)
    if not tokens:
        return "neutral", 0.0, ""
    vec = tfidf.transform([tokens])
    pred = model.predict(vec)[0]
    label = LABEL_NAMES[pred]

    # LinearSVC n'a pas predict_proba — on utilise decision_function
    # et on convertit via softmax pour obtenir un score entre 0 et 1
    if hasattr(model, "predict_proba"):
        score = float(model.predict_proba(vec)[0][pred])
    elif hasattr(model, "decision_function"):
        decisions = model.decision_function(vec)[0]
        if np.ndim(decisions) == 0 or len(np.atleast_1d(decisions)) == 1:
            raw = float(np.atleast_1d(decisions)[0])
            score = float(1 / (1 + np.exp(-abs(raw))))
        else:
            proba = softmax(np.array(decisions, dtype=float))
            score = float(proba[pred])
    else:
        score = 0.0

    return label, score, tokens


def call_fastapi(path, method="GET", payload=None, timeout=API_TIMEOUT):
    url = f"{API_BASE_URL}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type or raw.strip().startswith(("{", "[")):
                return True, json.loads(raw)
            return True, raw
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        return False, str(exc)


def predict_with_fastapi(text):
    ok, data = call_fastapi("/predict", method="POST", payload={"text": text})
    if not ok:
        return None, None, None, data
    return (
        data.get("sentiment", "neutral"),
        float(data.get("score", 0.0)),
        data.get("cleaned_text", ""),
        None,
    )


def batch_predict_with_fastapi(texts):
    ok, data = call_fastapi("/predict/batch", method="POST", payload={"texts": texts})
    if not ok:
        return None, data
    return data, None


def predict_for_ui(text, model, tfidf, prefer_fastapi=True):
    if prefer_fastapi:
        label, score, tokens, error = predict_with_fastapi(text)
        if error is None:
            return label, score, tokens, "FastAPI", None

    if model is not None and tfidf is not None:
        label, score, tokens = predict(text, model, tfidf)
        return label, score, tokens, "Modele local", None

    return (
        "neutral",
        0.0,
        "",
        "Indisponible",
        "FastAPI indisponible et modele local absent.",
    )


# =============================================================
# DONNEES FIGEES DES RESULTATS D'ENTRAINEMENT
# (issues du notebook Colab - pas besoin des CSV)
# =============================================================

TRAINING_RESULTS = {
    "LinearSVC": {
        "F1 (Val)": 0.8897,
        "F1 (Test)": 0.8902,
        "Accuracy (Test)": 0.8904,
        "CV F1 Moy": 0.8835,
        "CV F1 Std": 0.0021,
        "Temps (s)": 12.3,
    },
    "Logistic Regression": {
        "F1 (Val)": 0.8814,
        "F1 (Test)": 0.8821,
        "Accuracy (Test)": 0.8824,
        "CV F1 Moy": 0.8739,
        "CV F1 Std": 0.0018,
        "Temps (s)": 28.7,
    },
    "Naive Bayes": {
        "F1 (Val)": 0.7218,
        "F1 (Test)": 0.7224,
        "Accuracy (Test)": 0.7226,
        "CV F1 Moy": 0.7214,
        "CV F1 Std": 0.0031,
        "Temps (s)": 1.2,
    },
    "Random Forest": {
        "F1 (Val)": 0.6988,
        "F1 (Test)": 0.6994,
        "Accuracy (Test)": 0.7021,
        "CV F1 Moy": 0.6962,
        "CV F1 Std": 0.0044,
        "Temps (s)": 187.4,
    },
    "Gradient Boosting": {
        "F1 (Val)": 0.6161,
        "F1 (Test)": 0.6168,
        "Accuracy (Test)": 0.6171,
        "CV F1 Moy": 0.6153,
        "CV F1 Std": 0.0052,
        "Temps (s)": 1243.6,
    },
}

DATASET_STATS = {
    "DS1 - Global Political Tweets": {
        "tweets": 238_422,
        "positive": 40.2,
        "neutral": 26.3,
        "negative": 33.5,
    },
    "DS2 - Ukraine Conflict": {
        "tweets": 767,
        "positive": 19.0,
        "neutral": 47.5,
        "negative": 33.5,
    },
    "DS3 - US Election 2020": {
        "tweets": 1_456_644,
        "positive": 33.4,
        "neutral": 38.1,
        "negative": 28.5,
    },
}

DEMO_TEXTS = {
    "Positif - Victoire electorale": "The election results show a clear and decisive victory for democracy. The people have spoken and their voices have been heard loud and clear by the government.",
    "Positif - Accord de paix": "A historic peace agreement has been signed between the two nations today. This landmark deal brings hope and prosperity to millions of people across the region.",
    "Positif - Reforme reussie": "The new economic reform policy has successfully reduced unemployment and boosted growth. Citizens are benefiting from better public services and improved living standards.",
    "Negatif - Corruption": "The government has completely failed to address corruption scandals. Officials are abusing their power and stealing public funds while citizens suffer in poverty.",
    "Negatif - Conflit arme": "The brutal military offensive has killed hundreds of innocent civilians. Russia's invasion of Ukraine must stop immediately. This war is a crime against humanity.",
    "Negatif - Fraude electorale": "The election was rigged and stolen. Massive voter fraud has been documented across multiple states. The results cannot be trusted and must be rejected.",
    "Neutre - Annonce officielle": "The parliament will vote on the proposed budget legislation next Tuesday. The bill covers infrastructure spending and taxation reform across all sectors.",
    "Neutre - Rapport statistique": "The unemployment rate remained stable at 4.2 percent according to the latest government report released this morning by the national statistics office.",
    "Neutre - Agenda diplomatique": "The president will meet foreign ministers from five countries next week to discuss trade agreements and bilateral cooperation on climate change and security.",
}


# =============================================================
# CHARGEMENT
# =============================================================

model, tfidf = load_model()
api_ok, api_health = call_fastapi("/health")


# =============================================================
# SIDEBAR
# =============================================================

with st.sidebar:
    st.title("Navigation")
    page = st.radio(
        "Section :",
        [
            "Resultats des Modeles",
            "Statistiques Dataset",
            "Analyse en Temps Reel",
            "Tester API FastAPI",
            "Textes de Demo",
            "A propos du Projet",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    use_fastapi = st.checkbox(
        "Utiliser FastAPI pour les predictions",
        value=True,
        help="Streamlit appelle /predict. Si l'API est indisponible, le modele local prend le relais.",
    )
    st.caption(f"API : {API_BASE_URL}")
    if api_ok:
        st.success("FastAPI disponible")
    else:
        st.warning("FastAPI indisponible")
    st.markdown("---")
    if model is not None:
        st.success("Modele charge")
        st.caption(f"Type : {type(model).__name__}")
        st.caption(f"Vocabulaire : {len(tfidf.vocabulary_):,} features")
    else:
        st.error("Modele non charge")
        st.caption("Placez best_model.pkl et tfidf_vectorizer.pkl dans models/")
    st.markdown("---")
    st.caption("Projet NLP - INSI")
    st.caption("LinearSVC | F1 = 0.8902")


# =============================================================
# PAGE 1 - RESULTATS DES MODELES
# =============================================================

if page == "Resultats des Modeles":

    st.title("Resultats des Modeles de Classification")
    st.markdown(
        "5 modeles entraines et compares sur 600 000 tweets (echantillon stratifie)"
    )
    st.markdown("---")

    # Charger depuis CSV si dispo, sinon utiliser les donnees figees
    if REPORT_CSV.exists():
        comp_df = pd.read_csv(REPORT_CSV, index_col=0)
    else:
        comp_df = pd.DataFrame(TRAINING_RESULTS).T

    comp_df = comp_df.sort_values("F1 (Test)", ascending=False)

    # Tableau
    st.markdown(
        '<p class="section-title">Tableau Comparatif</p>', unsafe_allow_html=True
    )
    styled = (
        comp_df[
            [
                "F1 (Val)",
                "F1 (Test)",
                "Accuracy (Test)",
                "CV F1 Moy",
                "CV F1 Std",
                "Temps (s)",
            ]
        ]
        .style.highlight_max(
            subset=["F1 (Test)", "Accuracy (Test)", "CV F1 Moy"], color="#d5f5e3"
        )
        .highlight_min(subset=["Temps (s)"], color="#d5f5e3")
        .format(
            "{:.4f}",
            subset=[
                "F1 (Val)",
                "F1 (Test)",
                "Accuracy (Test)",
                "CV F1 Moy",
                "CV F1 Std",
            ],
        )
        .format("{:.1f}", subset=["Temps (s)"])
    )
    st.dataframe(styled, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)

    # F1 Test par modele
    with col1:
        st.markdown(
            '<p class="section-title">F1 Score par modele (Test)</p>',
            unsafe_allow_html=True,
        )
        fig, ax = plt.subplots(figsize=(6, 4))
        bar_colors = [
            "#2ecc71" if v == comp_df["F1 (Test)"].max() else "#3498db"
            for v in comp_df["F1 (Test)"]
        ]
        bars = ax.bar(
            [n.replace(" ", "\n") for n in comp_df.index],
            comp_df["F1 (Test)"],
            color=bar_colors,
            edgecolor="white",
            width=0.6,
        )
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("F1 Score (weighted)")
        ax.set_title("F1 sur le jeu de test (90 000 tweets)")
        for bar, val in zip(bars, comp_df["F1 (Test)"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{val:.4f}",
                ha="center",
                fontsize=8,
                fontweight="bold",
            )
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # Cross-Validation
    with col2:
        st.markdown(
            '<p class="section-title">Cross-Validation 5-Fold</p>',
            unsafe_allow_html=True,
        )
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(
            [n.replace(" ", "\n") for n in comp_df.index],
            comp_df["CV F1 Moy"],
            yerr=comp_df["CV F1 Std"],
            color="#9b59b6",
            alpha=0.85,
            capsize=5,
            edgecolor="white",
            error_kw={"linewidth": 2},
        )
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("F1 Score (weighted)")
        ax.set_title("CV 5-Fold (mean +/- std)")
        for i, (mean, std) in enumerate(
            zip(comp_df["CV F1 Moy"], comp_df["CV F1 Std"])
        ):
            ax.text(
                i,
                mean + std + 0.02,
                f"{mean:.4f}",
                ha="center",
                fontsize=8,
                fontweight="bold",
            )
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # Val vs Test
    st.markdown("---")
    st.markdown(
        '<p class="section-title">Validation vs Test</p>', unsafe_allow_html=True
    )
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(comp_df))
    w = 0.35
    ax.bar(
        x - w / 2,
        comp_df["F1 (Val)"],
        w,
        label="Validation",
        color="#3498db",
        alpha=0.85,
    )
    ax.bar(
        x + w / 2, comp_df["F1 (Test)"], w, label="Test", color="#e74c3c", alpha=0.85
    )
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ", "\n") for n in comp_df.index], fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("F1 Score (weighted)")
    ax.set_title("Comparaison F1 Validation vs Test — pas d'overfitting")
    ax.legend()
    for i, (v, t) in enumerate(zip(comp_df["F1 (Val)"], comp_df["F1 (Test)"])):
        ax.text(i - w / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=7)
        ax.text(i + w / 2, t + 0.01, f"{t:.3f}", ha="center", fontsize=7)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Temps d'entrainement
    st.markdown("---")
    st.markdown(
        '<p class="section-title">Temps d entrainement</p>', unsafe_allow_html=True
    )
    fig, ax = plt.subplots(figsize=(10, 3))
    palette = ["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"]
    bars = ax.barh(
        [n for n in comp_df.index],
        comp_df["Temps (s)"],
        color=palette[: len(comp_df)],
        alpha=0.85,
    )
    for bar, val in zip(bars, comp_df["Temps (s)"]):
        ax.text(
            bar.get_width() + 5,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}s",
            va="center",
            fontsize=9,
        )
    ax.set_xlabel("Secondes")
    ax.set_title("Temps d'entrainement sur 420 000 tweets (train set)")
    ax.set_xlim(0, comp_df["Temps (s)"].max() * 1.2)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Rapport texte
    if REPORT_TXT.exists():
        st.markdown("---")
        with st.expander("Voir le rapport de classification complet"):
            with open(REPORT_TXT, encoding="utf-8") as f:
                st.text(f.read())


# =============================================================
# PAGE 2 - STATISTIQUES DATASET
# =============================================================

elif page == "Statistiques Dataset":

    st.title("Statistiques des Datasets")
    st.markdown("Donnees issues du pipeline de preprocessing execute sur Google Colab.")
    st.markdown("---")

    # Metriques globales
    total = sum(v["tweets"] for v in DATASET_STATS.values())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total tweets", f"{total:,}")
    col2.metric(
        "DS1 - Global", f"{DATASET_STATS['DS1 - Global Political Tweets']['tweets']:,}"
    )
    col3.metric(
        "DS2 - Ukraine", f"{DATASET_STATS['DS2 - Ukraine Conflict']['tweets']:,}"
    )
    col4.metric(
        "DS3 - Election", f"{DATASET_STATS['DS3 - US Election 2020']['tweets']:,}"
    )

    st.markdown("---")
    col_a, col_b = st.columns(2)

    # Distribution sentiment par dataset
    with col_a:
        st.markdown(
            '<p class="section-title">Sentiment par Dataset (%)</p>',
            unsafe_allow_html=True,
        )
        labels = [k.split(" - ")[0] for k in DATASET_STATS]
        pos_vals = [v["positive"] for v in DATASET_STATS.values()]
        neu_vals = [v["neutral"] for v in DATASET_STATS.values()]
        neg_vals = [v["negative"] for v in DATASET_STATS.values()]

        x = np.arange(len(labels))
        w = 0.25
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(x - w, pos_vals, w, label="Positif", color="#2ecc71", alpha=0.85)
        ax.bar(x, neu_vals, w, label="Neutre", color="#95a5a6", alpha=0.85)
        ax.bar(x + w, neg_vals, w, label="Negatif", color="#e74c3c", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 60)
        ax.set_ylabel("Pourcentage (%)")
        ax.set_title("Distribution du sentiment par dataset")
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # Taille des datasets (donut)
    with col_b:
        st.markdown(
            '<p class="section-title">Taille des Datasets</p>', unsafe_allow_html=True
        )
        sizes = [v["tweets"] for v in DATASET_STATS.values()]
        labels_donut = [
            "DS1\nGlobal\n238k",
            "DS2\nUkraine\n767",
            "DS3\nElection\n1.46M",
        ]
        colors_donut = ["#3498db", "#e67e22", "#9b59b6"]
        fig, ax = plt.subplots(figsize=(5, 4))
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels_donut,
            colors=colors_donut,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={"width": 0.55, "edgecolor": "white", "linewidth": 2},
        )
        for at in autotexts:
            at.set_fontsize(10)
            at.set_fontweight("bold")
        ax.set_title(f"Total : {total:,} tweets")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # Pipeline resume
    st.markdown("---")
    st.markdown(
        '<p class="section-title">Resume du Pipeline de Preprocessing</p>',
        unsafe_allow_html=True,
    )

    pipeline_data = {
        "Etape": [
            "Tweets bruts charges",
            "Apres suppression doublons",
            "Apres suppression retweets",
            "Apres filtrage tweets courts",
            "Total tweets nettoyes",
            "Echantillon pour entrainement",
            "Train / Val / Test",
        ],
        "Nombre": [
            "~2 100 000",
            "~1 800 000",
            "~1 750 000",
            "~1 695 833",
            "1 695 833",
            "600 000",
            "420 000 / 90 000 / 90 000",
        ],
        "Detail": [
            "DS1 + DS2 + DS3 concatenes",
            "Deduplication sur le texte brut",
            "is_retweet == False + filtre RT",
            "Minimum 3 mots apres nettoyage",
            "Donnees finales labelisees VADER",
            "Max 200 000 tweets par classe (3 classes)",
            "Split stratifie 70 / 15 / 15",
        ],
    }
    st.dataframe(pd.DataFrame(pipeline_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown(
        '<p class="section-title">Parametres du Vectoriseur TF-IDF</p>',
        unsafe_allow_html=True,
    )

    tfidf_params = {
        "Parametre": [
            "ngram_range",
            "max_features",
            "sublinear_tf",
            "min_df",
            "max_df",
        ],
        "Valeur": ["(1, 2)", "50 000", "True", "3", "0.95"],
        "Explication": [
            "Unigrammes et bigrammes (ex: 'not good' comme feature unique)",
            "Top 50 000 n-grammes par score TF-IDF",
            "log(TF) pour reduire le biais vers les mots tres frequents",
            "N-gramme present dans au moins 3 tweets",
            "N-gramme present dans au maximum 95% des tweets",
        ],
    }
    st.dataframe(pd.DataFrame(tfidf_params), use_container_width=True, hide_index=True)


# =============================================================
# PAGE 3 - ANALYSE EN TEMPS REEL
# =============================================================

elif page == "Analyse en Temps Reel":

    st.title("Analyse de Sentiment en Temps Reel")
    st.markdown("Entrez un texte politique en anglais pour obtenir sa classification.")
    st.markdown("---")

    prediction_available = (use_fastapi and api_ok) or (
        model is not None and tfidf is not None
    )

    if not prediction_available:
        st.error(
            "Prediction indisponible. Demarrez FastAPI ou placez best_model.pkl "
            "et tfidf_vectorizer.pkl dans le dossier models/."
        )
    else:
        # --- Texte unique ---
        st.markdown(
            '<p class="section-title">Analyse d un texte</p>', unsafe_allow_html=True
        )

        user_input = st.text_area(
            "Texte :",
            placeholder="Ex: The election results show a clear victory for democracy and the people...",
            height=110,
            label_visibility="collapsed",
        )

        if st.button("Analyser", type="primary", use_container_width=True):
            if user_input.strip():
                label, score, tokens, source, error = predict_for_ui(
                    user_input, model, tfidf, use_fastapi
                )
                if error:
                    st.warning(error)

                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    emoji = (
                        "POSITIF"
                        if label == "positive"
                        else "NEGATIF" if label == "negative" else "NEUTRE"
                    )
                    st.markdown(
                        f'<div class="result-box {label}">{emoji}</div>',
                        unsafe_allow_html=True,
                    )
                    if score > 0:
                        st.progress(score)
                        st.caption(f"Confiance du modele : {score:.1%}")
                    st.caption(f"Source de prediction : {source}")

                st.markdown("**Tokens extraits apres preprocessing :**")
                st.code(
                    tokens if tokens else "(texte trop court ou vide apres nettoyage)"
                )
            else:
                st.warning("Veuillez entrer un texte.")

        # --- Batch ---
        st.markdown("---")
        st.markdown(
            '<p class="section-title">Analyse de plusieurs textes</p>',
            unsafe_allow_html=True,
        )

        multi_input = st.text_area(
            "Textes (un par ligne) :",
            placeholder=(
                "The government completely failed the people.\n"
                "A new era of peace and cooperation begins today.\n"
                "The parliament will vote on the budget next week."
            ),
            height=140,
            label_visibility="collapsed",
        )

        if st.button("Analyser tous", type="secondary", use_container_width=True):
            lines = [line.strip() for line in multi_input.split("\n") if line.strip()]
            if lines:
                rows = []
                for line in lines:
                    lbl, scr, _, source, _ = predict_for_ui(
                        line, model, tfidf, use_fastapi
                    )
                    rows.append(
                        {
                            "Texte": line[:90] + ("..." if len(line) > 90 else ""),
                            "Sentiment": lbl.capitalize(),
                            "Score": round(scr, 3),
                            "Source": source,
                        }
                    )
                result_df = pd.DataFrame(rows)

                def color_sent(val):
                    if val == "Positive":
                        return "color:#1e8449;font-weight:bold"
                    if val == "Negative":
                        return "color:#922b21;font-weight:bold"
                    return "color:#566573"

                st.dataframe(
                    result_df.style.map(color_sent, subset=["Sentiment"]),
                    use_container_width=True,
                    hide_index=True,
                )

                col_g, col_t = st.columns(2)
                with col_g:
                    counts = result_df["Sentiment"].value_counts()
                    fig, ax = plt.subplots(figsize=(4, 3))
                    ax.bar(
                        counts.index,
                        counts.values,
                        color=[COLORS.get(s.lower(), "#95a5a6") for s in counts.index],
                        edgecolor="white",
                    )
                    ax.set_ylabel("Nombre")
                    ax.set_title("Repartition des sentiments")
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()
                with col_t:
                    summary = result_df["Sentiment"].value_counts()
                    total_b = len(result_df)
                    st.markdown("**Resume :**")
                    for sent, count in summary.items():
                        pct = count / total_b * 100
                        st.markdown(f"- **{sent}** : {count} texte(s) ({pct:.0f}%)")
            else:
                st.warning("Veuillez entrer au moins un texte.")


# =============================================================
# PAGE 4 - TEST API FASTAPI
# =============================================================

elif page == "Tester API FastAPI":

    st.title("Tester les Endpoints FastAPI")
    st.markdown("Interface simple pour verifier les endpoints exposes par l'API ML.")
    st.markdown("---")

    st.markdown('<p class="section-title">Statut API</p>', unsafe_allow_html=True)
    col_h, col_m = st.columns(2)
    with col_h:
        if st.button("Verifier /health", use_container_width=True):
            ok, data = call_fastapi("/health")
            if ok:
                st.success("FastAPI repond correctement.")
                st.json(data)
            else:
                st.error(data)
    with col_m:
        if st.button("Lire /metrics", use_container_width=True):
            ok, data = call_fastapi("/metrics")
            if ok:
                st.code(str(data)[:2500], language="text")
            else:
                st.error(data)

    st.markdown("---")
    st.markdown('<p class="section-title">POST /predict</p>', unsafe_allow_html=True)

    examples = {
        "Positif": "A new era of peace and cooperation begins today.",
        "Negatif": "The government completely failed the people during the crisis.",
        "Neutre": "The parliament will vote on the budget next week.",
    }
    selected_example = st.selectbox("Exemple :", list(examples.keys()))
    endpoint_text = st.text_area(
        "Texte envoye a FastAPI :",
        value=examples[selected_example],
        height=110,
    )

    if st.button("Envoyer a /predict", type="primary", use_container_width=True):
        ok, data = call_fastapi(
            "/predict", method="POST", payload={"text": endpoint_text}
        )
        if ok:
            sentiment = data.get("sentiment", "neutral")
            st.markdown(
                f'<div class="result-box {sentiment}">{sentiment.upper()}</div>',
                unsafe_allow_html=True,
            )
            st.json(data)
        else:
            st.error(data)

    st.markdown("---")
    st.markdown(
        '<p class="section-title">POST /predict/batch</p>', unsafe_allow_html=True
    )

    batch_default = "\n".join(examples.values())
    endpoint_batch = st.text_area(
        "Textes envoyes a FastAPI, un par ligne :",
        value=batch_default,
        height=140,
    )

    if st.button("Envoyer a /predict/batch", use_container_width=True):
        texts = [line.strip() for line in endpoint_batch.splitlines() if line.strip()]
        ok, data = call_fastapi(
            "/predict/batch", method="POST", payload={"texts": texts}
        )
        if ok:
            rows = [
                {
                    "Texte": item.get("text", "")[:90],
                    "Sentiment": item.get("sentiment", "").capitalize(),
                    "Score": item.get("score", 0.0),
                    "Tokens": item.get("cleaned_text", ""),
                }
                for item in data
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.json(data)
        else:
            st.error(data)


# =============================================================
# PAGE 5 - TEXTES DE DEMO
# =============================================================

elif page == "Textes de Demo":

    st.title("Textes de Demonstration")
    st.markdown(
        "Textes politiques pre-selectionnes couvrant differentes categories de sentiment. "
        "Cliquez sur un texte pour l analyser directement."
    )
    st.markdown("---")

    prediction_available = (use_fastapi and api_ok) or (
        model is not None and tfidf is not None
    )

    if not prediction_available:
        st.error(
            "Prediction indisponible. Demarrez FastAPI ou placez best_model.pkl "
            "et tfidf_vectorizer.pkl dans models/."
        )
    else:
        # Analyser tous les textes de demo d'un coup
        demo_results = {}
        for titre, texte in DEMO_TEXTS.items():
            lbl, scr, tokens, source, _ = predict_for_ui(
                texte, model, tfidf, use_fastapi
            )
            demo_results[titre] = {
                "texte": texte,
                "label": lbl,
                "score": scr,
                "tokens": tokens,
                "source": source,
            }

        # Afficher par groupe
        groups = {
            "Textes Positifs": [k for k in DEMO_TEXTS if k.startswith("Positif")],
            "Textes Negatifs": [k for k in DEMO_TEXTS if k.startswith("Negatif")],
            "Textes Neutres": [k for k in DEMO_TEXTS if k.startswith("Neutre")],
        }

        for group_name, keys in groups.items():
            st.markdown(
                f'<p class="section-title">{group_name}</p>', unsafe_allow_html=True
            )
            for key in keys:
                r = demo_results[key]
                lbl = r["label"]
                emoji = (
                    "POSITIF"
                    if lbl == "positive"
                    else "NEGATIF" if lbl == "negative" else "NEUTRE"
                )
                badge_color = {
                    "positive": "#2ecc71",
                    "negative": "#e74c3c",
                    "neutral": "#95a5a6",
                }[lbl]

                with st.expander(f"{key.split(' - ')[1]}  —  prediction : {emoji}"):
                    st.markdown("**Texte :**")
                    st.markdown(f"> {r['texte']}")
                    st.markdown("")
                    colA, colB = st.columns(2)
                    with colA:
                        st.markdown(
                            f"**Sentiment predit :** "
                            f"<span style='color:{badge_color};font-weight:bold'>{emoji}</span>",
                            unsafe_allow_html=True,
                        )
                        if r["score"] > 0:
                            st.markdown(f"**Confiance :** {r['score']:.1%}")
                    with colB:
                        st.markdown(f"**Source :** {r['source']}")
                        st.markdown(f"**Tokens :** `{r['tokens'][:80]}...`")
            st.markdown("")

        # Tableau recapitulatif
        st.markdown("---")
        st.markdown(
            '<p class="section-title">Tableau Recapitulatif</p>', unsafe_allow_html=True
        )
        recap_rows = []
        for titre, r in demo_results.items():
            recap_rows.append(
                {
                    "Titre": titre.split(" - ")[1],
                    "Attendu": titre.split(" - ")[0],
                    "Predit": r["label"].capitalize(),
                    "Correct": (
                        "Oui" if titre.split(" - ")[0].lower() in r["label"] else "Non"
                    ),
                    "Score": round(r["score"], 3),
                }
            )
        recap_df = pd.DataFrame(recap_rows)

        def color_correct(val):
            return (
                "color:#1e8449;font-weight:bold"
                if val == "Oui"
                else "color:#922b21;font-weight:bold"
            )

        def color_pred(val):
            if val == "Positive":
                return "color:#1e8449;font-weight:bold"
            if val == "Negative":
                return "color:#922b21;font-weight:bold"
            return "color:#566573"

        st.dataframe(
            recap_df.style.map(color_correct, subset=["Correct"]).map(
                color_pred, subset=["Predit"]
            ),
            use_container_width=True,
            hide_index=True,
        )

        correct = (recap_df["Correct"] == "Oui").sum()
        total_d = len(recap_df)
        st.metric(
            "Precision sur les textes de demo",
            f"{correct}/{total_d}",
            f"{correct / total_d * 100:.0f}%",
        )


# =============================================================
# PAGE 5 - A PROPOS
# =============================================================

elif page == "A propos du Projet":

    st.title("A propos du Projet 11")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-title">Contexte</p>', unsafe_allow_html=True)
        st.markdown("""
**Auteur :** Vina RAHARITSIFA

**Niveau :** M1 I2AD — INSI

**Objectif :** Analyser le sentiment des discours politiques sur Twitter
pour classer automatiquement les tweets en : Positif, Neutre, Negatif.

**Secteur :** Politique / Media

**Duree :** 2 semaines
        """)

        st.markdown(
            '<p class="section-title">Meilleur Modele</p>', unsafe_allow_html=True
        )
        st.markdown("""
| Critere | Valeur |
|---|---|
| Algorithme | LinearSVC |
| Vectorisation | TF-IDF bigrammes |
| Features | 50 000 |
| F1 Test | **0.8902** |
| Accuracy Test | **0.8904** |
| CV F1 (5-fold) | 0.8835 +/- 0.0021 |
        """)

    with col2:
        st.markdown('<p class="section-title">Datasets</p>', unsafe_allow_html=True)
        st.markdown("""
| Dataset | Tweets | Source |
|---|---|---|
| Global Political Tweets | 238 422 | Kaggle - kaushiksuresh147 |
| Ukraine Conflict | 767 | Kaggle - subhajournal |
| US Election 2020 | 1 456 644 | Kaggle - manchunhui |
| **Total** | **1 695 833** | |
        """)

        st.markdown(
            '<p class="section-title">Stack Technique</p>', unsafe_allow_html=True
        )
        st.markdown("""
| Categorie | Outils |
|---|---|
| NLP & ML | scikit-learn, NLTK, VADER |
| MLOps | MLflow (tracking + registry) |
| API | FastAPI, Uvicorn, Pydantic |
| Dashboard | Streamlit |
| Docker | docker/Dockerfile, Dockerfile.streamlit |
| Environnement | Google Colab, Google Drive |
        """)

    st.markdown("---")
    st.markdown(
        '<p class="section-title">Architecture du Pipeline</p>', unsafe_allow_html=True
    )
    st.code(
        """
Tweets bruts (3 datasets Kaggle)
    -> Nettoyage : URLs, mentions @user, hashtags, emojis, RT
    -> Tokenisation + Suppression stopwords + Lemmatisation (NLTK)
    -> Labellisation automatique VADER (positive / neutral / negative)
    -> TF-IDF bigrammes (50 000 features, sublinear_tf=True)
    -> 5 classifieurs entraines + Cross-Validation 5-fold
    -> Tracking MLflow + Model Registry (Projet11_SentimentAnalysis)
    -> Meilleur modele selectionne : LinearSVC (F1 = 0.8902)
    -> API FastAPI (/predict, /predict/batch, /health)
    -> Dashboard Streamlit (analyse en temps reel)
    -> Docker (docker/Dockerfile + Dockerfile.streamlit)
    -> Docker Hub + GitHub
    """,
        language="text",
    )