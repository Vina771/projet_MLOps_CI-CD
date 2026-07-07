from fastapi.testclient import TestClient

from src import app as api


class FakeVectorizer:
    def transform(self, texts):
        return texts


class FakeModel:
    def predict(self, vector):
        text = vector[0]
        if "great" in text or "peace" in text:
            return [2]
        if "corrupt" in text or "war" in text:
            return [0]
        return [1]

    def decision_function(self, vector):
        return [[-0.2, 0.1, 1.2]]


def test_health():
    client = TestClient(api.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict(monkeypatch):
    monkeypatch.setattr(api, "model", FakeModel())
    monkeypatch.setattr(api, "tfidf", FakeVectorizer())
    client = TestClient(api.app)
    response = client.post("/predict", json={"text": "great victory for peace"})
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment"] in {"negative", "neutral", "positive"}
    assert 0 <= data["score"] <= 1


def test_metrics_endpoint():
    client = TestClient(api.app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "mlops_predict_requests_total" in response.text
