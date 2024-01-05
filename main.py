if __name__ == "__main__":
    import pygame as pg
    import timeit
    import threading

    from constants import *
    from board import ChessBoard
    from game import ChessGame
    from AI_mp import ChessAI, handle_ai_move
    from gui import GUI
    

def main():
    FPS = 10
    pg.init()
    pg.display.set_caption('Triksheim Chess')
    
    window = pg.display.set_mode((WIDTH, HEIGHT))   # Pygame display window
    clock = pg.time.Clock()
    board = ChessBoard()    # Board data
    game = ChessGame(white_clock=900, black_clock=900, increment=0)    # Game logic and game status
    gui = GUI()  # Graphics and IO handler

    # Set up the pieces on the board based on FEN string
    fen = STARTING_FEN
    #fen = TEST_FEN
    #fen = TEST2_FEN
    game.load_position_from_fen(board, fen)

    # setup thread for 1 sec clock count
    second_tick = threading.Thread(target=game.clock_tick)

    start_btn_press = False
    stop_btn_press = False

    game_running = False
    ai_finding_move = False
    pg_quit = False

    while not pg_quit:

        # Menu / Pause loop
        while not game_running and not pg_quit:

            # Reset game
            if gui.reset_button.active:
                board = ChessBoard()    
                game = ChessGame(white_clock=900, black_clock=900, increment=0) 
                gui = GUI()
                game.load_position_from_fen(board, fen)
                ai_finding_move = False

            gui.draw(window, board, game) 
            if gui.start_button.text == " Resume":
                gui.draw_text(window, "Game paused", 10*SQUARE_SIZE-25, 2*TOP_PADDING-10, 35)

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg_quit = True
                    break

                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.pos[0] > (COLS*SQUARE_SIZE)+(2*BOARD_FRAME_WIDTH):
                        start_btn_press = gui.mouse_click(event)
                            
            # Start game       
            if start_btn_press and not game.game_ended:
            
                if gui.black_settings.radio_group_player[1].active:     # Black Player is CPU
                    for btn in gui.black_settings.radio_group_diff:
                        if btn.active:
                            if  btn.text == "   Easy":
                                ai_black = ChessAI(EASY_MODE["depth"], EASY_MODE["depth_change"], "black")
                            elif btn.text == "Medium":
                                ai_black = ChessAI(MED_MODE["depth"], MED_MODE["depth_change"], "black")
                            else:
                                ai_black = ChessAI(HARD_MODE["depth"], HARD_MODE["depth_change"], "black")
                else:
                    ai_black = False

                if gui.white_settings.radio_group_player[1].active:     # White Player is CPU 
                     for btn in gui.white_settings.radio_group_diff:
                        if btn.active:
                            if btn.text == "   Easy":
                                ai_white = ChessAI(EASY_MODE["depth"], EASY_MODE["depth_change"], "white")
                            elif btn.text == "Medium":
                                ai_white = ChessAI(MED_MODE["depth"], MED_MODE["depth_change"], "white")
                            else:
                                ai_white = ChessAI(HARD_MODE["depth"], HARD_MODE["depth_change"], "white")
                else:
                    ai_white = False

                gui.disable_settings()
                game_running = True
                stop_btn_press = False 
                start_btn_press = False
               

            # Game ended status
            if game.checkmate:
                game.move_notation_log[-1] = game.move_notation_log[-1].replace("+", "#")
                if game.turn == "white":
                    checked_square = board.white_king_square
                else:
                    checked_square = board.black_king_square
                gui.draw(window, board, game, game.selected_square, checked_square)
                gui.draw_text(window, "Checkmate", 10*SQUARE_SIZE, 2*TOP_PADDING-10)
            elif game.stalemate:
                gui.draw_text(window, "Stalemate", 10*SQUARE_SIZE, 2*TOP_PADDING-10)
            elif game.white_clock <= 0 or game.black_clock <= 0:
                    if game.white_clock <= 0:
                        gui.draw_text(window, "White lost on time", 10*SQUARE_SIZE, 2*TOP_PADDING, 25)
                    else:
                        gui.draw_text(window, "Black lost on time", 10*SQUARE_SIZE, 2*TOP_PADDING, 25)
            elif game.repetition:
                gui.draw_text(window, "Draw by repetition", 10*SQUARE_SIZE, 2*TOP_PADDING, 25)
            
            if game.game_ended:
                gui.start_button.disable()
                gui.reset_button.enable()

            pg.display.flip()
            clock.tick(FPS)



        # Main gameloop (started)
        while game_running:
            
            if game.game_ended or game.repetition:
                game_running = False

            if game.selected_square is None:
                gui.draw(window, board, game)

            if not second_tick.is_alive():
                second_tick = threading.Thread(target=game.clock_tick)
                second_tick.start()

            if game.white_clock <= 0 or game.black_clock <= 0:
                game_running = False
            

            # AI move
            if ai_black and game.turn == ai_black.color and not ai_finding_move:
                ai_finding_move = True
                thread = threading.Thread(target=handle_ai_move, args=(ai_black, game, board))
                thread.start()

            # AI2 move
            elif ai_white and game.turn == ai_white.color and not ai_finding_move:  
                ai_finding_move = True
                thread = threading.Thread(target=handle_ai_move, args=(ai_white, game, board))
                thread.start()
        
            # Check if AI move is complete:
            if ai_finding_move and not thread.is_alive():
                ai_finding_move = False
                ai_move = game.ai_move
                if ai_move:
                    game.execute_move(board, ai_move[0], ai_move[1])
                    game.clock_increment()
                    game.update_gamestate(board)
                    game.evaluate_board(board)
                    game.get_algebraic_notation(board)
                    gui.draw(window, board, game)
                    if game.turn == "white":
                        game.white_move_clock = 0
                    else:
                        game.black_move_clock = 0
                    start_time_player = timeit.default_timer()
                else:
                    game_running = False


            # Check if player can move  
            if not ai_finding_move:
                if game.no_valid_moves(board):
                    game_running = False

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg_quit = True
                    game_running = False

                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.pos[0] > (COLS*SQUARE_SIZE)+(2*BOARD_FRAME_WIDTH):
                        stop_btn_press = gui.mouse_click(event)

                        if stop_btn_press:
                            gui.enable_settings()
                            game_running = False
                            

                if not ai_finding_move:

                    # Player move, selecting piece
                    if event.type == pg.MOUSEBUTTONDOWN and game.selected_square is None:
                        if game.selected_square is None:
                            square = board.select_square_by_mouse_click(event)
                            if board.contains_piece(square):
                                if board.get_piece(square).color == game.turn:
                                    valid_moves = game.get_valid_moves(board, square)
                                    if valid_moves:
                                        game.selected_square = square
                                        gui.draw(window, board, game, square)
                                        gui.board.draw_valid_moves(window, valid_moves)
                                    
                    # Player move, dropping selected piece
                    elif event.type == pg.MOUSEBUTTONUP and game.selected_square is not None:
                        new_square = board.select_square_by_mouse_click(event)
                        if new_square in valid_moves:
                            game.execute_move(board, None, new_square)
                            game.clock_increment()
                            game.update_attacked_squares(board)
                            game.swap_turn()
                            game.update_attacked_squares(board)
                            game.evaluate_board(board)
                            game.get_algebraic_notation(board)
                            if game.turn == "white":
                                game.white_move_clock = 0
                            else:
                                game.black_move_clock = 0
                            # print(f'black {game.black_eval}')
                            # print(f'white {game.white_eval}')
                            # print("")
                        game.selected_square = None
                       
                        if game.king_in_check(board):
                                if game.turn == "white":
                                    checked_square = board.white_king_square
                                else:
                                    checked_square = board.black_king_square
                        else:
                            checked_square = None
                        gui.draw(window, board, game, checked_square)
                        valid_moves = None
                        FPS = 10
                        

            # Drag selected piece
            if game.selected_square is not None:
                FPS = 60    # Increase FPS while dragging piece
                if event.type == pg.MOUSEMOTION or event.type == pg.MOUSEBUTTONDOWN:
                    mouse_cords = (event.pos[0], event.pos[1])
                    if game.king_in_check(board):
                        if game.turn == "white":
                            checked_square = board.white_king_square
                        else:
                            checked_square = board.black_king_square
                    else:
                        checked_square = None
                    gui.draw(window, board, game, game.selected_square, checked_square)
                    gui.board.draw_selected_piece(window, board, game.selected_square, mouse_cords)
                    gui.board.draw_valid_moves(window, valid_moves)


            if game_running and game.king_in_check(board) and game.selected_square is None:
                if game.turn == "white":
                    checked_square = board.white_king_square
                else:
                    checked_square = board.black_king_square
                gui.draw(window, board, game, game.selected_square, checked_square)
                gui.draw_text(window, "    Check", 10*SQUARE_SIZE, 2*TOP_PADDING-10)
                
            if not game_running and not stop_btn_press and not pg_quit:
                game.game_ended = True
                if game.white_clock <= 0 or game.black_clock <= 0 or game.repetition:
                    break
                elif game.king_in_check(board):
                    game.checkmate = True
                    if game.turn == "white":
                        checked_square = board.white_king_square
                    else:
                        checked_square = board.black_king_square
                else:
                    game.stalemate = True
                    
            pg.display.flip()
            clock.tick(FPS)


    pg.quit()

if __name__ == "__main__":
    main()