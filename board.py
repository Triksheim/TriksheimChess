from pieces import *
from constants import *
import math


class ChessBoard:
    def __init__(self):
        self.board = [None for _ in range(64)]
        self.int_board = [None for _ in range(64)]
        self.white_king_square = 4
        self.black_king_square = 60
        self.last_move = (None, None, None) # tuple with (Piece, original_sqaure, new_square)
        self.move_log = []
        self.board_state_log = [None]
        
        
    def get(self):
        return self.board

    def get_squares_with_piece(self, color):
        squares_and_pieces = []
        for square, piece in enumerate(self.board):
            if piece:
                if piece.color == color:
                    squares_and_pieces.append((square, piece))
        return squares_and_pieces

    def get_squares_for_color(self, color):
        squares = set()
        for square, piece in enumerate(self.board):
            if piece and piece.color == color:
                squares.add(square)
        return squares


    def add_piece(self, piece, square):
        """ Place a piece on the board at the given square index """
        self.board[square] = piece
        self.int_board[square] = piece.number
        if isinstance(piece, King):
            if piece.color == "white":
                self.white_king_square = square
            else:
                self.black_king_square = square

    def contains_piece(self, square):
        if square is not None:
            if self.board[square] is not None:
                return True
        return False

    def get_piece(self, square):
        return self.board[square]

    def move_piece(self, original_square, new_square):
        """ Move a piece to a new square on the board """
        self.last_move = (self.board[original_square], original_square, new_square)
        self.board[new_square] = self.board[original_square]

        self.int_board[new_square] = self.board[original_square].number
        self.int_board[original_square] = None
        self.board[original_square] = None
        self.board[new_square].not_moved = False

        self.move_log.append(self.last_move)
        self.board_state_log.append(hash(tuple(self.int_board)))
        

    def move_king(self, original_square, new_square, castle=False):
        """ Handle king-specific move """
        # Move rook if castling
        if castle:
            self._move_rook_in_castle(original_square, castle)

        self.move_piece(original_square, new_square)
        # update white King
        if original_square == self.white_king_square:
            self.white_king_square = new_square
        # update black King
        elif original_square == self.black_king_square:
            self.black_king_square = new_square


    def _move_rook_in_castle(self, king_square, side):
        """ Check if king move is castle and moves rook if it is """
        if side == "kingside":
            self.move_piece(king_square+3, king_square+1)
        else:
            self.move_piece(king_square-4, king_square-1)


    def move_en_passant(self, original_square, new_square):
        pawn_to_take = self.last_move[2]
        self.board[pawn_to_take] = None
        self.move_piece(original_square, new_square)
        

    def move_pawn_promote(self, original_square, new_square, color):
        self.move_piece(original_square, new_square)
        self.add_piece(Queen(color), new_square)


    def select_square_by_mouse_click(self, event):
        """Returns square index if click was on the board"""
        xcor = event.pos[0]
        ycor = event.pos[1]
        col = int(math.floor((xcor - LEFT_SIDE_PADDING) / SQUARE_SIZE))
        row = 7 - int(math.floor((ycor - TOP_PADDING) / SQUARE_SIZE))
        if 0 <= col <= 7 and 0 <= row <= 7:
            square_idx = row*8 + col
            #print(square_idx)
            return square_idx

