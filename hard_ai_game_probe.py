from AI import ChessAI
from board import ChessBoard
from constants import HARD_MODE, STARTING_FEN
from game import ChessGame
from pieces import Bishop, King, Knight, Pawn, Queen, Rook


PIECE_NAMES = {
    Pawn: "",
    Knight: "N",
    Bishop: "B",
    Rook: "R",
    Queen: "Q",
    King: "K",
}


OPENING_PREFS = [
    "e2e4",
    "g1f3",
    "f1c4",
    "e1g1",
    "d2d4",
    "b1c3",
    "c1g5",
    "f1b5",
    "a2a3",
    "h2h3",
]

OPENING_PREF_BONUS = {
    uci: max(10, 120 - index * 10)
    for index, uci in enumerate(OPENING_PREFS)
}


def square_to_uci(square):
    file_idx = square % 8
    rank = (square // 8) + 1
    return chr(ord("a") + file_idx) + str(rank)


def move_to_uci(move):
    return square_to_uci(move[0]) + square_to_uci(move[1])


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


def eval_for_color(game, board, color):
    game.evaluate_board(board)
    if color == "white":
        return game.white_eval - game.black_eval
    return game.black_eval - game.white_eval


def move_score(game, board, color, move):
    piece = board.get_piece(move[0])
    captured = board.get_piece(move[1]) if board.contains_piece(move[1]) else None
    score = 0

    if captured:
        score += 10000 + captured.value * 10 - piece.value
    if isinstance(piece, Pawn):
        if (piece.color == "white" and move[1] >= 56) or (piece.color == "black" and move[1] <= 7):
            score += 20000
    if isinstance(piece, King) and abs(move[0] - move[1]) == 2:
        score += 300

    state = game.make_move_for_search(board, move[0], move[1])
    try:
        score += eval_for_color(game, board, color)
        if game.king_in_check(board):
            score += 100
    finally:
        game.unmake_move_for_search(board, state)

    return score


class ProbePlayer:
    def __init__(self, color):
        self.color = color

    def choose_move(self, game, board):
        moves = legal_moves(game, board, self.color)

        return max(
            moves,
            key=lambda move: (
                move_score(game, board, self.color, move)
                + OPENING_PREF_BONUS.get(move_to_uci(move), 0),
                -move[0],
                -move[1],
            ),
        )


def piece_symbol(piece):
    if piece is None:
        return "."
    symbol = PIECE_NAMES[type(piece)] or "P"
    if piece.color == "black":
        symbol = symbol.lower()
    return symbol


def board_ascii(board):
    rows = []
    for rank in range(7, -1, -1):
        row = []
        for file_idx in range(8):
            row.append(piece_symbol(board.get_piece(rank * 8 + file_idx)))
        rows.append(f"{rank + 1} " + " ".join(row))
    rows.append("  a b c d e f g h")
    return "\n".join(rows)


def game_status(game, board):
    if legal_moves(game, board, game.turn):
        return None
    if game.king_in_check(board):
        return f"checkmate, {('black' if game.turn == 'white' else 'white')} wins"
    return "stalemate"


def main():
    board = ChessBoard()
    game = ChessGame()
    game.load_position_from_fen(board, STARTING_FEN)

    white = ProbePlayer("white")
    black = ChessAI(HARD_MODE["depth"], HARD_MODE["depth_inc"], "black")
    black.use_multiprocessing = True
    black.use_dynamic_depth = HARD_MODE.get("dynamic_depth", False)
    black.soft_time_limit = HARD_MODE.get("soft_time_limit")
    black.time_limit = HARD_MODE.get("time_limit")

    move_log = []
    max_plies = 80

    try:
        for ply in range(max_plies):
            status = game_status(game, board)
            if status:
                print(status)
                break

            if game.turn == "white":
                move = white.choose_move(game, board)
            else:
                ai_move, _, _ = black.generate_move(game, board)
                move = ai_move

            side = game.turn
            uci = move_to_uci(move)
            apply_move(game, board, move)
            notation = game.move_notation_log[-1]
            move_log.append((side, uci, notation))
            print(f"{ply + 1:02d}. {side:5} {uci:5} {notation}")

            if game.repetition:
                print("draw by repetition")
                break
        else:
            print(f"stopped after {max_plies} plies")
    finally:
        black.close_pool()

    print()
    print(board_ascii(board))
    print()
    print(f"Final eval from black AI perspective: {black.evaluate(game, board)}")
    print(f"Moves played: {len(move_log)} plies")


if __name__ == "__main__":
    main()
