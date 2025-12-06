import argparse
import csv
import json
from pathlib import Path


def load_predictions(path: Path) -> dict[int, float]:
    predictions: dict[int, float] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "person_id" not in reader.fieldnames or "predicted_score" not in reader.fieldnames:
            raise ValueError("CSV must contain 'person_id' and 'predicted_score' columns.")

        for row in reader:
            try:
                person_id = int(row["person_id"])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Invalid person_id value: {row.get('person_id')}") from exc

            try:
                score = float(row["predicted_score"])
            except (KeyError, ValueError) as exc:
                raise ValueError(
                    f"Invalid predicted_score for person_id={person_id}: {row.get('predicted_score')}"
                ) from exc

            predictions[person_id] = score

    return predictions


def update_scores(evaluations_path: Path, predictions: dict[int, float]):
    with evaluations_path.open("r", encoding="utf-8") as f:
        evaluations = json.load(f)

    updated = 0
    missing = 0

    for item in evaluations:
        person_id = item.get("person_id")
        if person_id in predictions:
            item["score"] = predictions[person_id]
            updated += 1
        else:
            missing += 1

    return evaluations, updated, missing


def write_output(evaluations, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(evaluations, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replace the 'score' field in person_evaluations_labeled.json with model predictions "
            "from artist_success_predictions.csv."
        )
    )
    parser.add_argument(
        "--evaluations",
        default="person_evaluations_labeled.json",
        type=Path,
        help="Path to person_evaluations_labeled.json",
    )
    parser.add_argument(
        "--predictions",
        default=Path("output") / "artist_success_predictions.csv",
        type=Path,
        help="CSV file that contains person_id and predicted_score columns",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the updated JSON. Defaults to overwriting the evaluations file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluations_path: Path = args.evaluations
    predictions_path: Path = args.predictions
    output_path: Path = args.output or evaluations_path

    if not evaluations_path.exists():
        raise FileNotFoundError(f"Evaluations file not found: {evaluations_path}")
    if not predictions_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {predictions_path}")

    predictions = load_predictions(predictions_path)
    updated_evaluations, updated_count, missing_count = update_scores(evaluations_path, predictions)

    write_output(updated_evaluations, output_path)

    print(
        "Done! Updated scores for "
        f"{updated_count} entries. Missing predictions for {missing_count} entries."
    )
    if output_path != evaluations_path:
        print(f"Updated data saved to {output_path}")


if __name__ == "__main__":
    main()
