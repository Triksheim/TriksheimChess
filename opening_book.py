from board import ChessBoard
from constants import STARTING_FEN
from game import ChessGame


OPENING_LINES = [
    (100, "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1 f8e7"),
    (105, "e2e4 b8c6 d2d4 d7d5 b1c3 d5e4 d4d5 c6b8 f2f3"),
    (100, "e2e4 b8c6 d2d4 e7e5 g1f3 e5d4 f3d4 g8f6 b1c3"),
    (90, "e2e4 b8c6 g1f3 e7e5 f1b5 g8f6 e1g1 f8c5"),
    (85, "e2e4 b8c6 b1c3 e7e5 g1f3 g8f6 f1b5"),
    (95, "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6"),
    (90, "e2e4 c7c5 g1f3 b8c6 d2d4 c5d4 f3d4 g8f6 b1c3 d7d6"),
    (90, "e2e4 e7e6 d2d4 d7d5 b1c3 g8f6 e4e5 f6d7 f2f4 c7c5"),
    (88, "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4 c8f5"),
    (85, "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6 c1g5 f8e7 e2e3 e8g8"),
    (82, "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 e2e3 e8g8 f1d3 d7d5"),
    (80, "d2d4 g8f6 c2c4 g7g6 b1c3 f8g7 e2e4 d7d6 g1f3 e8g8"),
    (76, "c2c4 e7e5 b1c3 g8f6 g1f3 b8c6 g2g3 d7d5 c4d5 f6d5"),
    (74, "g1f3 d7d5 d2d4 g8f6 c2c4 e7e6 b1c3 f8e7 c1g5 e8g8"),

    # Practical anti-offbeat lines seen in the local Stockfish match suite.
    (120, "b1c3 c7c6 d2d4 h7h6 e2e4 g7g6 c1f4 d7d6 d1d2"),
    (120, "b1c3 e7e5 g1f3 d7d5 f3e5 b8d7 d2d4 g8f6 c1g5"),
    (170, "e2e3 g7g6"),
    (170, "c2c3 e7e5"),
    (120, "e2e3 b8c6 d2d4 d7d5 c2c4 e7e5 c4d5 f8b4 b1c3 d8d5"),
    (120, "c2c3 b8c6 e2e4 d7d5 e4d5 d8d5 d1b3 d5e4 e1d1 e4g6"),
]


def uci_to_square(text):
    file_index = ord(text[0]) - ord("a")
    rank = int(text[1]) - 1
    return rank * 8 + file_index


def uci_to_move(text):
    return uci_to_square(text[:2]), uci_to_square(text[2:4])


def legal_moves(game, board, color):
    moves = []
    for square, _ in board.get_squares_with_piece(color):
        for move in game.get_valid_moves(board, square, color) or []:
            moves.append((square, move))
    return moves


def apply_uci(game, board, uci):
    move = uci_to_move(uci)
    if move not in legal_moves(game, board, game.turn):
        raise ValueError(f"Illegal book move {uci} for {game.turn}")
    game.execute_move(board, move[0], move[1])
    game.update_gamestate(board)
    game.evaluate_board(board)


def build_opening_book():
    book = {}
    for weight, line in OPENING_LINES:
        board = ChessBoard()
        game = ChessGame()
        game.load_position_from_fen(board, STARTING_FEN)
        moves = line.split()

        for uci in moves:
            key = game.get_position_key(board)
            candidates = book.setdefault(key, {})
            candidates[uci] = candidates.get(uci, 0) + weight
            apply_uci(game, board, uci)

    return book


_OPENING_BOOK = None


def get_opening_book():
    global _OPENING_BOOK
    if _OPENING_BOOK is None:
        _OPENING_BOOK = build_opening_book()
    return _OPENING_BOOK
