import argparse
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

SAMPLE_TEXTS = [
    "great victory for democracy and peace",
    "excellent public policy for citizens",
    "corrupt government destroyed the country",
    "war and violence are terrible for people",
    "the election results were announced today",
    "the president met parliament representatives",
]
SAMPLE_LABELS = [2, 2, 0, 0, 1, 1]


def train(output_dir: Path):
    x_train, x_test, y_train, y_test = train_test_split(
        SAMPLE_TEXTS,
        SAMPLE_LABELS,
        test_size=0.5,
        random_state=42,
        stratify=SAMPLE_LABELS,
    )
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=50000)
    train_vectors = vectorizer.fit_transform(x_train)
    test_vectors = vectorizer.transform(x_test)

    model = LinearSVC()
    model.fit(train_vectors, y_train)
    predictions = model.predict(test_vectors)
    score = f1_score(y_test, predictions, average="weighted")

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "best_model.pkl")
    joblib.dump(vectorizer, output_dir / "tfidf_vectorizer.pkl")
    return score


def main():
    parser = argparse.ArgumentParser(
        description="Entrainement minimal LinearSVC + TF-IDF"
    )
    parser.add_argument(
        "--output-dir",
        default="models",
        help="Dossier de sortie des fichiers pkl",
    )
    args = parser.parse_args()
    score = train(Path(args.output_dir))
    print(f"Modele entraine. F1 test minimal={score:.4f}")


if __name__ == "__main__":
    main()
