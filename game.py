from constants import *
from pieces import *
from pieces_table import *
from copy import deepcopy
import time as t



class ChessGame():
    def __init__(self, white_clock=900, black_clock=900, increment=10):
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
        self.white_king_has_moved = False
        self.black_king_has_moved = False
        self.white_king_is_pinned = False
        self.black_king_is_pinned = False
        self.white_queen_is_pinned = False
        self.black_queen_is_pinned = False
        self.white_rook_has_moved = (False, False)  # Queenside and Kingside
        self.black_rook_has_moved = (False, False)
        self.white_eval = 0
        self.black_eval = 0
        self.attacked_squares_by_white = []
        self.attacked_squares_by_black = []
        self.black_move_times = [0]
        self.white_move_times = [0]
        
    def clock_tick(self):
        t.sleep(1)
        if self.turn == "white":
            self.white_clock -= 1
            self.white_move_clock += 1
        else:
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


    def evaluate_board(self, board):
        white_eval, white_count = self.evaluate_color(board, "white")
        black_eval, black_count = self.evaluate_color(board, "black")
        self.white_eval = white_eval
        self.black_eval = black_eval
        self.piece_count = white_count + black_count
        
            
    def evaluate_color(self, board, color):
        evaluation = 0
        
        if color == "white":
            evaluation += (len(self.attacked_squares_by_white) * 2) # pts per attacked square
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
            evaluation += (len(self.attacked_squares_by_black) * 2)
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

        pieces = board.get_squares_with_piece(color)
        for square, piece in pieces:
            evaluation += piece.value

            if color == "white":

                if isinstance(piece, King):
                    if self.piece_count > 15:
                        evaluation += king_early_table[63-square]
                    else:
                        evaluation += king_late_table[63-square]
                    continue

                elif isinstance(piece, Rook):
                    evaluation += rook_table[63-square]
                elif isinstance(piece, Knight):
                    evaluation += knight_table[63-square]
                elif isinstance(piece, Bishop):
                    evaluation += bishop_table[63-square]
                elif isinstance(piece, Queen):
                    evaluation += queen_table[63-square]
                elif isinstance(piece, Pawn):
                    evaluation += pawn_table[63-square]
                
                def_count = self.attacked_squares_by_white.count(square)
                evaluation += (def_count * 3)


            else:
                if isinstance(piece, King):
                    if self.piece_count > 15:
                        evaluation += king_early_table[square]
                    else:
                        evaluation += king_late_table[square]
                    continue

                elif isinstance(piece, Rook):
                    evaluation += rook_table[square]
                elif isinstance(piece, Knight):
                    evaluation += knight_table[square]
                elif isinstance(piece, Bishop):
                    evaluation += bishop_table[square]
                elif isinstance(piece, Queen):
                    evaluation += queen_table[square]
                elif isinstance(piece, Pawn):
                    evaluation += pawn_table[square]
                
                def_count = self.attacked_squares_by_black.count(square)
                evaluation += (def_count * 3)

        return evaluation, len(pieces)
    
    def execute_move(self, board, original_square, new_square=None):
        self.move_count += 1
        if  original_square is None:
            original_square = self.selected_square
        
        if isinstance(board.board[original_square], King):
            if original_square - new_square == -2: 
                board.move_king(original_square, new_square, castle="kingside")
            elif original_square - new_square == 2: 
                board.move_king(original_square, new_square, castle="queenside")
            else:
                board.move_king(original_square, new_square)

        elif isinstance(board.board[original_square], Pawn):
            if new_square >= 56:
                board.move_pawn_promote(original_square, new_square, "white")
            elif new_square <= 7:
                board.move_pawn_promote(original_square, new_square, "black")
            elif isinstance(board.last_move[0], Pawn):
                if (abs(original_square - new_square) == 7 or abs(original_square - new_square) == 9) \
                and not board.contains_piece(new_square):
                    board.move_en_passant(original_square, new_square)
                else:
                    board.move_piece(original_square, new_square)
            else:
                board.move_piece(original_square, new_square)
        else:
            board.move_piece(original_square, new_square)
        
    def update_gamestate(self, board):
        self.update_attacked_squares(board)
        self.swap_turn()
        self.update_attacked_squares(board)
        self.evaluate_board(board)
        
            

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
        for square, piece in enumerate(board.get()):
            if piece is not None:
                if piece.color != color:
                    squares = self._get_attacked_squares(board, piece, square)
                    if squares is not None:
                        attacked_squares.extend(squares)

        # if color == "white":
        #     self.attacked_squares_by_black = set(attacked_squares)
        # else:
        #     self.attacked_squares_by_white = set(attacked_squares)

        if color == "white":
            self.attacked_squares_by_black = attacked_squares
        else:
            self.attacked_squares_by_white = attacked_squares

        


    def _get_attacked_squares(self, board, piece, square):
        attacked_squares = []
        if piece.name == "Pawn":
            attacked_squares.extend(self._get_attacked_pawn_squares(piece, square))  
        elif piece.name == "Rook" or piece.name == "Bishop" or piece.name == "Queen":
            attacked_squares.extend(self._get_valid_RBQ_moves(board, piece, square, get_attacking_squares=True))
        elif piece.name == "Knight":
           attacked_squares.extend(self._get_valid_knight_moves(board, piece, square, get_attacking_squares=True))
        elif piece.name == "King":
            attacked_squares.extend(self._get_attacked_king_squares( piece, square))

        return attacked_squares


    def _get_attacked_pawn_squares(self, piece, start_square):
        attacked_squares = []
        for move in piece.attack_moves:
            new_square = start_square + move
            if self._is_wraparound_diagonal_move(start_square, move):
                continue
            attacked_squares.append(new_square)

        return attacked_squares


    def _get_attacked_king_squares(self, piece, start_square):
        attacked_squares = []
        for move in piece.moves:
            new_square = start_square + move
            if self._is_invalid_board_square(new_square):
                continue
            if self._is_wraparound_sliding_move(start_square, new_square, move):
                continue
            if self._is_wraparound_diagonal_move(start_square, move):
                continue
            attacked_squares.append(new_square)

        return attacked_squares


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
            # valid_moves might be psudo legal and have to perform extra test on them
            valid_valid_moves = []
            for move in valid_moves:
                temp_board = deepcopy(board)
                temp_game = deepcopy(self)
                temp_game.execute_move(temp_board, start_square, move)
                temp_game.update_attacked_squares(temp_board)
                if not temp_game.king_in_check(temp_board):
                    valid_valid_moves.append(move)
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
        for move in piece.attack_moves:  
            if self._is_wraparound_diagonal_move(start_square, move):
                continue
            new_square = start_square + move
            if self._is_invalid_board_square(new_square):
                continue
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
        for move in piece.moves:
                new_square = start_square + move
                moving = True
                already_hit_a_piece = False
                
                while moving:
                    
                    if self._is_invalid_board_square(new_square):
                        break
                    if self._is_wraparound_sliding_move(start_square, new_square, move):
                        break
                    if self._is_wraparound_diagonal_move(start_square, move):
                        break
                    if self._is_wraparound_diagonal_move(new_square, move):
                        moving = False

                    # Check if new square contains a piece
                    if board.contains_piece(new_square):
                        
                        # If a piece has already been hit the check for valid moves is done, 
                        # but we keep looking for the next piece i the same direction to determine if a king is pinned.
                        if already_hit_a_piece:
                            if isinstance(board.get_piece(new_square), King):
                                if board.get_piece(new_square).color != piece.color:
                                    if piece.color == "white":
                                        self.black_king_is_pinned = True
                                    else:
                                        self.white_king_is_pinned = True
                            elif isinstance(board.get_piece(new_square), Queen):
                                if board.get_piece(new_square).color != piece.color:
                                    if piece.color == "white":
                                        self.black_queen_is_pinned = True
                                    else:
                                        self.white_queen_is_pinned = True
                            break

                        # Append valid move if piece is different color (take piece)
                        elif piece.color != board.get_piece(new_square).color:
                            valid_moves.append(new_square)
                        elif get_attacking_squares:
                            valid_moves.append(new_square)
                        already_hit_a_piece = True

                        new_square = new_square + move
                        # continue movement in same direction to check for pinned king
                        continue
                    
                    # Square is empty and is not blocked by a piece. Append valid move
                    if not already_hit_a_piece:
                        valid_moves.append(new_square)

                    new_square = new_square + move

        return valid_moves
    

    def _get_valid_knight_moves(self, board, piece, start_square, get_attacking_squares=False):
        """ Helper function for valid Knight moves.
            Also used for getting all squares attacked by piece when "get_attacking_squares=True"
        """
        valid_moves = []
        for move in piece.moves:
            new_square = start_square + move

            if self._is_invalid_board_square(new_square):
                continue
            if self._is_wraparound_knight_move(start_square, new_square):
                continue

            if board.contains_piece(new_square):
                if piece.color != board.get_piece(new_square).color:
                    valid_moves.append(new_square)
                elif get_attacking_squares:
                    valid_moves.append(new_square)
            else:
                valid_moves.append(new_square)

        return valid_moves
    
    def _get_valid_king_moves(self, board, piece, start_square, color):
        valid_moves = []
        for move in piece.moves:
                new_square = start_square + move
                
                if self._is_invalid_board_square(new_square):
                    continue
                if self._is_wraparound_sliding_move(start_square, new_square, move):
                    continue
                if self._is_wraparound_diagonal_move(start_square, move):
                    continue
                
                # Check if new square contains a piece of same color
                if board.contains_piece(new_square):
                    if piece.color == board.get_piece(new_square).color:
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
        last_piece, last_move_original_square, last_move_to_square = board.last_move
        return isinstance(last_piece, Pawn) and abs(last_move_to_square - last_move_original_square) == 16 and (last_piece == neighbour_piece)

