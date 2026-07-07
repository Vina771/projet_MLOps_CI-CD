from pathlib import Path

from src.train import train


def test_train_cree_les_artifacts(tmp_path):
    score = train(Path(tmp_path))
    assert 0 <= score <= 1
    assert (tmp_path / "best_model.pkl").exists()
    assert (tmp_path / "tfidf_vectorizer.pkl").exists()
