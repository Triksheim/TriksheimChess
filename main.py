import pygame as pg
import timeit
import time as t

from constants import *
from board import ChessBoard
from game import ChessGame
from AI import ChessAI, handle_ai_move
from gui import draw_text, draw_stats
from utility import load_piece_images

piece_images = load_piece_images(width=100, height=100)

def main():
    FPS = 10
    pg.init()
    pg_quit = False
    window = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()
    font = pg.font.Font('freesansbold.ttf', 30)
    
    # Create a new chess board
    board = ChessBoard()
    # Game logic for chess
    game = ChessGame()
    # Set up the pieces in their starting positions
    game.setup_posision_from_fen(board, STARTING_FEN)
    #game.setup_posision_from_fen(board, TEST_FEN)
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")
    game.evaluate_board(board)

    # Chess AI
    algorithm = ["random", "minimax"]

    ai = ChessAI()
    #ai = False             # Uncomment to deactivate
    ai_color = "black"
    ai_algo = algorithm[1]
    ai_depth = 3
    ai_dynamic_depth_change = 0
    black_move_times = [0]

    ai2 = ChessAI()
    ai2 = False             # Uncomment to deactivate
    ai2_color = "white"
    ai2_algo = algorithm[1]
    ai2_depth = 2
    ai2_dynamic_depth_change = 0
    white_move_times = [0]
    

     # Draws the board and pieces
    board.draw(window, piece_images)
    draw_stats(window, game, font, white_move_times, black_move_times) 
    pg.display.flip()


    running = not game.game_ended

    # Main gameloop
    while running:

        # if game.move_count == 6:
        #     total_ai_time = sum(black_move_times)
        #     print(f'AI TIME: {total_ai_time:.2f}')

        # AI move
        if ai and game.turn == ai_color:
            running = handle_ai_move(ai, game, board, ai_color, ai_algo, ai_depth, black_move_times)
            board.draw(window, piece_images)
            draw_stats(window, game, font, white_move_times, black_move_times)

            if not ai2:
                start_time_player = timeit.default_timer()


        # AI2 move
        elif ai2 and game.turn == ai2_color:    
            running = handle_ai_move(ai2, game, board, ai2_color, ai2_algo, ai2_depth, white_move_times)
            board.draw(window, piece_images)
            draw_stats(window, game, font, white_move_times, black_move_times)

            if not ai:
                start_time_player = timeit.default_timer()

        # Check if player can move
        else:
            if game.no_valid_moves(board):
                running = False


        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg_quit = True
                running = False

            # Player move, selecting piece
            elif event.type == pg.MOUSEBUTTONDOWN:
                if game.selected_square is None:
                    square = board.select_square_by_mouse_click(event)
                    if board.contains_piece(square):
                        if board.get_piece(square).color == game.turn:
                            valid_moves = game.get_valid_moves(board, square)
                            
                            if valid_moves:
                                board.draw(window, piece_images, square)
                                board.draw_valid_moves(window, valid_moves)
                                game.selected_square = square
                              
            # Player move, dropping selected piece
            elif game.selected_square is not None and event.type == pg.MOUSEBUTTONUP:
                new_square = board.select_square_by_mouse_click(event)
                if new_square in valid_moves:
                    game.execute_move(board, None, new_square)
                    game.update_attacked_squares(board)
                    end_time = timeit.default_timer()
                    try:
                        time = end_time - start_time_player
                    except:
                        time = 0 
                    if game.turn == "white":
                        white_move_times.append(time)
                    else:
                        black_move_times.append(time)
                    game.swap_turn()

                    if not ai and not ai2:
                        start_time_player = timeit.default_timer()
                game.selected_square = None
                game.update_attacked_squares(board)
                game.evaluate_board(board)

                if game.king_in_check(board):
                        if game.turn == "white":
                            checked_square = board.white_king_square
                        else:
                            checked_square = board.black_king_square
                else:
                    checked_square = None

                board.draw(window, piece_images, checked_square)
                draw_stats(window, game, font, white_move_times, black_move_times)
                valid_moves = None
                FPS = 10
                

            # Drag selected piece
            if game.selected_square is not None:
                FPS = 60
                if event.type == pg.MOUSEMOTION or event.type == pg.MOUSEBUTTONDOWN:
                    mouse_cords = (event.pos[0], event.pos[1])
                    if game.king_in_check(board):
                        if game.turn == "white":
                            checked_square = board.white_king_square
                        else:
                            checked_square = board.black_king_square
                    else:
                        checked_square = None
                    board.draw(window, piece_images, game.selected_square, checked_square)
                    draw_stats(window, game, font, white_move_times, black_move_times)
                    board.draw_selected_piece(window, piece_images, game.selected_square, mouse_cords)
                    board.draw_valid_moves(window, valid_moves)


        if running and game.king_in_check(board) and game.selected_square is None:
            if game.turn == "white":
                checked_square = board.white_king_square
            else:
                checked_square = board.black_king_square
            board.draw(window, piece_images, game.selected_square, checked_square)
            draw_stats(window, game, font, white_move_times, black_move_times)
            draw_text(window, font, "Check", 10*SQUARE_SIZE, TOP_PADDING)
            

        if not running and not pg_quit:
            game.game_ended = True
            if game.king_in_check(board):
                game.checkmate = True
                if game.turn == "white":
                    checked_square = board.white_king_square
                else:
                    checked_square = board.black_king_square
                board.draw(window, piece_images, game.selected_square, checked_square)
                draw_stats(window, game, font, white_move_times, black_move_times)
                draw_text(window, font, "Checkmate", 10*SQUARE_SIZE, TOP_PADDING)
            else:
                game.stalemate = True
                draw_text(window, font, "Stalemate", 10*SQUARE_SIZE, TOP_PADDING)

        pg.display.flip()
        clock.tick(FPS)

       


    # Temp end loop
    while game.game_ended and not pg_quit:

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg_quit = True
                break

        pg.display.flip()
        clock.tick(10)

    pg.quit()

if __name__ == "__main__":
    main()