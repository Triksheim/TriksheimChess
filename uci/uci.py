#!/usr/bin/env python3
"""UCI adapter for TriksheimChessPy.

The original project is a pygame chess app. This module exposes the existing
hard-mode Python AI as a Universal Chess Interface process so chess GUIs can
launch it as an engine.
"""

import contextlib
import io
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI import ChessAI
from board import ChessBoard
from constants import EASY_MODE, HARD_MODE, MED_MODE, STARTING_FEN
from game import ChessGame
from pieces import Bishop, King, Knight, Pawn, Queen, Rook


FILES = "abcdefgh"
PIECES_BY_PROMOTION = {
    "q": Queen,
    "r": Rook,
    "b": Bishop,
    "n": Knight,
}
START_FEN_FULL = STARTING_FEN + " w KQkq - 0 1"


def out(text):
    print(text, flush=True)


def square_to_uci(square):
    return FILES[square % 8] + str(square // 8 + 1)


def uci_to_square(text):
    return (int(text[1]) - 1) * 8 + FILES.index(text[0])


def uci_to_move(text):
    return uci_to_square(text[:2]), uci_to_square(text[2:4])


def move_to_uci(move, board=None):
    if move is None or move == (None, None):
        return "0000"
    uci = square_to_uci(move[0]) + square_to_uci(move[1])
    if board is not None:
        piece = board.get_piece(move[0])
        if isinstance(piece, Pawn):
            if (piece.color == "white" and move[1] >= 56) or (piece.color == "black" and move[1] <= 7):
                uci += "q"
    return uci


def legal_moves(game, board, color=None):
    color = color or game.turn
    moves = []
    for square, _ in board.get_squares_with_piece(color):
        for move in game.get_valid_moves(board, square, color) or []:
            moves.append((square, move))
    return moves


def set_all_rook_king_flags_moved(board):
    for piece in board.board:
        if isinstance(piece, (King, Rook)):
            piece.not_moved = False


def set_castling_flags_from_fen(board, castling):
    set_all_rook_king_flags_moved(board)
    rights = "" if castling == "-" else castling

    white_king = board.get_piece(4)
    black_king = board.get_piece(60)
    if isinstance(white_king, King) and white_king.color == "white":
        white_king.not_moved = "K" in rights or "Q" in rights
    if isinstance(black_king, King) and black_king.color == "black":
        black_king.not_moved = "k" in rights or "q" in rights

    for letter, square, color in (
        ("Q", 0, "white"),
        ("K", 7, "white"),
        ("q", 56, "black"),
        ("k", 63, "black"),
    ):
        rook = board.get_piece(square)
        if isinstance(rook, Rook) and rook.color == color:
            rook.not_moved = letter in rights


def set_en_passant_from_fen(board, game, ep_square):
    if ep_square == "-":
        board.last_move = (None, None, None, False)
        return

    ep = uci_to_square(ep_square)
    if game.turn == "white":
        pawn_square = ep - 8
        original_square = ep + 8
    else:
        pawn_square = ep + 8
        original_square = ep - 8

    pawn = board.get_piece(pawn_square) if 0 <= pawn_square < 64 else None
    if isinstance(pawn, Pawn):
        board.last_move = (pawn, original_square, pawn_square, False)
    else:
        board.last_move = (None, None, None, False)


def load_full_fen(fen):
    parts = fen.strip().split()
    if len(parts) == 1:
        parts += ["w", "KQkq", "-", "0", "1"]
    if len(parts) < 4:
        raise ValueError("FEN needs at least board, active color, castling, and en passant fields")

    board = ChessBoard()
    game = ChessGame()
    game.load_position_from_fen(board, parts[0])
    game.turn = "black" if parts[1] == "b" else "white"
    set_castling_flags_from_fen(board, parts[2])
    set_en_passant_from_fen(board, game, parts[3])
    board.board_state_log = [game.get_position_key(board)]
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")
    game.evaluate_board(board)
    return game, board


def apply_move(game, board, uci):
    move = uci_to_move(uci)
    if move not in legal_moves(game, board, game.turn):
        raise ValueError(f"Illegal move {uci} for {game.turn}")

    promotion = uci[4:5].lower()
    game.execute_move(board, move[0], move[1])
    if promotion and promotion in PIECES_BY_PROMOTION:
        moved_piece = board.get_piece(move[1])
        if moved_piece is not None:
            board.add_piece(PIECES_BY_PROMOTION[promotion](moved_piece.color), move[1])
    game.update_gamestate(board)
    game.evaluate_board(board)
    return move


def parse_position(command):
    tokens = command.split()
    if len(tokens) < 2:
        return START_FEN_FULL, []

    moves = []
    if tokens[1] == "startpos":
        fen = START_FEN_FULL
        if "moves" in tokens:
            moves = tokens[tokens.index("moves") + 1:]
        return fen, moves

    if tokens[1] == "fen":
        if "moves" in tokens:
            move_idx = tokens.index("moves")
            fen_tokens = tokens[2:move_idx]
            moves = tokens[move_idx + 1:]
        else:
            fen_tokens = tokens[2:]
        return " ".join(fen_tokens), moves

    return START_FEN_FULL, []


def parse_go(command):
    tokens = command.split()
    params = {}
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token in {"depth", "movetime", "nodes", "wtime", "btime", "winc", "binc"} and i + 1 < len(tokens):
            try:
                params[token] = int(tokens[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1
    return params


class TriksheimPyUci:
    def __init__(self):
        self.mode = "hard"
        self.game, self.board = load_full_fen(START_FEN_FULL)
        self.ais = {}
        self.ensure_ai("white")
        self.ensure_ai("black")

    def new_game(self):
        self.game, self.board = load_full_fen(START_FEN_FULL)
        for ai in self.ais.values():
            ai.close_pool()
        self.ais = {}
        self.ensure_ai("white")
        self.ensure_ai("black")

    def mode_config(self):
        if self.mode == "easy":
            return EASY_MODE
        if self.mode == "medium":
            return MED_MODE
        return HARD_MODE

    def ensure_ai(self, color):
        ai = self.ais.get(color)
        if ai is not None:
            return ai
        config = self.mode_config()
        ai = ChessAI(config["depth"], config["depth_inc"], color)
        ai.use_multiprocessing = True
        ai.use_dynamic_depth = config.get("dynamic_depth", False)
        ai.soft_time_limit = config.get("soft_time_limit")
        ai.time_limit = config.get("time_limit")
        self.ais[color] = ai
        return ai

    def set_option(self, command):
        lower = command.lower()
        if "name mode" in lower and "value" in lower:
            value = command[lower.index("value") + len("value"):].strip().lower()
            if value in {"easy", "medium", "hard"}:
                self.mode = value
                self.new_game()
        elif "name multiprocessing" in lower and "value" in lower:
            value = command[lower.index("value") + len("value"):].strip().lower()
            enabled = value not in {"false", "0", "off", "no"}
            for ai in self.ais.values():
                ai.use_multiprocessing = enabled

    def set_position(self, command):
        fen, moves = parse_position(command)
        self.game, self.board = load_full_fen(fen)
        for move in moves:
            apply_move(self.game, self.board, move)

    def bestmove(self, go_params):
        color = self.game.turn
        ai = self.ensure_ai(color)
        config = self.mode_config()
        ai.depth = config["depth"]
        ai.use_depth_inc = config.get("depth_inc", 0) > 0
        ai.depth_inc_limit = config.get("depth_inc", 0)
        ai.use_dynamic_depth = config.get("dynamic_depth", False)
        ai.soft_time_limit = config.get("soft_time_limit")
        ai.time_limit = config.get("time_limit")

        if "movetime" in go_params and go_params["movetime"] > 0:
            seconds = max(0.05, go_params["movetime"] / 1000)
            ai.use_dynamic_depth = True
            ai.soft_time_limit = seconds
            ai.time_limit = max(seconds + 0.05, seconds * 1.25)

        start = time.perf_counter()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                move, evaluation, _ = ai.generate_move(self.game, self.board)
        except Exception as exc:
            out(f"info string search error: {exc}")
            return "0000"

        elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))
        summary = ai.last_search_summary or {}
        nodes = int(summary.get("nodes", getattr(ai.nodes, "value", 0)))
        score = evaluation if evaluation is not None else ai.evaluate(self.game, self.board)
        depth = summary.get("completed_depth") or summary.get("depth") or ai.depth
        pv = move_to_uci(move, self.board)
        out(f"info depth {depth} score cp {int(score)} nodes {nodes} time {elapsed_ms} pv {pv}")
        return pv

    def close(self):
        for ai in self.ais.values():
            ai.close_pool()


def main():
    engine = TriksheimPyUci()
    try:
        for raw in sys.stdin:
            command = raw.strip()
            if not command:
                continue
            if command == "uci":
                out("id name TriksheimChess Py")
                out("id author Martin")
                out("option name Mode type combo default hard var easy var medium var hard")
                out("option name Multiprocessing type check default true")
                out("uciok")
            elif command == "isready":
                out("readyok")
            elif command == "ucinewgame":
                engine.new_game()
            elif command.startswith("setoption "):
                engine.set_option(command)
            elif command.startswith("position "):
                try:
                    engine.set_position(command)
                except Exception as exc:
                    out(f"info string position error: {exc}")
            elif command.startswith("go"):
                best = engine.bestmove(parse_go(command))
                out(f"bestmove {best}")
            elif command == "stop":
                out("bestmove 0000")
            elif command == "quit":
                break
    finally:
        engine.close()


if __name__ == "__main__":
    main()
