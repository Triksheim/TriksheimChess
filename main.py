import pygame as pg
from constants import *
from board import ChessBoard
from game import ChessGame
from AI import ChessAI
import timeit


def draw_check(window, font):
    text = font.render("Check", 0, (WHITE_COLOR))
    window.blit(text, (10*SQUARE_SIZE, TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))

def draw_checkmate(window, font):
    text = font.render("Checkmate", 0, (WHITE_COLOR))
    window.blit(text, (10*SQUARE_SIZE, TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))

def draw_game_status(window, font, status):
    text = font.render(status, 0, (WHITE_COLOR))
    window.blit(text, (10*SQUARE_SIZE, TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))

def draw_eval(window, font, game, ai_eval):
    text = font.render(f'AI eval: {ai_eval}', 0, (WHITE_COLOR))
    window.blit(text, (SQUARE_SIZE/2, TOP_PADDING/2 + 0*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    # text = font.render(f'White eval: {game.white_eval}', 0, (WHITE_COLOR))
    # window.blit(text, (SQUARE_SIZE/2, TOP_PADDING/2 + 9*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def main():
    pg.init()
    window = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()
    font = pg.font.Font('freesansbold.ttf', 25)
    running = True

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
    ai = ChessAI()
    algorithm = ["random", "minimax", "minimax_pruning"]
    
    engine = True
    engine_color = "black"
    engine_depth = 3
    engine_dynamic_depth_change = 0

    engine2 = True
    engine2_color = "white"
    engine2_depth = 2
    engine2_dynamic_depth_change = 0
    
    white_move_times = [1]
    black_move_times = [1]

     # Draws the board and pieces
    board.draw(window)
    eval = "n/a"
    draw_eval(window, font, game, eval) 
    pg.display.flip()

    # Main gameloop
    while running:

        if game.move_count == 6:
            total_ai_time = sum(black_move_times)
            print(f'AI TIME: {total_ai_time:.2f}')

        # AI move
        if engine and game.turn == engine_color:
            last_generation_times = black_move_times[-3:]
            if (sum(last_generation_times) / len(last_generation_times)) < 3:
                engine_depth += engine_dynamic_depth_change
            elif (sum(last_generation_times) / len(last_generation_times)) > 15:
                if engine_depth > 2:
                    engine_depth -= engine_dynamic_depth_change

            start_time = timeit.default_timer()
            
            result = ai.generate_move(game, board, algorithm[2], engine_depth, engine_color)
            selected_square, new_square, eval = result[0][0], result[0][1], result[1]

            end_time = timeit.default_timer()
            time = end_time - start_time
            black_move_times.append(time)
            print(f'{engine_color}: depth:{engine_depth} time:{time:.2f}s')

            if new_square is None:
                game.game_ended = True
                running = False
                if game.turn == "white":
                    board.draw_attacked_squares(window, game.attacked_squares_by_black)
                else:
                    board.draw_attacked_squares(window, game.attacked_squares_by_white)    
            else:
                game.execute_move(board, selected_square, new_square)
                game.update_attacked_squares(board)
                game.swap_turn()
                game.update_attacked_squares(board)
                game.evaluate_board(board)
                board.draw(window)



        elif engine2 and game.turn == engine2_color:
            last_generation_times = white_move_times[-3:]
            if (sum(last_generation_times) / len(last_generation_times)) < 3:
                engine2_depth += engine2_dynamic_depth_change
            elif (sum(last_generation_times) / len(last_generation_times)) > 15:
                if engine2_depth > 2:
                    engine2_depth -= engine2_dynamic_depth_change
                    
            start_time = timeit.default_timer()
            
            result = ai.generate_move(game, board, algorithm[2], engine2_depth, engine2_color)
            selected_square, new_square, eval = result[0][0], result[0][1], result[1]

            end_time = timeit.default_timer()
            time = end_time - start_time
            white_move_times.append(time)
            print(f'{engine2_color}: depth:{engine2_depth} time:{time:.2f}s')

            if new_square is None:
                game.game_ended = True
                running = False
                if game.turn == "white":
                    board.draw_attacked_squares(window, game.attacked_squares_by_black)
                else:
                    board.draw_attacked_squares(window, game.attacked_squares_by_white)    
            else:
                game.execute_move(board, selected_square, new_square)
                game.update_attacked_squares(board)
                game.swap_turn()
                game.update_attacked_squares(board)
                game.evaluate_board(board)
                board.draw(window)


        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            elif event.type == pg.MOUSEBUTTONDOWN:
                if game.selected_square is None:
                    start_time = timeit.default_timer()
                    square = board.select_square_by_mouse_click(event)
                    if board.contains_piece(square):
                        if board.get_piece(square).color == game.turn:
                            valid_moves = game.get_valid_moves(board, square)
                            board.draw(window)
                            
                            if valid_moves:
                                board.draw_valid_moves(window, valid_moves)
                                # if game.turn == "white":
                                #     board.draw_attacked_squares(window, game.attacked_squares_by_black)
                                # else:
                                #     board.draw_attacked_squares(window, game.attacked_squares_by_white)
                                game.selected_square = square
                    end_time = timeit.default_timer()  
                
                elif game.selected_square >= 0:
                    new_square = board.select_square_by_mouse_click(event)
                    if new_square in valid_moves:
                        game.execute_move(board, None, new_square)
                        game.swap_turn()
                    game.selected_square = None
                    game.update_attacked_squares(board)
                    game.evaluate_board(board)
                    board.draw(window)
                    valid_moves = None

        if game.no_valid_moves(board):
            if game.king_in_check(board):
                game.checkmate = True
                draw_game_status(window, font, "Checkmate")
            else:
                game.stalemate = True
                draw_game_status(window, font, "Stalemate")

        if game.king_in_check(board):
            if game.turn == "white":
                checked_square = board.white_king_square
            else:
                checked_square = board.black_king_square
            board.draw(window, checked_square)

            if game.checkmate:
                draw_game_status(window, font, "Checkmate")
            else:
                draw_game_status(window, font, "Check")
            try:
                if valid_moves:
                    board.draw_valid_moves(window, valid_moves)
            except:
                pass 

        draw_eval(window, font, game, eval)               
        pg.display.flip()
        clock.tick(10)


    # Temp end loop
    while game.game_ended:

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                break

        pg.display.flip()
        clock.tick(10)

    pg.quit()

if __name__ == "__main__":
    main()