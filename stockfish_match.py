import argparse
import contextlib
import io
import json
import subprocess
import time
from pathlib import Path

from AI import ChessAI
from board import ChessBoard
from constants import HARD_MODE, STARTING_FEN
from game import ChessGame


STOCKFISH_PATH = Path(__file__).resolve().parents[1] / "Engines" / "stockfish" / "stockfish-windows-x86-64-avx2.exe"


def format_duration(seconds):
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes}m {seconds:02d}s"


def square_to_uci(square):
    return chr(ord("a") + square % 8) + str(square // 8 + 1)


def move_to_uci(move, board=None):
    uci = square_to_uci(move[0]) + square_to_uci(move[1])
    if board is not None:
        piece = board.get_piece(move[0])
        if piece is not None and piece.name == "Pawn":
            if (piece.color == "white" and move[1] >= 56) or (piece.color == "black" and move[1] <= 7):
                uci += "q"
    return uci


def uci_to_square(text):
    file_idx = ord(text[0]) - ord("a")
    rank = int(text[1]) - 1
    return rank * 8 + file_idx


def uci_to_move(text):
    return uci_to_square(text[:2]), uci_to_square(text[2:4])


def legal_moves(game, board, color):
    moves = []
    for square, _ in board.get_squares_with_piece(color):
        for move in game.get_valid_moves(board, square, color) or []:
            moves.append((square, move))
    return moves


def apply_move(game, board, move):
    game.execute_move(board, move[0], move[1])
    game.update_gamestate(board)
    game.evaluate_board(board)
    game.get_algebraic_notation(board)


def game_status(game, board):
    if legal_moves(game, board, game.turn):
        return None
    if game.king_in_check(board):
        winner = "black" if game.turn == "white" else "white"
        return f"checkmate:{winner}"
    return "stalemate"


class Stockfish:
    def __init__(self, path, elo=1320, movetime_ms=100, threads=1):
        self.path = str(path)
        self.elo = elo
        self.movetime_ms = movetime_ms
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
        self.send("setoption name Hash value 32")
        self.send("setoption name UCI_LimitStrength value true")
        self.send(f"setoption name UCI_Elo value {elo}")
        self.isready()

    def send(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def read_until(self, token):
        lines = []
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Stockfish stopped unexpectedly")
            line = line.strip()
            lines.append(line)
            if line == token or line.startswith(token + " "):
                return lines

    def isready(self):
        self.send("isready")
        self.read_until("readyok")

    def new_game(self):
        self.send("ucinewgame")
        self.isready()

    def bestmove(self, move_history):
        moves = " ".join(move_history)
        if moves:
            self.send(f"position startpos moves {moves}")
        else:
            self.send("position startpos")
        self.send(f"go movetime {self.movetime_ms}")

        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Stockfish stopped unexpectedly")
            line = line.strip()
            if line.startswith("bestmove "):
                return line.split()[1]

    def close(self):
        if self.process.poll() is None:
            self.send("quit")
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


def play_game(stockfish, ai_color, max_plies, verbose_moves=False, progress_callback=None):
    board = ChessBoard()
    game = ChessGame()
    game.load_position_from_fen(board, STARTING_FEN)

    ai = ChessAI(HARD_MODE["depth"], HARD_MODE["depth_inc"], ai_color)
    ai.use_multiprocessing = True
    ai.use_dynamic_depth = HARD_MODE.get("dynamic_depth", False)
    ai.soft_time_limit = HARD_MODE.get("soft_time_limit")
    ai.time_limit = HARD_MODE.get("time_limit")
    move_history = []
    ai_times = []
    sf_times = []
    move_times = []

    stockfish.new_game()

    try:
        for ply in range(max_plies):
            status = game_status(game, board)
            if status:
                return status, move_history, ai_times, sf_times, move_times, game, board
            if game.repetition:
                return "draw:repetition", move_history, ai_times, sf_times, move_times, game, board

            if game.turn == ai_color:
                mover = "AI"
                start = time.perf_counter()
                with contextlib.redirect_stdout(io.StringIO()):
                    ai_move, _, _ = ai.generate_move(game, board)
                elapsed = time.perf_counter() - start
                ai_times.append(elapsed)
                move = ai_move
                uci = move_to_uci(move, board)
            else:
                mover = "Stockfish"
                start = time.perf_counter()
                uci = stockfish.bestmove(move_history)
                elapsed = time.perf_counter() - start
                sf_times.append(elapsed)
                move = uci_to_move(uci)

            legal = legal_moves(game, board, game.turn)
            if move not in legal:
                return f"illegal:{game.turn}:{uci}", move_history, ai_times, sf_times, move_times, game, board

            apply_move(game, board, move)
            move_history.append(uci)
            move_times.append((ply + 1, mover, game.turn, uci, elapsed))
            if verbose_moves:
                print(f"  ply {ply + 1:03d}: {mover:<9} {uci:<5} {elapsed:6.2f}s", flush=True)
            if progress_callback is not None:
                progress_callback(ply + 1, ai_times, sf_times)

        ai_eval = ai.evaluate(game, board)
        if ai_eval > 250:
            result = f"adjudicated:{ai_color}"
        elif ai_eval < -250:
            result = f"adjudicated:{'black' if ai_color == 'white' else 'white'}"
        else:
            result = "draw:maxplies"
        return result, move_history, ai_times, sf_times, move_times, game, board
    finally:
        ai.close_pool()


def score_for_ai(result, ai_color):
    if result.startswith("draw"):
        return 0.5
    if result.startswith("checkmate:") or result.startswith("adjudicated:"):
        winner = result.split(":", 1)[1]
        return 1.0 if winner == ai_color else 0.0
    return 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--elo", type=int, default=1320)
    parser.add_argument("--movetime", type=int, default=100)
    parser.add_argument("--max-plies", type=int, default=120)
    parser.add_argument("--verbose-moves", action="store_true")
    parser.add_argument("--progress-every", type=int, default=0)
    parser.add_argument("--ai-color", choices=("white", "black"))
    parser.add_argument("--save-json", type=Path)
    args = parser.parse_args()

    stockfish = Stockfish(STOCKFISH_PATH, elo=args.elo, movetime_ms=args.movetime)
    try:
        total_score = 0.0
        game_records = []
        series_start = time.perf_counter()
        completed_plies_before_game = 0
        for game_idx in range(args.games):
            ai_color = args.ai_color or ("white" if game_idx % 2 == 0 else "black")
            print(f"Game {game_idx + 1}: AI={ai_color} vs Stockfish Elo {args.elo}", flush=True)

            def progress_callback(current_game_ply, ai_times, sf_times):
                if args.progress_every <= 0:
                    return
                if current_game_ply % args.progress_every != 0 and current_game_ply != args.max_plies:
                    return
                elapsed = time.perf_counter() - series_start
                completed_plies = completed_plies_before_game + current_game_ply
                remaining_cap_plies = (args.games - game_idx - 1) * args.max_plies + (args.max_plies - current_game_ply)
                avg_seconds_per_ply = elapsed / max(completed_plies, 1)
                eta = avg_seconds_per_ply * remaining_cap_plies
                avg_ai = sum(ai_times) / len(ai_times) if ai_times else 0.0
                avg_sf = sum(sf_times) / len(sf_times) if sf_times else 0.0
                print(
                    f"  progress: game={game_idx + 1}/{args.games} ply={current_game_ply}/{args.max_plies} "
                    f"elapsed={format_duration(elapsed)} eta_cap={format_duration(eta)} "
                    f"avg_ai={avg_ai:.2f}s avg_sf={avg_sf:.2f}s",
                    flush=True,
                )

            result, moves, ai_times, sf_times, move_times, game, board = play_game(
                stockfish,
                ai_color,
                args.max_plies,
                verbose_moves=args.verbose_moves,
                progress_callback=progress_callback,
            )
            completed_plies_before_game += len(moves)
            score = score_for_ai(result, ai_color)
            total_score += score
            max_ai_time = max(ai_times) if ai_times else 0.0
            long_ai_moves = sum(1 for move_time in ai_times if move_time >= 8.0)
            print(
                f"Game {game_idx + 1}: AI={ai_color} result={result} "
                f"score={score} plies={len(moves)} "
                f"avg_ai_time={sum(ai_times) / len(ai_times):.2f}s "
                f"max_ai_time={max_ai_time:.2f}s "
                f"long_ai_moves={long_ai_moves} "
                f"avg_sf_time={sum(sf_times) / len(sf_times):.2f}s",
                flush=True,
            )
            print("moves:", " ".join(moves), flush=True)
            print(f"final_eval_ai_perspective={ChessAI(1, 0, ai_color).evaluate(game, board)}", flush=True)
            print(flush=True)
            game_records.append(
                {
                    "game": game_idx + 1,
                    "ai_color": ai_color,
                    "elo": args.elo,
                    "movetime_ms": args.movetime,
                    "max_plies": args.max_plies,
                    "result": result,
                    "score": score,
                    "plies": len(moves),
                    "moves": moves,
                    "ai_times": ai_times,
                    "stockfish_times": sf_times,
                    "move_times": [
                        {
                            "ply": ply,
                            "mover": mover,
                            "next_turn": next_turn,
                            "move": move,
                            "time": elapsed,
                        }
                        for ply, mover, next_turn, move, elapsed in move_times
                    ],
                    "avg_ai_time": sum(ai_times) / len(ai_times) if ai_times else 0.0,
                    "max_ai_time": max_ai_time,
                    "long_ai_moves": long_ai_moves,
                    "avg_stockfish_time": sum(sf_times) / len(sf_times) if sf_times else 0.0,
                    "final_eval_ai_perspective": ChessAI(1, 0, ai_color).evaluate(game, board),
                }
            )

        pct = total_score / args.games
        print(f"Total: {total_score}/{args.games} = {pct:.0%} against Stockfish Elo {args.elo}", flush=True)
        if pct >= 0.75:
            print("Interpretation: engine is likely above this Elo setting.", flush=True)
        elif pct >= 0.35:
            print("Interpretation: engine is competitive around this Elo setting.", flush=True)
        else:
            print("Interpretation: engine is likely below this Elo setting.", flush=True)
        if args.save_json:
            payload = {
                "elo": args.elo,
                "movetime_ms": args.movetime,
                "max_plies": args.max_plies,
                "games": game_records,
                "total_score": total_score,
                "score_fraction": pct,
                "elapsed_seconds": time.perf_counter() - series_start,
            }
            with open(args.save_json, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)
            print(f"Saved match data to {args.save_json}", flush=True)
    finally:
        stockfish.close()


if __name__ == "__main__":
    main()
