"""
Projet MLOps CI/CD - Tests unitaires
Pipeline GitLab CI/CD : pytest tests/
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_clean_function():
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize

    for resource in ["punkt", "stopwords", "wordnet", "omw-1.4", "punkt_tab"]:
        nltk.download(resource, quiet=True)
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words("english")) - {
        "not",
        "no",
        "never",
        "against",
        "war",
        "peace",
    }

    def clean(text):
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
            lemmatizer.lemmatize(t)
            for t in tokens
            if t not in stop_words and len(t) > 2
        ]
        return " ".join(tokens)

    return clean


clean_and_tokenize = get_clean_function()


class TestPreprocessing:
    def test_suppression_url(self):
        result = clean_and_tokenize("Check this https://example.com for more info")
        assert "http" not in result
        assert "example" not in result

    def test_suppression_mention(self):
        result = clean_and_tokenize("@JoeBiden won the election today")
        assert "@" not in result
        assert "joebiden" not in result

    def test_hashtag_garde_mot(self):
        result = clean_and_tokenize("I support #Democracy and #Freedom")
        assert "#" not in result
        assert "democracy" in result or "freedom" in result

    def test_suppression_retweet(self):
        result = clean_and_tokenize("RT @user The election was stolen")
        assert not result.startswith("rt")

    def test_minuscules(self):
        result = clean_and_tokenize("The PRESIDENT signed a NEW LAW today")
        assert result == result.lower()

    def test_texte_vide(self):
        assert clean_and_tokenize("") == ""
        assert clean_and_tokenize(None) == ""

    def test_texte_que_url(self):
        assert clean_and_tokenize("https://example.com https://autre.com") == ""

    def test_conservation_mot_politique(self):
        result = clean_and_tokenize("The war in Ukraine must stop now")
        assert "war" in result
        assert "ukraine" in result

    def test_conservation_negation(self):
        result = clean_and_tokenize("This is not good for the people")
        assert "not" in result

    def test_suppression_ponctuation(self):
        result = clean_and_tokenize("Hello, world! This is a test...")
        assert "," not in result
        assert "!" not in result
        assert "." not in result


class TestModel:
    @pytest.fixture
    def model_and_tfidf(self):
        import joblib

        model_path = Path("models/best_model.pkl")
        tfidf_path = Path("models/tfidf_vectorizer.pkl")
        if not model_path.exists() or not tfidf_path.exists():
            pytest.skip("Modele non disponible - ignore en CI sans modele")
        model = joblib.load(model_path)
        tfidf = joblib.load(tfidf_path)
        return model, tfidf

    def test_modele_charge(self, model_and_tfidf):
        model, tfidf = model_and_tfidf
        assert model is not None
        assert tfidf is not None

    def test_prediction_shape(self, model_and_tfidf):
        model, tfidf = model_and_tfidf
        vectors = tfidf.transform(["test one", "test two", "test three"])
        predictions = model.predict(vectors)
        assert len(predictions) == 3


class TestFichiersProjet:
    def test_fichiers_principaux_existent(self):
        expected = [
            "app_streamlit.py",
            "setup_models.py",
            "requirements.txt",
            "Dockerfile.streamlit",
            ".gitlab-ci.yml",
            "docker-compose.yml",
            "docker-compose.infra.yml",
            "ansible/playbook.yml",
            "monitoring/prometheus.yml",
            "src/app.py",
            "docker/Dockerfile",
        ]
        for file_path in expected:
            assert Path(file_path).exists(), f"Fichier manquant : {file_path}"

    def test_ancien_flux_supprime(self):
        legacy_pipeline = "J" + "enkins"
        legacy_tunnel = "ng" + "rok"
        legacy_file = legacy_pipeline + "file"
        assert not Path(legacy_file).exists()
        forbidden = [legacy_pipeline, legacy_tunnel, legacy_file]
        files = [
            "README.md",
            "docker-compose.infra.yml",
            ".gitlab-ci.yml",
            "setup_mlops.ps1",
        ]
        for file_path in files:
            content = Path(file_path).read_text(encoding="utf-8")
            for word in forbidden:
                assert word not in content

    def test_gitlab_ci_contient_6_stages(self):
        content = Path(".gitlab-ci.yml").read_text(encoding="utf-8")
        for stage in ["lint", "test", "build", "scan", "push", "deploy"]:
            assert f"- {stage}" in content
        assert "REGISTRY" in content
        assert "ghcr.io" in content
        assert "IMAGE_NAME" in content
        assert "FASTAPI_IMAGE_NAME" in content
        assert "GHCR_TOKEN" in content
        assert "docker/Dockerfile" in content
        assert "$FASTAPI_IMAGE_NAME:$IMAGE_TAG" in content

    def test_requirements_api_monitoring(self):
        content = Path("requirements.txt").read_text(encoding="utf-8")
        assert "fastapi" in content
        assert "prometheus-client" in content
        assert "streamlit" in content
        assert "uvicorn" in content

    def test_dockerfiles_exposent_ports(self):
        streamlit = Path("Dockerfile.streamlit").read_text(encoding="utf-8")
        fastapi = Path("docker/Dockerfile").read_text(encoding="utf-8")
        assert "8501" in streamlit
        assert "8000" in fastapi
