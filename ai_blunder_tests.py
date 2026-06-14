import argparse
import contextlib
import io
import json
import re
import subprocess
import time
from pathlib import Path

from AI import ChessAI
from board import ChessBoard
from constants import HARD_MODE, STARTING_FEN
from game import ChessGame
from stockfish_match import apply_move, legal_moves, move_to_uci, uci_to_move


STOCKFISH_PATH = Path(__file__).resolve().parents[1] / "Engines" / "stockfish" / "stockfish-windows-x86-64-avx2.exe"
JSON_DIR = Path(__file__).with_name("json")
OUTPUT_PATH = JSON_DIR / "ai_blunder_positions.json"
MATE_SCORE = 100000


RECENT_MATCH_GAMES = [
    {
        "name": "sf1600_g1_ai_white_loss",
        "ai_color": "white",
        "result": "checkmate:black",
        "moves": "e2e4 c7c5 d2d4 d8a5 b1c3 c5d4 d1d4 e7e6 d4a7 a8a7 c1f4 b8a6 f1a6 a7a6 e1c1 g8f6 a2a3 g7g5 f4e3 f8a3 e3d4 a3b2 c1d2 e6e5 d4e5 a5c3 e5c3 f6e4 d2d3 b2c3 d3e4 g5g4 g1e2 c3f6 h1e1 d7d6 e2d4 e8g8 g2g3 f6g7 f2f4 d6d5 e4d3 a6f6 d3d2 f6b6 c2c3 g7d4 c3d4 b6a6 d1c1 g8h8 h2h4 g4h3 d2d1 b7b5 d1d2 c8f5 d2d1 b5b4 d1d2 h3h2 d2d1 f5e4 d1d2 a6a2 d2e3 b4b3 g3g4 b3b2 c1c7 h2h1q e1h1 e4h1 c7b7 f8e8 e3d3 b2b1q b7b1 e8a8 b1b3 a2g2 g4g5 g2g4 b3b7 a8f8 f4f5 g4g1 g5g6 h7g6 f5g6 h1e4 d3d2 g1g6 d2c3 g6g1 c3b2 g1b1 b2c3 f8c8 b7c7 c8c7 c3d2 b1b3 d2d1 c7c2 d1e1 e4d3 e1d1 d3f5 d1e1 f7f6 e1d1 f5g6 d1e1 g6e4 e1d1 b3b1",
    },
    {
        "name": "sf1600_g3_ai_white_loss",
        "ai_color": "white",
        "result": "checkmate:black",
        "moves": "e2e4 d7d5 b1c3 e7e6 e4d5 f8b4 d1g4 b4f8 f1b5 c7c6 d5e6 c6b5 e6f7 e8f7 g4f3 g8f6 b2b4 a7a6 g1e2 f8b4 a2a3 b4c3 f3c3 d8e7 c3e3 h8e8 e3e7 f7e7 d2d4 e7d8 c1g5 c8f5 a1b1 b8d7 e1f1 f5c2 g5f6 d7f6 b1b2 c2f5 g2g3 f5d3 b2d2 d3e4 h1g1 a8c8 f2f3 e4d5 f1f2 e8f8 f3f4 f6e4 f2e1 f8e8 d2d1 d5c4 e2c1 e4g5 e1f2 g5h3 f2g2 c4e2 c1e2 h3g1 e2g1 c8c3 d1b1 c3a3 g1f3 e8e2 g2f1 e2c2 f3h4 b7b6 h4f5 c2h2 f5g7 b5b4 g7e6 d8e7 f4f5 b4b3 b1e1 e7d6 f1g1 a3a2 f5f6 h2f2 e6f4 f2f3 e1e6 d6c7 e6e7 c7d6 e7e6 d6c7 e6e7 c7c6 d4d5 c6b5 e7g7 b3b2 g1g2 f3f4 g3f4 b2b1q g2f3 b1d3 f3g4 h7h6 f6f7 a2a3 f4f5 a3a4 g4h5 d3f5 h5h6 a4h4",
    },
    {
        "name": "sf1600_g4_ai_black_loss",
        "ai_color": "black",
        "result": "checkmate:white",
        "moves": "c2c3 d7d5 d2d4 b8c6 b1d2 e7e5 d4e5 c6e5 g1f3 e5f3 e2f3 d5d4 d2e4 c8f5 e4g3 d8e7 f1e2 d4c3 e1g1 c3b2 c1b2 e7b4 f1e1 f5d3 e2d3 g8e7 d1e2 b4e1 a1e1 e8c8 b2c3 e7d5 e2b2 d5c3 b2c3 d8d3 c3d3 f8d6 e1d1 d6g3 h2g3 b7b6 d3c4 h8f8 g3g4 c7c5 g1h2 g7g6 c4d5 c5c4 d5d7 c8b8 d7e7 f8c8 h2h1 f7f6 h1h2 f6f5 d1d2 f5g4 e7e5 b8a8 e5e4 a8b8 d2d7 c8c7 e4f4 g4g3 h2h3 g3f2 f4c7 b8a8 c7c8",
    },
    {
        "name": "sf1600_g5_ai_white_loss",
        "ai_color": "white",
        "result": "adjudicated:black",
        "moves": "e2e4 e7e6 d2d4 b8c6 f1c4 c6a5 c4b5 c7c6 b5d3 d7d5 g1f3 f8e7 b1c3 h7h6 c1d2 b7b6 e4d5 c6d5 d3b5 e8f8 b2b4 e7b4 c3d5 b4d2 d1d2 d8d5 d2b4 g8e7 e1g1 a5c6 b5c6 d5c6 a1c1 a7a5 b4d2 e7g6 c2c4 c8b7 f1e1 f8g8 h2h4 c6d6 d2c3 h6h5 d4d5 a8f8 g2g3 h8h6 c3e3 e6d5 c4d5 b7a8 e3g5 a8b7 a2a4 b7a8 e1d1 g6e7 d1e1 e7g6 e1d1 g6e7 g5h6 d6h6 d5d6 h6c1 d1c1 a8f3 d6e7 f8e8 c1c3 f3g4 c3e3 f7f6 f2f3 g4c8 e3e1 g8f7 g3g4 c8e6 g4g5 f7e7 g5g6 e7f8 e1b1 e8a8 b1b6 e6c4 f3f4 c4e2 b6e6 e2g4 e6b6 f8g8 b6b1 g4f5 b1b5 f5d3 b5h5 d3c2 f4f5 c2d1 h5h7 d1g4 h4h5 a8e8 h5h6 g7h6 h7f7 g4f5 f7f6 f5g4 g1f2 e8d8 f2g3 g4c8 g3f2 d8f8 f6f8 g8f8 f2e1 f8g7 e1d1 c8e6 d1c1 g7g6 c1b1 g6g7 b1a1 g7g6 a1b1 e6f5 b1b2 f5g4 b2a2 g4c8 a2b2 c8d7 b2a3 d7e6 a3b2 h6h5 b2a1 e6g4 a1b1 g6g5 b1a2 g5f6 a2b1 f6g6",
    },
    {
        "name": "sf1600_g6_ai_black_loss",
        "ai_color": "black",
        "result": "checkmate:white",
        "moves": "e2e4 e7e5 g1f3 a7a5 f3e5 g8f6 f1c4 d7d5 e4d5 f6d5 d1e2 d5f4 c4f7 e8e7 e2e4 f4e6 d2d4 d8d4 c1g5 e7d6 e5c4 d4c4 e4c4 e6g5 c4f4 d6e7 f7d5 h7h6 f4c7 b8d7 b1a3 e7e8 a3b5 f8b4 b5c3 h8f8 e1c1 b4c3 h1e1 c3e1 d1e1 g5e6 d5e6 g7g5 e6d5 d7e5 d5c6 b7c6 e1e5 c8e6 e5e6",
    },
]


class StockfishAnalyzer:
    def __init__(self, path, depth=8, threads=1, hash_mb=64):
        self.path = str(path)
        self.depth = depth
        self.process = subprocess.Popen(
            [self.path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.send("uci")
        self.read_until("uciok")
        self.send(f"setoption name Threads value {threads}")
        self.send(f"setoption name Hash value {hash_mb}")
        self.isready()

    def send(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def read_until(self, token):
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Stockfish stopped unexpectedly")
            line = line.strip()
            if line == token or line.startswith(token + " "):
                return line

    def isready(self):
        self.send("isready")
        self.read_until("readyok")

    def analyse(self, move_history):
        if move_history:
            self.send(f"position startpos moves {' '.join(move_history)}")
        else:
            self.send("position startpos")
        self.send(f"go depth {self.depth}")

        bestmove = None
        score_cp = None
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Stockfish stopped unexpectedly")
            line = line.strip()
            if " score cp " in line or " score mate " in line:
                parsed = parse_stockfish_score(line)
                if parsed is not None:
                    score_cp = parsed
            if line.startswith("bestmove "):
                bestmove = line.split()[1]
                break

        return bestmove, score_cp

    def close(self):
        if self.process.poll() is None:
            self.send("quit")
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


def parse_stockfish_score(line):
    cp_match = re.search(r"\bscore cp (-?\d+)", line)
    if cp_match:
        return int(cp_match.group(1))
    mate_match = re.search(r"\bscore mate (-?\d+)", line)
    if mate_match:
        mate = int(mate_match.group(1))
        sign = 1 if mate > 0 else -1
        return sign * (MATE_SCORE - min(abs(mate), 99) * 100)
    return None


def side_to_move_after(move_history):
    return "white" if len(move_history) % 2 == 0 else "black"


def score_from_ai_perspective(score_cp, side_to_move, ai_color):
    if score_cp is None:
        return None
    return score_cp if side_to_move == ai_color else -score_cp


def build_position(move_history):
    board = ChessBoard()
    game = ChessGame()
    game.load_position_from_fen(board, STARTING_FEN)
    for uci in move_history:
        move = uci_to_move(uci)
        legal = legal_moves(game, board, game.turn)
        if move not in legal:
            raise ValueError(f"Illegal replay move {uci} for {game.turn}")
        apply_move(game, board, move)
    return game, board


def ai_move_for_position(move_history, ai_color, use_multiprocessing=True, ai_options=None):
    ai_options = ai_options or {}
    game, board = build_position(move_history)
    ai = ChessAI(
        ai_options.get("depth", HARD_MODE["depth"]),
        ai_options.get("depth_inc", HARD_MODE["depth_inc"]),
        ai_color,
    )
    ai.use_multiprocessing = use_multiprocessing
    ai.use_dynamic_depth = HARD_MODE.get("dynamic_depth", False)
    ai.soft_time_limit = ai_options.get("soft_time_limit", HARD_MODE.get("soft_time_limit"))
    ai.time_limit = ai_options.get("time_limit", HARD_MODE.get("time_limit"))
    ai.use_quiescence_checks = ai_options.get("quiescence_checks", ai.use_quiescence_checks)
    ai.use_killer_history = ai_options.get("killer_history", ai.use_killer_history)
    ai.use_root_score_ordering = ai_options.get("root_score_ordering", ai.use_root_score_ordering)
    ai.quiescence_depth = ai_options.get("quiescence_depth", ai.quiescence_depth)
    ai.use_pvs = ai_options.get("use_pvs", ai.use_pvs)
    ai.use_opening_book = ai_options.get("use_opening_book", ai.use_opening_book)

    start = time.perf_counter()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            move, evaluation, path = ai.generate_move(game, board)
        elapsed = time.perf_counter() - start
        return move_to_uci(move, board), evaluation, len(path or []), elapsed
    finally:
        ai.close_pool()


def candidate_ai_moves(games, lookback_ai_moves):
    candidates = []
    for game_data in games:
        ai_color = game_data["ai_color"]
        moves = game_data["moves"].split()
        ai_ply_indexes = [
            index for index in range(len(moves))
            if side_to_move_after(moves[:index]) == ai_color
        ]
        if not game_data["result"].endswith(ai_color):
            ai_ply_indexes = ai_ply_indexes[-lookback_ai_moves:]

        for index in ai_ply_indexes:
            candidates.append(
                {
                    "game": game_data["name"],
                    "result": game_data["result"],
                    "ai_color": ai_color,
                    "ply": index + 1,
                    "move_history": moves[:index],
                    "played_move": moves[index],
                }
            )
    return candidates


def extract_blunder_cases(games, depth, lookback_ai_moves, max_cases, include_same_best=False):
    analyzer = StockfishAnalyzer(STOCKFISH_PATH, depth=depth)
    cases = []
    try:
        candidates = candidate_ai_moves(games, lookback_ai_moves)
        for number, candidate in enumerate(candidates, 1):
            before_moves = candidate["move_history"]
            after_moves = before_moves + [candidate["played_move"]]
            before_best, before_score = analyzer.analyse(before_moves)
            _, after_score = analyzer.analyse(after_moves)
            before_ai_score = score_from_ai_perspective(
                before_score,
                side_to_move_after(before_moves),
                candidate["ai_color"],
            )
            after_ai_score = score_from_ai_perspective(
                after_score,
                side_to_move_after(after_moves),
                candidate["ai_color"],
            )
            drop = None
            if before_ai_score is not None and after_ai_score is not None:
                drop = before_ai_score - after_ai_score

            case = {
                **candidate,
                "stockfish_best": before_best,
                "before_eval_ai": before_ai_score,
                "after_eval_ai": after_ai_score,
                "eval_drop": drop,
            }
            cases.append(case)
            print(
                f"analysed {number:03d}/{len(candidates)} "
                f"{candidate['game']} ply={candidate['ply']} played={candidate['played_move']} "
                f"sf={before_best} drop={drop}",
                flush=True,
            )
    finally:
        analyzer.close()

    ranked = sorted(
        (
            case for case in cases
            if case["eval_drop"] is not None
            and (include_same_best or case["stockfish_best"] != case["played_move"])
        ),
        key=lambda case: case["eval_drop"],
        reverse=True,
    )
    return ranked[:max_cases]


def run_cases(cases, use_multiprocessing=True, stockfish_depth=None, good_move_threshold=75, ai_options=None):
    results = []
    analyzer = StockfishAnalyzer(STOCKFISH_PATH, depth=stockfish_depth) if stockfish_depth else None
    try:
        for index, case in enumerate(cases, 1):
            ai_move, ai_eval, path_len, elapsed = ai_move_for_position(
                case["move_history"],
                case["ai_color"],
                use_multiprocessing=use_multiprocessing,
                ai_options=ai_options,
            )
            matched = ai_move == case["stockfish_best"]
            current_after_eval = None
            current_eval_loss = None
            good_move = matched

            if analyzer is not None:
                _, current_after_score = analyzer.analyse(case["move_history"] + [ai_move])
                current_after_eval = score_from_ai_perspective(
                    current_after_score,
                    side_to_move_after(case["move_history"] + [ai_move]),
                    case["ai_color"],
                )
                if case.get("before_eval_ai") is not None and current_after_eval is not None:
                    current_eval_loss = case["before_eval_ai"] - current_after_eval
                    good_move = current_eval_loss <= good_move_threshold

            result = {
                **case,
                "current_ai_move": ai_move,
                "current_ai_eval": ai_eval,
                "current_ai_path_len": path_len,
                "current_ai_time": elapsed,
                "current_after_eval_ai": current_after_eval,
                "current_eval_loss": current_eval_loss,
                "matches_stockfish": matched,
                "is_good_move": good_move,
            }
            results.append(result)
            quality_text = f" good={good_move}"
            if current_eval_loss is not None:
                quality_text += f" loss={current_eval_loss}"
            print(
                f"case {index:02d}: {case['game']} ply={case['ply']} "
                f"drop={case['eval_drop']} sf={case['stockfish_best']} "
                f"played={case['played_move']} ai_now={ai_move} "
                f"match={matched}{quality_text} time={elapsed:.2f}s",
                flush=True,
            )
    finally:
        if analyzer is not None:
            analyzer.close()
    return results


def save_cases(cases, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(cases, file, indent=2)


def load_cases(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stockfish-depth", type=int, default=8)
    parser.add_argument("--lookback-ai-moves", type=int, default=10)
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--single-process", action="store_true")
    parser.add_argument("--depth", type=int)
    parser.add_argument("--depth-inc", type=int)
    parser.add_argument("--quiescence-checks", action="store_true")
    parser.add_argument("--killer-history", action="store_true")
    parser.add_argument("--root-score-ordering", action="store_true")
    parser.add_argument("--no-root-score-ordering", action="store_true")
    parser.add_argument("--no-opening-book", action="store_true")
    parser.add_argument(
        "--score-current-moves",
        action="store_true",
        help="Use Stockfish to score the current AI move, not just exact best-move matches.",
    )
    parser.add_argument(
        "--good-move-threshold",
        type=int,
        default=75,
        help="Centipawn loss threshold for counting a current AI move as good.",
    )
    parser.add_argument(
        "--include-same-best",
        action="store_true",
        help="Keep positions where Stockfish's best move matches the played move.",
    )
    args = parser.parse_args()

    if args.input:
        cases = load_cases(args.input)
    else:
        cases = extract_blunder_cases(
            RECENT_MATCH_GAMES,
            depth=args.stockfish_depth,
            lookback_ai_moves=args.lookback_ai_moves,
            max_cases=args.max_cases,
            include_same_best=args.include_same_best,
        )
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
    if args.no_opening_book:
        ai_options["use_opening_book"] = False

    results = run_cases(
        cases,
        use_multiprocessing=not args.single_process,
        stockfish_depth=args.stockfish_depth if args.score_current_moves else None,
        good_move_threshold=args.good_move_threshold,
        ai_options=ai_options,
    )
    save_cases(results, args.output)

    matches = sum(1 for result in results if result["matches_stockfish"])
    good_moves = sum(1 for result in results if result.get("is_good_move"))
    avg_time = sum(result["current_ai_time"] for result in results) / len(results) if results else 0.0
    print(
        f"Saved {len(results)} blunder cases to {args.output}. "
        f"Stockfish move matches: {matches}/{len(results)}. "
        f"Good moves: {good_moves}/{len(results)}. "
        f"Avg AI time: {avg_time:.2f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
