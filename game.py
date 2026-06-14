from constants import *
from pieces import *
from pieces_table import *
import time as t
from dataclasses import dataclass
from typing import Dict, Any


SLIDING_DIRECTION_DELTAS = {
    -9: (-1, -1),
    -8: (-1, 0),
    -7: (-1, 1),
    -1: (0, -1),
    1: (0, 1),
    7: (1, -1),
    8: (1, 0),
    9: (1, 1),
}

SLIDING_RAYS = {}
for _square in range(64):
    _row, _col = divmod(_square, 8)
    _rays = {}
    for _move, (_dr, _dc) in SLIDING_DIRECTION_DELTAS.items():
        _ray = []
        _next_row = _row + _dr
        _next_col = _col + _dc
        while 0 <= _next_row < 8 and 0 <= _next_col < 8:
            _ray.append(_next_row * 8 + _next_col)
            _next_row += _dr
            _next_col += _dc
        _rays[_move] = _ray
    SLIDING_RAYS[_square] = _rays

KNIGHT_DELTAS = (
    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
    (1, -2), (1, 2), (2, -1), (2, 1),
)
KING_DELTAS = (
    (0, -1), (0, 1), (-1, 0), (1, 0),
    (-1, 1), (1, -1), (-1, -1), (1, 1),
)
PAWN_ATTACK_DELTAS = {
    "white": ((1, -1), (1, 1)),
    "black": ((-1, -1), (-1, 1)),
}


def _precompute_leaper_moves(deltas):
    moves_by_square = {}
    for square in range(64):
        row, col = divmod(square, 8)
        moves = []
        for dr, dc in deltas:
            new_row = row + dr
            new_col = col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                moves.append(new_row * 8 + new_col)
        moves_by_square[square] = tuple(moves)
    return moves_by_square


KNIGHT_MOVES_BY_SQUARE = _precompute_leaper_moves(KNIGHT_DELTAS)
KING_MOVES_BY_SQUARE = _precompute_leaper_moves(KING_DELTAS)
PAWN_ATTACKS_BY_COLOR = {
    color: _precompute_leaper_moves(deltas)
    for color, deltas in PAWN_ATTACK_DELTAS.items()
}
SQUARE_ROWS = tuple(square // 8 for square in range(64))
SQUARE_COLS = tuple(square % 8 for square in range(64))


@dataclass
class SearchMoveState:
    board_board: list
    board_int_board: list
    board_last_move: tuple
    board_move_log_len: int
    board_board_state_log_len: int
    white_king_square_before: int
    black_king_square_before: int
    game_turn_before: str
    game_repetition_before: bool
    game_move_count_before: int
    piece_not_moved_before: Dict[Any, bool]
    attacked_squares_by_white_before: list
    attacked_squares_by_black_before: list
    white_king_is_pinned_before: bool
    black_king_is_pinned_before: bool
    white_queen_is_pinned_before: bool
    black_queen_is_pinned_before: bool


class ChessGame():
    def __init__(self, white_clock=900, black_clock=900, increment=0):
        self.turn = "white"
        self.white_clock = white_clock
        self.black_clock = black_clock
        self.time_increment = increment
        self.white_move_clock = 0
        self.black_move_clock = 0
        self.move_count = 0
        self.piece_count = 0
        self.selected_square = None
        self.ai_move = None
        self.game_ended = False
        self.checkmate = False
        self.stalemate = False
        self.repetition = False
        self.white_king_has_moved = False
        self.black_king_has_moved = False
        self.white_king_is_pinned = False
        self.black_king_is_pinned = False
        self.white_queen_is_pinned = False
        self.black_queen_is_pinned = False
        self.white_eval = 0
        self.black_eval = 0
        self.white_piece_value = 0
        self.black_piece_value = 0
        self.attacked_squares_by_white = []
        self.attacked_squares_by_black = []
        self.move_notation_log = []

        
    def clock_tick(self):
        t.sleep(1)
        if self.turn == "white" and self.white_clock > 0:
            self.white_clock -= 1
            self.white_move_clock += 1
            
        elif self.black_clock > 0:
            self.black_clock -= 1
            self.black_move_clock += 1

    def clock_increment(self):
        if self.turn == "white":
            self.white_clock += self.time_increment   
        else:
            self.black_clock += self.time_increment

    def swap_turn(self):
        self.turn = 'black' if self.turn == 'white' else 'white'

    def is_checkmated(self, board, color):
        return self.king_in_check(board, color) and self.checkmate

    def king_in_check(self, board, color=None):
        if color is None:
            color = self.turn
        if color == "white":
            if board.white_king_square in self.attacked_squares_by_black:
                return True
        else:
            if board.black_king_square in self.attacked_squares_by_white:
                return True
        return False
    
    def no_valid_moves(self, board):
        color = self.turn
        ally_pieces = board.get_squares_with_piece(color)
        for square, piece in ally_pieces:
            if self.get_valid_moves(board, square, color):
                return False
        return True
            
    def load_position_from_fen(self, board, fen):
        """Places pieces on the board based on the FEN string"""
        pieces = {'p':Pawn, 'r':Rook , 'n':Knight, 'b':Bishop, 'q':Queen, 'k':King}
        file = 0
        rank = 7
        for char in fen:
            if char == '/': # Move down one rank
                file = 0
                rank -= 1
            else:
                if char.isdigit(): # Move file (empty space)
                    file += int(char)
                else:
                    if char.isupper():
                        color = "white"
                    else:
                        color = "black"
                    piece = pieces[char.lower()](color)
                    board_index = rank * 8 + file
                    board.add_piece(piece, board_index)
                    file += 1
        self.update_attacked_squares(board, "white")
        self.update_attacked_squares(board, "black")
        self.evaluate_board(board)
        board.board_state_log = [self.get_position_key(board)]

    def eval_piece_count_value(self, board):
        white_piece_value = 0
        white_pieces = board.get_pieces_for_color("white")
        for piece in white_pieces:
            white_piece_value += piece.value
        black_piece_value = 0
        black_pieces = board.get_pieces_for_color("black")
        for piece in black_pieces:
            black_piece_value += piece.value

        self.white_piece_value = white_piece_value // 100
        self.black_piece_value = black_piece_value // 100
        
    def get_algebraic_notation(self, board):
        # Adds the chess notation for last move to log
        piece, original_square, new_square, is_capture = board.last_move
        notation = ""
        match piece.name:
            case "Rook":
                notation += "R"
            case "Knight":
                notation += "N"
            case "Bishop":
                notation += "B"
            case "Queen":
                notation += "Q"
            case "King":
                notation += "K"

        if is_capture:
            if piece.name == "Pawn":
                _, from_col = self.square_to_row_col(original_square)
                notation += BOARD_FILES[from_col]
            notation += "x"

        row, col = self.square_to_row_col(new_square)
        file = BOARD_FILES[col]
        rank = str(BOARD_RANKS[row])
        notation += file + rank
        
        if piece.name == "King" and (original_square == 4 or original_square == 60):
            if new_square in (6,62):
                notation = "O-O"
            elif new_square in (2,58):
                notation = "O-O-O"

        if self.king_in_check(board):
            notation += "+"

        self.move_notation_log.append(notation)

    def evaluate_board(self, board):
        white_pieces = board.get_squares_with_piece("white")
        black_pieces = board.get_squares_with_piece("black")
        white_attack_counts = self.count_squares(self.attacked_squares_by_white)
        black_attack_counts = self.count_squares(self.attacked_squares_by_black)
        self.piece_count = len(white_pieces) + len(black_pieces)
        white_eval, white_count = self.evaluate_color(board, "white", white_pieces, black_pieces, white_attack_counts, black_attack_counts)
        black_eval, black_count = self.evaluate_color(board, "black", black_pieces, white_pieces, black_attack_counts, white_attack_counts)
        self.white_eval = white_eval
        self.black_eval = black_eval
        self.piece_count = white_count + black_count
        if self.piece_count <= 10:
            if self.white_eval > self.black_eval + 500:
                self.king_chase(board, "white")
            elif self.black_eval > self.white_eval + 500:
                self.king_chase(board, "black")

    def square_to_row_col(self, square):
        return SQUARE_ROWS[square], SQUARE_COLS[square]

    def count_squares(self, squares):
        counts = [0 for _ in range(64)]
        for square in squares:
            if 0 <= square < 64:
                counts[square] += 1
        return counts

    def get_position_key(self, board):
        """Return the full chess state needed for repetition and TT lookups."""
        return (
            tuple(board.int_board),
            self.turn,
            self.get_castling_rights(board),
            self.get_en_passant_target(board),
        )

    def get_castling_rights(self, board):
        rights = []
        board_squares = board.board
        for color, king_square, queenside_rook, kingside_rook in (
            ("white", 4, 0, 7),
            ("black", 60, 56, 63),
        ):
            king = board_squares[king_square]
            king_can_castle = (
                isinstance(king, King)
                and king.color == color
                and king.not_moved
            )

            for rook_square in (queenside_rook, kingside_rook):
                rook = board_squares[rook_square]
                rights.append(
                    king_can_castle
                    and isinstance(rook, Rook)
                    and rook.color == color
                    and rook.not_moved
                )

        return tuple(rights)

    def get_en_passant_target(self, board):
        last_piece, original_square, new_square, _ = board.last_move
        if isinstance(last_piece, Pawn) and abs(new_square - original_square) == 16:
            return (original_square + new_square) // 2
        return None

    def king_chase(self, board, color):
        w_row, w_col = self.square_to_row_col(board.white_king_square)
        b_row, b_col = self.square_to_row_col(board.black_king_square)
        distance = abs(w_row - b_row) + abs(w_col - b_col)

        if color == "white":
            self.white_eval += (8 - distance) * 50
            if b_row == 5 or b_col == 5:
                self.white_eval += 100
            elif b_row == 6 or b_col == 6:
                self.white_eval += 200
            elif b_row == 7 or b_col == 7:
                self.white_eval += 300

        else:
            self.black_eval += (8 - distance) * 50
            if w_row == 5 or w_col == 5:
                self.black_eval += 100
            elif w_row == 6 or w_col == 6:
                self.black_eval += 200
            elif w_row == 7 or w_col == 7:
                self.black_eval += 300

    def is_passed_pawn(self, square, color, opponent_pawns):
        row = SQUARE_ROWS[square]
        col = SQUARE_COLS[square]
        for opponent_square in opponent_pawns:
            opponent_row = SQUARE_ROWS[opponent_square]
            opponent_col = SQUARE_COLS[opponent_square]
            if abs(opponent_col - col) > 1:
                continue
            if color == "white" and opponent_row > row:
                return False
            if color == "black" and opponent_row < row:
                return False
        return True

    def pawn_structure_bonus(self, square, color, ally_pawn_files, opponent_pawns, ally_pawns=None, attack_counts=None):
        row = SQUARE_ROWS[square]
        col = SQUARE_COLS[square]
        bonus = 0

        if ally_pawn_files[col] > 1:
            bonus -= 12
        if (col == 0 or ally_pawn_files[col - 1] == 0) and (col == 7 or ally_pawn_files[col + 1] == 0):
            bonus -= 10

        if self.is_passed_pawn(square, color, opponent_pawns):
            advancement = row if color == "white" else 7 - row
            bonus += 18 + advancement * 10
            if advancement >= 4:
                bonus += (advancement - 3) * 12
            if attack_counts is not None and attack_counts[square] > 0:
                bonus += 12
            if ally_pawns is not None:
                for ally_square in ally_pawns:
                    if ally_square == square:
                        continue
                    if abs(SQUARE_COLS[ally_square] - col) == 1 and abs(SQUARE_ROWS[ally_square] - row) <= 1:
                        bonus += 10
                        break

        return bonus

    def rook_file_bonus(self, square, ally_pawn_files, opponent_pawn_files):
        col = SQUARE_COLS[square]
        if ally_pawn_files[col] == 0 and opponent_pawn_files[col] == 0:
            return 20
        if ally_pawn_files[col] == 0:
            return 10
        return 0

    def attack_activity_bonus(self, attacked_squares):
        unique_attacks = set(attacked_squares)
        return len(unique_attacks) * 2 + max(0, len(attacked_squares) - len(unique_attacks))

    def king_zone_squares(self, king_square, color):
        row = SQUARE_ROWS[king_square]
        col = SQUARE_COLS[king_square]
        direction = 1 if color == "white" else -1
        squares = []
        for row_delta in (-1, 0, 1, direction * 2):
            for col_delta in (-1, 0, 1):
                new_row = row + row_delta
                new_col = col + col_delta
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    square = new_row * 8 + new_col
                    if square not in squares:
                        squares.append(square)
        return squares

    def king_safety_penalty(self, board, color, pieces, ally_pawn_files, opponent_attack_counts):
        if self.piece_count <= 10:
            return 0

        king_square = board.white_king_square if color == "white" else board.black_king_square
        king_row = SQUARE_ROWS[king_square]
        king_col = SQUARE_COLS[king_square]
        direction = 1 if color == "white" else -1
        board_squares = board.board
        penalty = 0

        attack_pressure = 0
        for square in self.king_zone_squares(king_square, color):
            attack_pressure += opponent_attack_counts[square]
        if attack_pressure:
            penalty += attack_pressure * 14

        for col in range(max(0, king_col - 1), min(7, king_col + 1) + 1):
            has_close_pawn = False
            has_far_pawn = False
            for distance in (1, 2):
                row = king_row + direction * distance
                if not 0 <= row < 8:
                    continue
                piece = board_squares[row * 8 + col]
                if isinstance(piece, Pawn) and piece.color == color:
                    if distance == 1:
                        has_close_pawn = True
                    has_far_pawn = True
            if not has_close_pawn:
                penalty += 12
            if not has_far_pawn:
                penalty += 8
            if ally_pawn_files[col] == 0:
                penalty += 8

        if color == "white":
            if king_square in (3, 4) and board_squares[5] is None and board_squares[6] is None:
                penalty += 12
        else:
            if king_square in (59, 60) and board_squares[61] is None and board_squares[62] is None:
                penalty += 12

        return penalty

    def hanging_piece_penalty(self, piece, square, ally_attack_counts, opponent_attack_counts):
        if isinstance(piece, King):
            return 0

        defenders = ally_attack_counts[square]
        attackers = opponent_attack_counts[square]
        if attackers <= 0:
            if defenders == 0 and not isinstance(piece, Pawn):
                return min(24, piece.value // 45)
            return 0

        if defenders == 0:
            return max(12, piece.value // 7)
        if attackers > defenders:
            return max(6, piece.value // 18)
        return 0

                     
    def evaluate_color(self, board, color, pieces=None, opponent_pieces=None, attack_counts=None, opponent_attack_counts=None):
        evaluation = 0
        
        if color == "white":
            evaluation += self.attack_activity_bonus(self.attacked_squares_by_white)
            if board.black_king_square in self.attacked_squares_by_white:
                evaluation += 30
            if self.black_king_is_pinned:
                evaluation += 10
            if self.white_king_is_pinned:
                evaluation -= 10
            if self.black_queen_is_pinned:
                evaluation += 10
            if self.white_queen_is_pinned:
                evaluation -= 10
            
        else:
            evaluation += self.attack_activity_bonus(self.attacked_squares_by_black)
            if board.white_king_square in self.attacked_squares_by_black:
                evaluation += 30
            if self.white_king_is_pinned:
                evaluation += 10
            if self.black_king_is_pinned:
                evaluation -= 10
            if self.white_queen_is_pinned:
                evaluation += 10
            if self.black_queen_is_pinned:
                evaluation -= 10

        opponent = "black" if color == "white" else "white"
        if pieces is None:
            pieces = board.get_squares_with_piece(color)
        if opponent_pieces is None:
            opponent_pieces = board.get_squares_with_piece(opponent)
        if attack_counts is None:
            attack_counts = self.count_squares(
                self.attacked_squares_by_white if color == "white" else self.attacked_squares_by_black
            )
        if opponent_attack_counts is None:
            opponent_attack_counts = self.count_squares(
                self.attacked_squares_by_black if color == "white" else self.attacked_squares_by_white
            )
        ally_pawns = [square for square, piece in pieces if piece.name == "Pawn"]
        opponent_pawns = [square for square, piece in opponent_pieces if piece.name == "Pawn"]
        ally_pawn_files = [0 for _ in range(8)]
        opponent_pawn_files = [0 for _ in range(8)]
        bishop_count = 0

        for square in ally_pawns:
            col = SQUARE_COLS[square]
            ally_pawn_files[col] += 1
        for square in opponent_pawns:
            col = SQUARE_COLS[square]
            opponent_pawn_files[col] += 1

        for _, piece in pieces:
            if piece.name == "Bishop":
                bishop_count += 1
        if bishop_count >= 2:
            evaluation += 38

        evaluation -= self.king_safety_penalty(board, color, pieces, ally_pawn_files, opponent_attack_counts)

        for square, piece in pieces:
            evaluation += piece.value

            if color == "white":

                if piece.name == "King":
                    if self.piece_count > 10:
                        evaluation += king_early_table[63-square]
                    else:
                        evaluation += king_late_table[63-square]
                    continue

                elif piece.name == "Rook":
                    evaluation += rook_table[63-square]
                    evaluation += self.rook_file_bonus(square, ally_pawn_files, opponent_pawn_files)
                elif piece.name == "Knight":
                    evaluation += knight_table[63-square]
                elif piece.name == "Bishop":
                    evaluation += bishop_table[63-square]
                elif piece.name == "Queen":
                    evaluation += queen_table[63-square]
                elif piece.name == "Pawn":
                    evaluation += pawn_table[63-square]
                    evaluation += self.pawn_structure_bonus(square, color, ally_pawn_files, opponent_pawns, ally_pawns, attack_counts)
                
                def_count = attack_counts[square]
                evaluation += (def_count * 3)
                evaluation -= self.hanging_piece_penalty(piece, square, attack_counts, opponent_attack_counts)

            else:
                if piece.name == "King":
                    if self.piece_count > 10:
                        evaluation += king_early_table[square]
                    else:
                        evaluation += king_late_table[square]
                    continue

                elif piece.name == "Rook":
                    evaluation += rook_table[square]
                    evaluation += self.rook_file_bonus(square, ally_pawn_files, opponent_pawn_files)
                elif piece.name == "Knight":
                    evaluation += knight_table[square]
                elif piece.name == "Bishop":
                    evaluation += bishop_table[square]
                elif piece.name == "Queen":
                    evaluation += queen_table[square]
                elif piece.name == "Pawn":
                    evaluation += pawn_table[square]
                    evaluation += self.pawn_structure_bonus(square, color, ally_pawn_files, opponent_pawns, ally_pawns, attack_counts)
                
                def_count = attack_counts[square]
                evaluation += (def_count * 3)
                evaluation -= self.hanging_piece_penalty(piece, square, attack_counts, opponent_attack_counts)

        return evaluation, len(pieces)
    
    def execute_move(self, board, original_square, new_square=None, log_state=True):
        self.move_count += 1
        if  original_square is None:
            original_square = self.selected_square
        
        if isinstance(board.board[original_square], King):
            if original_square - new_square == -2: 
                board.move_king(original_square, new_square, castle="kingside", log_state=log_state)
            elif original_square - new_square == 2: 
                board.move_king(original_square, new_square, castle="queenside", log_state=log_state)
            else:
                board.move_king(original_square, new_square, log_state=log_state)

        elif isinstance(board.board[original_square], Pawn):
            if new_square >= 56:
                board.move_pawn_promote(original_square, new_square, "white", log_state=log_state)
            elif new_square <= 7:
                board.move_pawn_promote(original_square, new_square, "black", log_state=log_state)
            elif isinstance(board.last_move[0], Pawn):
                if (abs(original_square - new_square) == 7 or abs(original_square - new_square) == 9) \
                and not board.contains_piece(new_square):
                    board.move_en_passant(original_square, new_square, log_state=log_state)
                else:
                    board.move_piece(original_square, new_square, log_state=log_state)
            else:
                board.move_piece(original_square, new_square, log_state=log_state)
        else:
            board.move_piece(original_square, new_square, log_state=log_state)

    def make_move_for_search(self, board, original_square, new_square):
        """move for search with previous state"""
        # Snapshot board arrays
        board_board = list(board.board)
        board_int_board = list(board.int_board)
        board_last_move = board.last_move
        board_move_log_len = len(board.move_log)
        board_board_state_log_len = len(board.board_state_log)

        # Snapshot king squares
        white_king_square_before = board.white_king_square
        black_king_square_before = board.black_king_square

        # Snapshot game state
        game_turn_before = self.turn
        game_repetition_before = self.repetition
        game_move_count_before = self.move_count

        # Snapshot only flags that can change during this move.
        piece_not_moved_before: Dict[Any, bool] = {}
        moved_piece = board.board[original_square]
        if moved_piece is not None and hasattr(moved_piece, "not_moved"):
            piece_not_moved_before[moved_piece] = moved_piece.not_moved

        if isinstance(moved_piece, King) and abs(original_square - new_square) == 2:
            rook_square = original_square + (3 if new_square > original_square else -4)
            rook = board.board[rook_square]
            if rook is not None and hasattr(rook, "not_moved"):
                piece_not_moved_before[rook] = rook.not_moved

        # Snapshot attacked squares and pinned flags
        attacked_squares_by_white_before = list(self.attacked_squares_by_white)
        attacked_squares_by_black_before = list(self.attacked_squares_by_black)
        white_king_is_pinned_before = self.white_king_is_pinned
        black_king_is_pinned_before = self.black_king_is_pinned
        white_queen_is_pinned_before = self.white_queen_is_pinned
        black_queen_is_pinned_before = self.black_queen_is_pinned

        state = SearchMoveState(
            board_board=board_board,
            board_int_board=board_int_board,
            board_last_move=board_last_move,
            board_move_log_len=board_move_log_len,
            board_board_state_log_len=board_board_state_log_len,
            white_king_square_before=white_king_square_before,
            black_king_square_before=black_king_square_before,
            game_turn_before=game_turn_before,
            game_repetition_before=game_repetition_before,
            game_move_count_before=game_move_count_before,
            piece_not_moved_before=piece_not_moved_before,
            attacked_squares_by_white_before=attacked_squares_by_white_before,
            attacked_squares_by_black_before=attacked_squares_by_black_before,
            white_king_is_pinned_before=white_king_is_pinned_before,
            black_king_is_pinned_before=black_king_is_pinned_before,
            white_queen_is_pinned_before=white_queen_is_pinned_before,
            black_queen_is_pinned_before=black_queen_is_pinned_before,
        )

        self.execute_move(board, original_square, new_square, log_state=False)
        self.update_gamestate_for_search(board)

        return state

    def unmake_move_for_search(self, board, state: SearchMoveState):
        """undo move made in search based on state"""
        # Restore board arrays
        board.board = list(state.board_board)
        board.int_board = list(state.board_int_board)

        # Restore last_move and logs
        board.last_move = state.board_last_move

        while len(board.move_log) > state.board_move_log_len:
            board.move_log.pop()
        while len(board.board_state_log) > state.board_board_state_log_len:
            board.board_state_log.pop()

        # Restore king squares
        board.white_king_square = state.white_king_square_before
        board.black_king_square = state.black_king_square_before

        # Restore game state
        self.turn = state.game_turn_before
        self.repetition = state.game_repetition_before
        self.move_count = state.game_move_count_before

        # Restore not_moved flags
        for piece, not_moved in state.piece_not_moved_before.items():
            piece.not_moved = not_moved

        # Restore attacked squares and pinned flags
        self.attacked_squares_by_white = state.attacked_squares_by_white_before
        self.attacked_squares_by_black = state.attacked_squares_by_black_before
        self.white_king_is_pinned = state.white_king_is_pinned_before
        self.black_king_is_pinned = state.black_king_is_pinned_before
        self.white_queen_is_pinned = state.white_queen_is_pinned_before
        self.black_queen_is_pinned = state.black_queen_is_pinned_before

    def update_gamestate(self, board):
        self.update_attacked_squares(board)
        self.swap_turn()
        self.update_attacked_squares(board)
        self.evaluate_board(board)
        board.board_state_log[-1] = self.get_position_key(board)
        board_state = board.board_state_log[-1]
        if board.board_state_log.count(board_state) >= 3:
            self.repetition = True
            
    def update_gamestate_for_search(self, board):
        """Lighter version of update_gamestate used inside minimax"""
        self.update_attacked_squares(board)
        self.swap_turn()
        self.update_attacked_squares(board)

        # repetition
        board_state = self.get_position_key(board)
        board.board_state_log.append(board_state)
        self.repetition = board.board_state_log.count(board_state) >= 3


    def update_attacked_squares(self, board, color=None):
        if not color:
            color = self.turn

        if color == "white":
            self.white_king_is_pinned = False
            self.white_queen_is_pinned = False
        else:
            self.black_king_is_pinned = False
            self.black_queen_is_pinned = False

        attacked_squares = []
        attacked_extend = attacked_squares.extend
        board_squares = board.board
        pawn_attacks = PAWN_ATTACKS_BY_COLOR
        king_moves = KING_MOVES_BY_SQUARE
        for square, piece in enumerate(board_squares):
            if piece is not None:
                if piece.color != color:
                    if piece.name == "Pawn":
                        attacked_extend(pawn_attacks[piece.color][square])
                    elif piece.name == "Rook" or piece.name == "Bishop" or piece.name == "Queen":
                        attacked_extend(self._get_valid_RBQ_moves(board, piece, square, get_attacking_squares=True))
                    elif piece.name == "Knight":
                        attacked_extend(self._get_valid_knight_moves(board, piece, square, get_attacking_squares=True))
                    elif piece.name == "King":
                        attacked_extend(king_moves[square])

        if color == "white":
            self.attacked_squares_by_black = attacked_squares
        else:
            self.attacked_squares_by_white = attacked_squares

        
    def _get_attacked_squares(self, board, piece, square):
        if piece.name == "Pawn":
            return self._get_attacked_pawn_squares(piece, square)
        elif piece.name == "Rook" or piece.name == "Bishop" or piece.name == "Queen":
            return self._get_valid_RBQ_moves(board, piece, square, get_attacking_squares=True)
        elif piece.name == "Knight":
            return self._get_valid_knight_moves(board, piece, square, get_attacking_squares=True)
        elif piece.name == "King":
            return self._get_attacked_king_squares(piece, square)
        return []


    def _get_attacked_pawn_squares(self, piece, start_square):
        return PAWN_ATTACKS_BY_COLOR[piece.color][start_square]


    def _get_attacked_king_squares(self, piece, start_square):
        return KING_MOVES_BY_SQUARE[start_square]


    def get_valid_moves(self, board, start_square, color=None):
        if not color:
            color = self.turn
        if board.contains_piece(start_square):
            piece = board.get_piece(start_square)
            if piece.color != color:
                return
        else:
            return
        
        valid_moves = []

        if piece.name == "Pawn":
            valid_moves.extend(self._get_valid_pawn_moves(board, piece, start_square))  
        elif piece.name == "Rook" or piece.name == "Bishop" or piece.name == "Queen":
            valid_moves.extend(self._get_valid_RBQ_moves(board, piece, start_square))
        elif piece.name == "Knight":
           valid_moves.extend(self._get_valid_knight_moves(board, piece, start_square))
        elif piece.name == "King":
            valid_moves.extend(self._get_valid_king_moves(board, piece, start_square, color))

        if color == "white":
            king_is_pinned = self.white_king_is_pinned
        else:
            king_is_pinned = self.black_king_is_pinned

       
        if (self.king_in_check(board) or king_is_pinned) and valid_moves:
            # valid_moves might be pseudo legal, filter out moves that leave king in check
            valid_valid_moves = []
            for move in valid_moves:
                state = self.make_move_for_search(board, start_square, move)
                try:
                    if not self.king_in_check(board, color):
                        valid_valid_moves.append(move)
                finally:
                    self.unmake_move_for_search(board, state)
            return valid_valid_moves if valid_valid_moves else None

        return valid_moves if valid_moves else None
    

    def _is_invalid_board_square(self, square):
        """ Check if outside of board range 0-63. """
        return square < 0 or square > 63

    def _is_wraparound_diagonal_move(self, start_square, move):
        """ Check wraparound on file (sides) for diagonal movement """
        if (start_square % 8 == 0 and (move == -9 or move == 7)):
            return True 
        if (start_square % 8 == 7 and (move == 9 or move == -7)):
            return True
        return False

    def _is_wraparound_sliding_move(self, start_square, end_square, move): 
        """ Check wraparound on file (sides) for slide movement. True if rank changed """ 
        return ((start_square // 8 != end_square // 8) and abs(move) == 1)
    
    def _is_wraparound_knight_move(self, start_square, new_square):
        """ Check wraparound on file (sides) for knight movement. True if rank changed more than 2 """
        return abs((start_square % 8) - (new_square % 8)) > 2
                                

    def _get_valid_pawn_moves(self, board, piece, start_square):
        """ Helper function for valid Pawn moves """
        valid_moves = []

        # Pawn forward movement
        new_square = start_square + piece.move
        if not self._is_invalid_board_square(new_square):
            if not board.contains_piece(new_square):
                valid_moves.append(new_square)

                # Pawn double step if not yet moved
                if piece.not_moved:
                    new_square = start_square + (piece.move * 2)
                    if not board.contains_piece(new_square):
                        valid_moves.append(new_square)

        # Pawn diagonal attack
        for new_square in PAWN_ATTACKS_BY_COLOR[piece.color][start_square]:
            if board.contains_piece(new_square):
                if piece.color != board.get_piece(new_square).color:
                    valid_moves.append(new_square)

        # En passant
        direction = [1, -1]
        for i in direction:
            if board.contains_piece(start_square + i):
                if (start_square % 8 == 0 and i == -1) or (start_square % 8 == 7 and i == 1):
                    continue
                neighbour_piece = board.get_piece(start_square + i)
                if self.eligible_to_en_passant(board, neighbour_piece):
                    valid_moves.append(start_square + piece.move + i)

        return valid_moves
    

    def _get_valid_RBQ_moves(self, board, piece, start_square, get_attacking_squares=False):
        """ Helper function for valid Rook, Bishop and Queen moves.
            Also used for getting all squares attacked by piece when "get_attacking_squares=True"
        """
        valid_moves = []
        board_squares = board.board
        append = valid_moves.append
        rays = SLIDING_RAYS[start_square]
        piece_color = piece.color
        for move in piece.moves:
            already_hit_a_piece = False

            for new_square in rays[move]:
                target_piece = board_squares[new_square]

                if target_piece is not None:
                    # After the first blocker, only look for pinned high-value pieces.
                    if already_hit_a_piece:
                        if target_piece.name == "King":
                            if target_piece.color != piece_color:
                                if piece_color == "white":
                                    self.black_king_is_pinned = True
                                else:
                                    self.white_king_is_pinned = True
                        elif target_piece.name == "Queen":
                            if target_piece.color != piece_color:
                                if piece_color == "white":
                                    self.black_queen_is_pinned = True
                                else:
                                    self.white_queen_is_pinned = True
                        break

                    if piece_color != target_piece.color:
                        append(new_square)
                    elif get_attacking_squares:
                        append(new_square)
                    already_hit_a_piece = True
                    continue

                if not already_hit_a_piece:
                    append(new_square)

        return valid_moves
    

    def _get_valid_knight_moves(self, board, piece, start_square, get_attacking_squares=False):
        """ Helper function for valid Knight moves.
            Also used for getting all squares attacked by piece when "get_attacking_squares=True"
        """
        valid_moves = []
        board_squares = board.board
        for new_square in KNIGHT_MOVES_BY_SQUARE[start_square]:
            target_piece = board_squares[new_square]

            if target_piece is not None:
                if piece.color != target_piece.color:
                    valid_moves.append(new_square)
                elif get_attacking_squares:
                    valid_moves.append(new_square)
            else:
                valid_moves.append(new_square)

        return valid_moves
    
    def _get_valid_king_moves(self, board, piece, start_square, color):
        valid_moves = []
        board_squares = board.board
        for new_square in KING_MOVES_BY_SQUARE[start_square]:
            # Check if new square contains a piece of same color
            target_piece = board_squares[new_square]
            if target_piece is not None:
                if piece.color == target_piece.color:
                    continue

            # Check if new square is under attack
            if color == "white":
                if new_square in self.attacked_squares_by_black:
                    continue
            else:
                if new_square in self.attacked_squares_by_white:
                    continue

            # Move is valid. Append square
            valid_moves.append(new_square)

        # Check if king can castle
        if piece.not_moved:
            if self.eligible_to_castle(board, piece, start_square, is_king_side=True):
                valid_moves.append(start_square + 2)
            if self.eligible_to_castle(board, piece, start_square, is_king_side=False):
                valid_moves.append(start_square - 2)

        return valid_moves
    

    def eligible_to_castle(self, board, piece, king_square, is_king_side):
        
        if piece.color == "white":
            if king_square != 4:
                return
            attacked_squares = self.attacked_squares_by_black
        else:
            if king_square != 60:
                return
            attacked_squares = self.attacked_squares_by_white

        if king_square in attacked_squares:
            return False

        direction = 1 if is_king_side else -1
        check_squares = [1, 2] if is_king_side else [1, 2, 3]

        for i in check_squares:
            if board.contains_piece(king_square + i * direction) or (king_square + i * direction in attacked_squares):
                return False

        rook_square = king_square + (3 if is_king_side else 4) * direction
        if not board.contains_piece(rook_square):
            return False
        if not board.get_piece(rook_square).not_moved:
            return False

        return True


    def eligible_to_en_passant(self, board, neighbour_piece):
        last_piece, last_move_original_square, last_move_to_square, is_capture = board.last_move
        return isinstance(last_piece, Pawn) and abs(last_move_to_square - last_move_original_square) == 16 and (last_piece == neighbour_piece)

