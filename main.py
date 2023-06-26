import pygame as pg
import timeit
import time as t
import threading

from constants import *
from board import ChessBoard
from game import ChessGame
from AI import ChessAI, handle_ai_move
from gui import draw_text, draw_stats, GUI
from utility import load_piece_images


piece_images = load_piece_images(width=100, height=100)

def main():
    FPS = 10
    pg.init()
    pg_quit = False
    window = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption('Triksheim Chess')
    
    clock = pg.time.Clock()
    font = pg.font.Font('freesansbold.ttf', 35)
   
    
    # Create a new chess board
    board = ChessBoard()

    # Game logic for chess
    game = ChessGame()
    tick_sec = threading.Thread(target=game.clock_tick)
    # Set up the pieces in their starting positions
    game.setup_posision_from_fen(board, STARTING_FEN)
    #game.setup_posision_from_fen(board, TEST_FEN)
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")
    game.evaluate_board(board)

    gui = GUI()
    
    black_move_times = [0]
    white_move_times = [0]
    
    start = False
    stop = False
    running = False
    ai_finding_move = False

    while not pg_quit:

        # Menu / Pause loop
        while not running and not pg_quit:

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg_quit = True
                    break

                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.pos[0] > (COLS*SQUARE_SIZE)+(2*BOARD_FRAME_WIDTH):
                        start = gui.mouse_click(event)
                            
                        
            if start and not game.game_ended:
            
                if gui.black_settings.radio_group_player[1].active:     # Black Player is CPU
                    for btn in gui.black_settings.radio_group_diff:
                        if btn.active:
                            if btn.text == "Easy":
                                ai_black = ChessAI(EASY_MODE["depth"], EASY_MODE["algo"], EASY_MODE["depth_change"])
                            elif btn.text == "Medium":
                                ai_black = ChessAI(MED_MODE["depth"], MED_MODE["algo"], MED_MODE["depth_change"])
                            else:
                                ai_black = ChessAI(HARD_MODE["depth"], HARD_MODE["algo"], HARD_MODE["depth_change"])
                else:
                    ai_black = False

                if gui.white_settings.radio_group_player[1].active:     # White Player is CPU 
                     for btn in gui.white_settings.radio_group_diff:
                        if btn.active:
                            if btn.text == "Easy":
                                ai_white = ChessAI(EASY_MODE["depth"], EASY_MODE["algo"], EASY_MODE["depth_change"], "white")
                            elif btn.text == "Medium":
                                ai_white = ChessAI(MED_MODE["depth"], MED_MODE["algo"], MED_MODE["depth_change"], "white")
                            else:
                                ai_white = ChessAI(HARD_MODE["depth"], HARD_MODE["algo"], HARD_MODE["depth_change"], "white")
                else:
                    ai_white = False

                gui.disable_settings()
                running = True
                stop = False 
                start = False
                    
            
            if game.checkmate:
                if game.turn == "white":
                    checked_square = board.white_king_square
                else:
                    checked_square = board.black_king_square
                board.draw(window, piece_images, game.selected_square, checked_square)
                draw_text(window, font, "Checkmate", 10*SQUARE_SIZE, TOP_PADDING)
            elif game.stalemate:
                draw_text(window, font, "Stalemate", 10*SQUARE_SIZE, TOP_PADDING)
                board.draw(window, piece_images)
            else:
                board.draw(window, piece_images)

            draw_stats(window, game, font, white_move_times, black_move_times) 
            gui.draw(window)

            pg.display.flip()
            clock.tick(10)





        # Main gameloop (started)
        while running:

            if game.selected_square is None:
                board.draw(window, piece_images)
                draw_stats(window, game, font, white_move_times, black_move_times)

            if not tick_sec.is_alive():
                tick_sec = threading.Thread(target=game.clock_tick)
                tick_sec.start()

            if game.white_clock <= 0 or game.black_clock <= 0:
                running = False
            
            # if game.move_count == 6:
            #     total_ai_time = sum(black_move_times)
            #     print(f'AI TIME: {total_ai_time:.2f}')

            # AI move
            if ai_black and game.turn == ai_black.color and not ai_finding_move:
                ai_finding_move = True
                thread = threading.Thread(target=handle_ai_move, args=(ai_black, game, board, ai_black.color, ai_black.algo, ai_black.depth, black_move_times))
                thread.start()

            # AI2 move
            elif ai_white and game.turn == ai_white.color and not ai_finding_move:  
                ai_finding_move = True
                thread = threading.Thread(target=handle_ai_move, args=(ai_white, game, board, ai_white.color, ai_white.algo, ai_white.depth, white_move_times))
                thread.start()
        
            # Check if AI move is complete:
            if ai_finding_move and not thread.is_alive():
                ai_finding_move = False
                ai_move = game.ai_move
                if ai_move:
                    game.execute_move(board, ai_move[0], ai_move[1])
                    game.update_gamestate(board)
                    board.draw(window, piece_images)
                    draw_stats(window, game, font, white_move_times, black_move_times)
                    if game.turn == "white":
                        game.white_move_clock = 0
                    else:
                        game.black_move_clock = 0
                    start_time_player = timeit.default_timer()
                else:
                    running = False


            # Check if player can move
            if not ai_finding_move:
                if game.no_valid_moves(board):
                    running = False


            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg_quit = True
                    running = False


                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.pos[0] > (COLS*SQUARE_SIZE)+(2*BOARD_FRAME_WIDTH):
                        stop = gui.mouse_click(event)

                        if stop:
                            gui.enable_settings()
                            running = False
                            



                if not ai_finding_move:

                    # Player move, selecting piece
                    if event.type == pg.MOUSEBUTTONDOWN and game.selected_square is None:
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
                    elif event.type == pg.MOUSEBUTTONUP and game.selected_square is not None:
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
                            if game.turn == "white":
                                game.white_move_clock = 0
                            else:
                                game.black_move_clock = 0


                            if not ai_black and not ai_white:
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
                

            if not running and not stop and not pg_quit:
                
                game.game_ended = True
                if game.white_clock <= 0 or game.black_clock <= 0:
                    font = pg.font.Font('freesansbold.ttf', 25)
                    if game.white_clock <= 0:
                        draw_text(window, font, "White lost on time", 10*SQUARE_SIZE, TOP_PADDING)
                    else:
                        draw_text(window, font, "Black lost on time", 10*SQUARE_SIZE, TOP_PADDING)
                
                elif game.king_in_check(board):
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


            gui.draw(window)
            pg.display.flip()
            clock.tick(FPS)

        


    pg.quit()

if __name__ == "__main__":
    main()