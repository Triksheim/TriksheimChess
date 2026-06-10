import argparse
import json
import time
from pathlib import Path

from ai_blunder_tests import (
    StockfishAnalyzer,
    ai_move_for_position,
    score_from_ai_perspective,
    side_to_move_after,
)


TESTDATA_DIR = Path(__file__).with_name("testdata")
DEFAULT_MATCH_PATH = TESTDATA_DIR / "stockfish_1500_match.json"
DEFAULT_CASE_PATH = TESTDATA_DIR / "ai_general_positions.json"


def load_match_games(path):
    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("games", [])


def phase_for_ply(ply, total_plies):
    if ply <= 16:
        return "opening"
    if total_plies - ply <= 16:
        return "late"
    return "middlegame"


def take_spread(cases, count):
    if len(cases) <= count:
        return list(cases)

    selected = []
    used_indexes = set()
    groups = {}
    for index, case in enumerate(cases):
        groups.setdefault((case["source_game"], case["side_to_move"]), []).append((index, case))

    while len(selected) < count:
        changed = False
        for group in groups.values():
            while group and group[0][0] in used_indexes:
                group.pop(0)
            if not group:
                continue
            index, case = group.pop(0)
            used_indexes.add(index)
            selected.append(case)
            changed = True
            if len(selected) >= count:
                break
        if not changed:
            break
    return selected


def sample_cases_from_games(games, step=6, max_cases=48, include_stockfish_turns=False):
    cases = []
    for game in games:
        moves = game["moves"]
        ai_color = game["ai_color"]
        total_plies = len(moves)
        eligible_index = 0
        for ply_index in range(0, total_plies):
            side = side_to_move_after(moves[:ply_index])
            if not include_stockfish_turns and side != ai_color:
                continue
            if eligible_index % step != 0:
                eligible_index += 1
                continue
            eligible_index += 1
            phase = phase_for_ply(ply_index + 1, total_plies)
            cases.append(
                {
                    "source_game": game.get("game"),
                    "source_result": game.get("result"),
                    "source_ai_color": ai_color,
                    "phase": phase,
                    "ply": ply_index + 1,
                    "side_to_move": side,
                    "move_history": moves[:ply_index],
                    "played_move": moves[ply_index] if ply_index < total_plies else None,
                }
            )

    if len(cases) <= max_cases:
        return cases

    targets = {
        "opening": max(6, max_cases // 5),
        "late": max(8, max_cases // 4),
    }
    targets["middlegame"] = max_cases - targets["opening"] - targets["late"]
    selected = []
    for phase in ("opening", "middlegame", "late"):
        phase_cases = [case for case in cases if case["phase"] == phase]
        selected.extend(take_spread(phase_cases, targets[phase]))

    if len(selected) < max_cases:
        selected_ids = {id(case) for case in selected}
        for case in cases:
            if id(case) not in selected_ids:
                selected.append(case)
                if len(selected) >= max_cases:
                    break
    return selected[:max_cases]


def annotate_stockfish(cases, depth):
    analyzer = StockfishAnalyzer(Path(__file__).resolve().parents[1] / "Engines" / "stockfish" / "stockfish-windows-x86-64-avx2.exe", depth=depth)
    annotated = []
    try:
        for index, case in enumerate(cases, 1):
            best_move, score = analyzer.analyse(case["move_history"])
            stockfish_eval = score_from_ai_perspective(score, case["side_to_move"], case["side_to_move"])
            annotated_case = {
                **case,
                "stockfish_best": best_move,
                "stockfish_eval_for_side": stockfish_eval,
            }
            annotated.append(annotated_case)
            print(
                f"annotated {index:03d}/{len(cases)} phase={case['phase']} "
                f"ply={case['ply']} side={case['side_to_move']} sf={best_move} eval={stockfish_eval}",
                flush=True,
            )
    finally:
        analyzer.close()
    return annotated


def run_cases(cases, stockfish_depth=8, good_move_threshold=75, use_multiprocessing=True, ai_options=None):
    analyzer = StockfishAnalyzer(Path(__file__).resolve().parents[1] / "Engines" / "stockfish" / "stockfish-windows-x86-64-avx2.exe", depth=stockfish_depth)
    results = []
    try:
        for index, case in enumerate(cases, 1):
            start = time.perf_counter()
            ai_move, ai_eval, path_len, elapsed = ai_move_for_position(
                case["move_history"],
                case["side_to_move"],
                use_multiprocessing=use_multiprocessing,
                ai_options=ai_options,
            )
            _, after_score = analyzer.analyse(case["move_history"] + [ai_move])
            after_eval = score_from_ai_perspective(
                after_score,
                side_to_move_after(case["move_history"] + [ai_move]),
                case["side_to_move"],
            )
            before_eval = case.get("stockfish_eval_for_side")
            eval_loss = None
            if before_eval is not None and after_eval is not None:
                eval_loss = before_eval - after_eval
            exact = ai_move == case.get("stockfish_best")
            good = exact or (eval_loss is not None and eval_loss <= good_move_threshold)
            result = {
                **case,
                "current_ai_move": ai_move,
                "current_ai_eval": ai_eval,
                "current_ai_path_len": path_len,
                "current_ai_time": elapsed,
                "current_after_eval": after_eval,
                "current_eval_loss": eval_loss,
                "matches_stockfish": exact,
                "is_good_move": good,
                "wall_time": time.perf_counter() - start,
            }
            results.append(result)
            print(
                f"case {index:03d}/{len(cases)} {case['phase']:<10} ply={case['ply']:<3} "
                f"side={case['side_to_move']:<5} sf={case.get('stockfish_best')} ai={ai_move} "
                f"match={exact} good={good} loss={eval_loss} time={elapsed:.2f}s",
                flush=True,
            )
    finally:
        analyzer.close()
    return results


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def summarize(results):
    total = len(results)
    exact = sum(1 for result in results if result["matches_stockfish"])
    good = sum(1 for result in results if result["is_good_move"])
    avg_time = sum(result["current_ai_time"] for result in results) / total if total else 0.0
    avg_loss_values = [
        result["current_eval_loss"]
        for result in results
        if result["current_eval_loss"] is not None and abs(result["current_eval_loss"]) < 10000
    ]
    avg_loss = sum(avg_loss_values) / len(avg_loss_values) if avg_loss_values else 0.0
    print(
        f"Summary: exact={exact}/{total} good={good}/{total} "
        f"avg_ai_time={avg_time:.2f}s avg_cp_loss={avg_loss:.1f}",
        flush=True,
    )
    for phase in ("opening", "middlegame", "late"):
        phase_results = [result for result in results if result["phase"] == phase]
        if not phase_results:
            continue
        phase_good = sum(1 for result in phase_results if result["is_good_move"])
        phase_exact = sum(1 for result in phase_results if result["matches_stockfish"])
        phase_time = sum(result["current_ai_time"] for result in phase_results) / len(phase_results)
        print(
            f"  {phase}: exact={phase_exact}/{len(phase_results)} "
            f"good={phase_good}/{len(phase_results)} avg_time={phase_time:.2f}s",
            flush=True,
        )


def parse_case_indexes(text):
    indexes = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            indexes.update(range(int(start), int(end) + 1))
        else:
            indexes.add(int(part))
    return indexes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-json", type=Path, default=DEFAULT_MATCH_PATH)
    parser.add_argument("--cases-json", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--stockfish-depth", type=int, default=8)
    parser.add_argument("--good-move-threshold", type=int, default=75)
    parser.add_argument("--sample-step", type=int, default=6)
    parser.add_argument("--max-cases", type=int, default=48)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--single-process", action="store_true")
    parser.add_argument("--depth", type=int)
    parser.add_argument("--depth-inc", type=int)
    parser.add_argument("--quiescence-checks", action="store_true")
    parser.add_argument("--killer-history", action="store_true")
    parser.add_argument("--root-score-ordering", action="store_true")
    parser.add_argument("--no-root-score-ordering", action="store_true")
    parser.add_argument("--quiescence-depth", type=int)
    parser.add_argument("--soft-time-limit", type=float)
    parser.add_argument("--time-limit", type=float)
    parser.add_argument("--no-pvs", action="store_true")
    parser.add_argument("--no-opening-book", action="store_true")
    parser.add_argument("--case-indexes")
    args = parser.parse_args()

    if args.build:
        games = load_match_games(args.match_json)
        cases = sample_cases_from_games(games, step=args.sample_step, max_cases=args.max_cases)
        cases = annotate_stockfish(cases, args.stockfish_depth)
        save_json(args.cases_json, cases)
        print(f"Saved {len(cases)} general cases to {args.cases_json}", flush=True)
    else:
        with open(args.cases_json, "r", encoding="utf-8") as file:
            cases = json.load(file)

    if args.case_indexes:
        selected_indexes = parse_case_indexes(args.case_indexes)
        cases = [
            case for index, case in enumerate(cases, 1)
            if index in selected_indexes
        ]

    ai_options = {
        "quiescence_checks": args.quiescence_checks,
        "killer_history": args.killer_history,
    }
    if args.root_score_ordering:
        ai_options["root_score_ordering"] = True
    elif args.no_root_score_ordering:
        ai_options["root_score_ordering"] = False
    if args.depth is not None:
        ai_options["depth"] = args.depth
    if args.depth_inc is not None:
        ai_options["depth_inc"] = args.depth_inc
    if args.quiescence_depth is not None:
        ai_options["quiescence_depth"] = args.quiescence_depth
    if args.soft_time_limit is not None:
        ai_options["soft_time_limit"] = args.soft_time_limit
    if args.time_limit is not None:
        ai_options["time_limit"] = args.time_limit
    if args.no_pvs:
        ai_options["use_pvs"] = False
    if args.no_opening_book:
        ai_options["use_opening_book"] = False

    results = run_cases(
        cases,
        stockfish_depth=args.stockfish_depth,
        good_move_threshold=args.good_move_threshold,
        use_multiprocessing=not args.single_process,
        ai_options=ai_options,
    )
    summarize(results)
    if args.output:
        save_json(args.output, results)
        print(f"Saved results to {args.output}", flush=True)


if __name__ == "__main__":
    main()
