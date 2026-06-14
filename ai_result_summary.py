import json
import sys
from pathlib import Path


def summarize(path):
    with open(path, "r", encoding="utf-8") as file:
        results = json.load(file)

    total = len(results)
    exact = sum(1 for result in results if result["matches_stockfish"])
    good = sum(1 for result in results if result["is_good_move"])
    avg_time = sum(result["current_ai_time"] for result in results) / total if total else 0.0
    loss_values = [
        result["current_eval_loss"]
        for result in results
        if result["current_eval_loss"] is not None and abs(result["current_eval_loss"]) < 10000
    ]
    avg_loss = sum(loss_values) / len(loss_values) if loss_values else 0.0
    bad = [index + 1 for index, result in enumerate(results) if not result["is_good_move"]]

    print(
        f"{Path(path).name}: exact={exact}/{total} good={good}/{total} "
        f"avg_time={avg_time:.2f}s avg_cp_loss={avg_loss:.1f} bad={bad}"
    )


if __name__ == "__main__":
    for result_path in sys.argv[1:]:
        summarize(result_path)
