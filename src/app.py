import re
import time
from pathlib import Path
from typing import List

import joblib
import nltk
import numpy as np
from fastapi import FastAPI, HTTPException
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

try:
    from setup_models import download_models
except Exception:  # pragma: no cover
    download_models = None

for resource in ["punkt", "stopwords", "wordnet", "omw-1.4", "punkt_tab"]:
    nltk.download(resource, quiet=True)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "best_model.pkl"
TFIDF_PATH = BASE_DIR / "models" / "tfidf_vectorizer.pkl"
LABEL_NAMES = ["negative", "neutral", "positive"]

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

app = FastAPI(
    title="Projet 11 NLP Sentiment API",
    description="API FastAPI pour predire le sentiment de tweets politiques.",
    version="1.0.0",
)

REQUEST_COUNT = Counter(
    "mlops_predict_requests_total",
    "Nombre de requetes de prediction",
)
ERROR_COUNT = Counter(
    "mlops_predict_errors_total",
    "Nombre d'erreurs de prediction",
)
PREDICTION_COUNT = Counter(
    "mlops_predictions_total",
    "Predictions par classe",
    ["sentiment"],
)
PREDICTION_LATENCY = Histogram(
    "mlops_prediction_latency_seconds",
    "Latence des predictions",
)

model = None
tfidf = None


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texte politique a analyser")


class BatchPredictRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=100)


class PredictResponse(BaseModel):
    text: str
    cleaned_text: str
    sentiment: str
    score: float


def clean_and_tokenize(text: str) -> str:
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


def softmax(values):
    values = np.array(values, dtype=float)
    exp_values = np.exp(values - np.max(values))
    return exp_values / exp_values.sum()


def load_artifacts():
    global model, tfidf
    if model is not None and tfidf is not None:
        return model, tfidf
    if (not MODEL_PATH.exists() or not TFIDF_PATH.exists()) and download_models:
        download_models()
    if not MODEL_PATH.exists() or not TFIDF_PATH.exists():
        raise RuntimeError(
            "Modeles absents: placez best_model.pkl et tfidf_vectorizer.pkl "
            "dans models/."
        )
    model = joblib.load(MODEL_PATH)
    tfidf = joblib.load(TFIDF_PATH)
    return model, tfidf


def predict_sentiment(text: str) -> PredictResponse:
    loaded_model, loaded_tfidf = load_artifacts()
    cleaned = clean_and_tokenize(text)
    if not cleaned:
        return PredictResponse(
            text=text,
            cleaned_text="",
            sentiment="neutral",
            score=0.0,
        )

    vector = loaded_tfidf.transform([cleaned])
    prediction = int(loaded_model.predict(vector)[0])
    sentiment = LABEL_NAMES[prediction]

    if hasattr(loaded_model, "predict_proba"):
        score = float(loaded_model.predict_proba(vector)[0][prediction])
    elif hasattr(loaded_model, "decision_function"):
        decisions = np.atleast_1d(loaded_model.decision_function(vector)[0])
        if len(decisions) == 1:
            score = float(1 / (1 + np.exp(-abs(float(decisions[0])))))
        else:
            score = float(softmax(decisions)[prediction])
    else:
        score = 0.0

    PREDICTION_COUNT.labels(sentiment=sentiment).inc()
    return PredictResponse(
        text=text,
        cleaned_text=cleaned,
        sentiment=sentiment,
        score=round(score, 4),
    )


@app.get("/health")
def health():
    model_exists = MODEL_PATH.exists()
    tfidf_exists = TFIDF_PATH.exists()
    return {
        "status": "ok",
        "service": "fastapi",
        "version": app.version,
        "model_exists": model_exists,
        "tfidf_exists": tfidf_exists,
        "model_loaded": model is not None and tfidf is not None,
        "ready": model_exists and tfidf_exists,
    }


@app.post("/predict", response_model=PredictResponse)
def predict_endpoint(payload: PredictRequest):
    REQUEST_COUNT.inc()
    start = time.perf_counter()
    try:
        return predict_sentiment(payload.text)
    except Exception as exc:
        ERROR_COUNT.inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        PREDICTION_LATENCY.observe(time.perf_counter() - start)


@app.post("/predict/batch", response_model=List[PredictResponse])
def predict_batch_endpoint(payload: BatchPredictRequest):
    REQUEST_COUNT.inc()
    start = time.perf_counter()
    try:
        return [predict_sentiment(text) for text in payload.texts]
    except Exception as exc:
        ERROR_COUNT.inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        PREDICTION_LATENCY.observe(time.perf_counter() - start)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
