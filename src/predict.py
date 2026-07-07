import argparse

from src.app import predict_sentiment


def main():
    parser = argparse.ArgumentParser(
        description="Prediction de sentiment depuis la ligne de commande"
    )
    parser.add_argument("text", help="Texte a analyser")
    args = parser.parse_args()
    result = predict_sentiment(args.text)
    print(
        f"sentiment={result.sentiment} score={result.score} cleaned='{result.cleaned_text}'"
    )


if __name__ == "__main__":
    main()
