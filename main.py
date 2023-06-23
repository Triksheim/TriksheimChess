import pygame as pg
from constants import *
from board import ChessBoard
from game import ChessGame
from AI import ChessAI
import timeit
import time as t



def draw_game_status(window, font, status):
    text = font.render(status, 0, (WHITE_COLOR))
    window.blit(text, (10*SQUARE_SIZE, TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))

def draw_eval(window, font, game, ai_eval):
    # text = font.render(f'AI eval: {ai_eval}', 0, (WHITE_COLOR))
    # window.blit(text, (SQUARE_SIZE/2, TOP_PADDING/2 + 0*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    text = font.render(f'White eval: {game.white_eval}', 0, (WHITE_COLOR))
    window.blit(text, (SQUARE_SIZE/2, TOP_PADDING/2 + 9*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    text = font.render(f'Black eval: {game.black_eval}', 0, (WHITE_COLOR))
    window.blit(text, (SQUARE_SIZE/2, TOP_PADDING/2 + 0*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def draw_move_time(window, font, color, time):
    if color == "black":
        text = font.render(f'{time:.2f}s', 0, (WHITE_COLOR))
        window.blit(text, (4*SQUARE_SIZE, TOP_PADDING/2 + 0*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    else:
        text = font.render(f'{time:.2f}s', 0, (WHITE_COLOR))
        window.blit(text, (4*SQUARE_SIZE, TOP_PADDING/2 + 9*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def transform_image(image, width, height):
    return pg.transform.scale(image, (width, height))

def load_image(filename):
    return pg.image.load(filename)


def main():
    FPS = 10
    pg.init()
    window = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()
    font = pg.font.Font('freesansbold.ttf', 25)
    
    # load piece img
    width = 100
    height = 100
    piece_names = ['king', 'queen', 'bishop', 'knight', 'rook', 'pawn']
    filenames = []
    for i in range(6):
        for j in range(2):
            color = 'white' if j == 0 else 'black'
            filenames.append((f'{color}_{piece_names[i]}.png'))
    piece_images = {}
    for filename in filenames:
        img = load_image(f'image\{filename}')
        piece_images[filename] = transform_image(img, width, height)




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
    ai = False             # Uncomment to deactivate
    ai_color = "black"
    ai_algo = algorithm[1]
    ai_depth = 3
    ai_dynamic_depth_change = 0
    black_move_times = [5,5,0]

    ai2 = ChessAI()
    ai2 = False             # Uncomment to deactivate
    ai2_color = "white"
    ai2_algo = algorithm[1]
    ai2_depth = 1
    ai2_dynamic_depth_change = 0
    white_move_times = [5,5,0]
    
    max_move_time = 30
    min_move_time = 1

    

     # Draws the board and pieces
    board.draw(window, piece_images)
    eval = "n/a"
    draw_eval(window, font, game, eval) 
    pg.display.flip()

    start_time = timeit.default_timer()
    running = True

    # Main gameloop
    while running:

        # if game.move_count == 6:
        #     total_ai_time = sum(black_move_times)
        #     print(f'AI TIME: {total_ai_time:.2f}')

        # AI move
        if ai and game.turn == ai_color:
            last_generation_times = black_move_times[-3:]
            if (sum(last_generation_times) / len(last_generation_times)) < min_move_time:
                ai_depth += ai_dynamic_depth_change
            elif (sum(last_generation_times) / len(last_generation_times)) > max_move_time:
                if ai_depth > 4:
                    ai_depth -= ai_dynamic_depth_change

            start_time = timeit.default_timer()
            
            result = ai.generate_move(game, board, ai_algo, ai_depth, ai_color)
            selected_square, new_square, eval = result[0][0], result[0][1], result[1]

            end_time = timeit.default_timer()
            time = end_time - start_time
            black_move_times.append(time)
            if time < 0.5:
                t.sleep(0.5)
            print(f'{ai_color}: depth:{ai_depth} time:{time:.2f}s')

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
                board.draw(window, piece_images)
                if not ai2:
                    start_time = timeit.default_timer()


        # AI2 move
        elif ai2 and game.turn == ai2_color:
            last_generation_times = white_move_times[-3:]
            if (sum(last_generation_times) / len(last_generation_times)) < min_move_time:
                ai2_depth += ai2_dynamic_depth_change
            elif (sum(last_generation_times) / len(last_generation_times)) > max_move_time:
                if ai2_depth > 4:
                    ai2_depth -= ai2_dynamic_depth_change
                    
            start_time = timeit.default_timer()
            
            result = ai2.generate_move(game, board, ai2_algo, ai2_depth, ai2_color)
            selected_square, new_square, _ = result[0][0], result[0][1], result[1]

            end_time = timeit.default_timer()
            time = end_time - start_time
            white_move_times.append(time)
            if time < 0.5:
                t.sleep(0.5)
            print(f'{ai2_color}: depth:{ai2_depth} time:{time:.2f}s')

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
                board.draw(window, piece_images)
                if not ai:
                    start_time = timeit.default_timer()


        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            # Player move, selecting piece
            elif event.type == pg.MOUSEBUTTONDOWN:
                if game.selected_square is None:
                    square = board.select_square_by_mouse_click(event)
                    if board.contains_piece(square):
                        if board.get_piece(square).color == game.turn:
                            valid_moves = game.get_valid_moves(board, square)
                            #board.draw(window, piece_images, square)
                            
                            if valid_moves:
                                board.draw(window, piece_images, square)
                                board.draw_valid_moves(window, valid_moves)
                                # if game.turn == "white":
                                #     board.draw_attacked_squares(window, game.attacked_squares_by_black)
                                # else:
                                #     board.draw_attacked_squares(window, game.attacked_squares_by_white)
                                game.selected_square = square
                            
                     
            # Player move, dropping selected piece
            elif game.selected_square is not None and event.type == pg.MOUSEBUTTONUP:
                new_square = board.select_square_by_mouse_click(event)
                if new_square in valid_moves:
                    game.execute_move(board, None, new_square)
                    game.update_attacked_squares(board)
                    end_time = timeit.default_timer()
                    time = end_time - start_time 
                    if game.turn == "white":
                        white_move_times.append(time)
                    else:
                        black_move_times.append(time)
                    game.swap_turn()
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
                valid_moves = None
                FPS = 10
                start_time = timeit.default_timer()

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
                    board.draw_selected_piece(window, piece_images, game.selected_square, mouse_cords)
                    board.draw_valid_moves(window, valid_moves)


        if game.no_valid_moves(board):
            if game.king_in_check(board):
                game.checkmate = True
                draw_game_status(window, font, "Checkmate")
            else:
                game.stalemate = True
                draw_game_status(window, font, "Stalemate")

        if game.king_in_check(board) and game.selected_square is None:
            if game.turn == "white":
                checked_square = board.white_king_square
            else:
                checked_square = board.black_king_square
            board.draw(window, piece_images, game.selected_square, checked_square)

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
        draw_move_time(window, font, "black", black_move_times[-1])
        draw_move_time(window, font, "white", white_move_times[-1])               
        pg.display.flip()
        clock.tick(FPS)

       


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