from pieces import *
from constants import *
import pygame as pg
import math


class ChessBoard:
    def __init__(self):
        self.board = [None for _ in range(64)]
        self.int_board = [None for _ in range(64)]
        self.white_king_square = 4
        self.black_king_square = 60
        self.last_move = (None, None, None) # tuple with (Piece, original_sqaure, new_square)
        
        
    def get(self):
        return self.board

    def get_squares_with_piece(self, color):
        squares_and_pieces = []
        for square, piece in enumerate(self.board):
            if piece:
                if piece.color == color:
                    squares_and_pieces.append((square, piece))
        return squares_and_pieces

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


    def draw(self, window, pieces, selected_square=None, checked_square=None):
        window.fill(DARK_GRAY_COLOR)
        self.draw_board(window)
        self.draw_last_move(window)
        if checked_square is not None:
            self.draw_checked_square(window, checked_square)
        self.draw_pieces(window, pieces, selected_square)
        

    def draw_board(self, window):
        for row in range(ROWS):
            for col in range (COLS):
                if row % 2 == 0:
                    if col % 2 == 0:
                        square_color = LIGHT_SQUARE_COLOR
                    else:
                        square_color = DARK_SQUARE_COLOR   
                else: # Alternate row starting color
                    if col % 2 == 0:
                        square_color = DARK_SQUARE_COLOR  
                    else:
                        square_color = LIGHT_SQUARE_COLOR    
                pg.draw.rect(window, square_color, (row*SQUARE_SIZE + LEFT_SIDE_PADDING, col*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))
        self.draw_board_frame(window)

    def draw_board_frame(self, window):
        font = pg.font.Font('freesansbold.ttf', 40)
        frame_color = TEST_COLOR
        char_color = WHITE_COLOR
        chars = "ABCDEFGH"
        pg.draw.rect(window, frame_color, (0, TOP_PADDING-BOARD_FRAME_WIDTH,  COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2), BOARD_FRAME_WIDTH )) #top
        pg.draw.rect(window, frame_color, (0, ROWS*SQUARE_SIZE + (TOP_PADDING),  COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2), BOARD_FRAME_WIDTH )) #bot
        pg.draw.rect(window, frame_color, (0, TOP_PADDING-BOARD_FRAME_WIDTH,   BOARD_FRAME_WIDTH, COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2) )) #left
        pg.draw.rect(window, frame_color, (COLS*SQUARE_SIZE + BOARD_FRAME_WIDTH, TOP_PADDING-BOARD_FRAME_WIDTH,   BOARD_FRAME_WIDTH, COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2) )) #right
        for i, char in enumerate(chars):
            char_text = font.render(char, 1 , char_color)
            window.blit(char_text, ((i+1)*SQUARE_SIZE - 15 , ROWS*SQUARE_SIZE + TOP_PADDING + 10, SQUARE_SIZE, SQUARE_SIZE))
            num = str(i+1)
            num_text = font.render(num, 1 , char_color)
            window.blit(num_text, ((BOARD_FRAME_WIDTH/2) - 15 , (8 - (i+1))*SQUARE_SIZE + TOP_PADDING + (BOARD_FRAME_WIDTH/2) + 5, SQUARE_SIZE, SQUARE_SIZE))


            

    def draw_pieces(self, window, piece_images, selected_square):
        for square, piece in enumerate(self.board):
            if piece is not None and square != selected_square:
                row = square // 8
                col = square % 8
                filename = f'{piece.color}_{piece.name.lower()}.png'
                image = piece_images[filename]
                window.blit(image, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING))
        

    def draw_selected_piece(self, window, piece_images, selected_square, mouse_cords):
        piece = self.get_piece(selected_square)
        x_cor = mouse_cords[0]
        y_cor = mouse_cords[1]
        #print(x_cor, y_cor)
        filename = f'{piece.color}_{piece.name.lower()}.png'
        image = piece_images[filename]
        window.blit(image, (x_cor-(SQUARE_SIZE/2), y_cor-(SQUARE_SIZE/2)))
        


    def draw_pieces_old(self, window):
        font = pg.font.Font('freesansbold.ttf', 25)
        for i, square in enumerate(self.board):
            if square is not None:
                row =  i // 8
                col = i % 8
                if square.color == 'white':
                    color = WHITE_PIECE_COLOR
                else:
                    color = BLACK_PIECE_COLOR
                text = font.render(square.name, 0, color)
                window.blit(text, (col*SQUARE_SIZE + 10 + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING + 40, SQUARE_SIZE, SQUARE_SIZE))
    

    def draw_last_move(self, window):
        if self.last_move[2] or self.last_move[2] == 0:
            old_square = self.last_move[1]
            new_square = self.last_move[2]
            row =  new_square // 8
            col = new_square % 8
            pg.draw.rect(window, GRAY_COLOR, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))
            row =  old_square // 8
            col = old_square % 8
            pg.draw.rect(window, LIGHT_GRAY_COLOR, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))


    def draw_checked_square(self, window, square):
            row =  square // 8
            col = square % 8
            pg.draw.rect(window, CHECK_COLOR, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))


    def draw_valid_moves(self, window, moves):
        for move in moves:
            row = move // ROWS
            col = move % COLS
            pg.draw.circle(window, GRAY_COLOR, ((col*SQUARE_SIZE + (SQUARE_SIZE/2)) + LEFT_SIDE_PADDING, ((ROWS - row - 1)*SQUARE_SIZE + (SQUARE_SIZE/2)) + TOP_PADDING), 5)


    def draw_attacked_squares(self, window, attacked_squares):
        for square in attacked_squares:
            row = square // ROWS
            col = square % COLS
            pg.draw.circle(window, RED_COLOR, ((col*SQUARE_SIZE + (SQUARE_SIZE/2)) + LEFT_SIDE_PADDING, ((ROWS - row - 1)*SQUARE_SIZE + (SQUARE_SIZE/2)) + TOP_PADDING), 2)



   