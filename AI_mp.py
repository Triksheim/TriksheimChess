from pieces import *
from copy import deepcopy
import timeit
import time as t
from multiprocessing import Pool, Manager, cpu_count
import ctypes
import random as rnd


MATE = 10000


def multiprocess_minimax(args):
    ai, game, board, depth, alpha, beta, maximize, last_move, initial_call, total_inc = args
    return ai.minimax(game, board, depth, alpha, beta, maximize, last_move, initial_call, total_inc)

def generate_ai_move(ai, game, board):
    start_time = timeit.default_timer()
    result = ai.generate_move(game, board)
    selected_square, new_square, eval = result[0][0], result[0][1], result[1]
    end_time = timeit.default_timer()
    time = end_time - start_time
    try:
        print(f'{ai.color} move:({selected_square},{new_square})  Eval:{eval}  Time:{time:.2f}s' '\n')
    except:
        pass
    return selected_square, new_square, eval, time

def handle_ai_move(ai, game, board):
    selected_square, new_square, eval, time = generate_ai_move(ai, game, board)
    if time < 0.5:
        t.sleep(0.5)
    if new_square is None:
        game.ai_move = None
    else:
        game.ai_move = (selected_square, new_square)
        




class ChessAI:
    def __init__(self, depth, depth_inc, ai_color):
        self.depth = depth
        self.color = ai_color
        if self.color == "white":
            self.opponent = "black"
        else:
            self.opponent = "white"

        self.use_depth_inc = depth_inc
        if cpu_count() < 6:
            self.depth_inc_limit = 1
        else:
            self.depth_inc_limit = 2
        
        self.randomness = True
        self.use_memo = False
        manager = Manager()
        self.transposition_table = manager.dict()
        self.count = manager.Value(ctypes.c_int, 0)
        self.calc_count = manager.Value(ctypes.c_int, 0)

        self.memo_exact_count = manager.Value(ctypes.c_int, 0)
        self.memo_alpha_count = manager.Value(ctypes.c_int, 0)
        self.extention_count = manager.Value(ctypes.c_int, 0)
       

    def generate_move(self, game, board):
        core_count = (cpu_count() - 1)
        pool = Pool(core_count)  

        squares_to_check = self.get_prioritised_moves(game, board, self.color, self.opponent)
        args_list = []  
        for square in squares_to_check:
            valid_moves = game.get_valid_moves(board, square, self.color)

            if valid_moves:
                for move in valid_moves:
                    args_list.append((self, game, board, self.depth, float("-inf"), float("inf"), True, (square, move), True, 0))
        
        if args_list:
            results = pool.map(multiprocess_minimax, args_list)
            pool.close()
            pool.join()
            if results:
    
                #print(sorted(results, key=lambda x: x[1]))
                #print(max(results, key=lambda x: x[1]))

                max_move = max(results, key=lambda x: x[1])

                if self.randomness:
                    try:
                        moves = sorted(results, key=lambda x: x[1], reverse=True)
                        if len(moves) >= 3:
                            top_moves = []
                            weights = []
                            for i in range(0,3):
                                top_moves.append(moves[i])
                                weights.append(moves[i][1])

                            min_weight = min(weights)
                            for weight in weights:
                                weight += abs(min_weight+1)

                            choosen_move = rnd.choices(top_moves, weights)[0]
                            if abs(choosen_move[1] - max_move[1]) >= 100:
                                choosen_move = max_move
                            
                        else:
                            choosen_move = max_move
                    except:
                        choosen_move = max_move
                else:
                    choosen_move = max_move

                





            print(f'Moves checked: {self.count.value}, Moves calculated: {self.calc_count.value}')
            #print(f'Exact: {self.memo_exact_count.value}, Alpha: {self.memo_alpha_count.value}')
            #print(f'Extention: {self.extention_count.value}')
            self.memo_exact_count.value = 0
            self.memo_alpha_count.value = 0
            self.extention_count.value = 0
            self.count.value = 0
            self.calc_count.value = 0
            self.transposition_table.clear()
            
            return choosen_move
        else:
            return [(None, None), None, None]   # No possible moves
           


    def get_prioritised_moves(self, game, board, for_color, opponent):
        prioritised_moves = []
        first_prio = []
        second_prio = []
        third_prio = []
        fourth_prio = []

        ally_pieces = board.get_squares_with_piece(for_color)
        opponent_pieces = board.get_squares_with_piece(opponent)
        opponent_dict = {}
        for square, piece in opponent_pieces:
            opponent_dict[square] = piece

        if for_color == "white":
            attacked = game.attacked_squares_by_black
            defended = game.attacked_squares_by_white
        else:
            attacked = game.attacked_squares_by_white
            defended = game.attacked_squares_by_black

        for square, piece in ally_pieces:
            if isinstance(piece, Pawn):
                added = False
                if square in attacked and square not in defended:
                    first_prio.append(square)
                    continue
                for move in piece.attack_moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked or opponent_dict[square + move].value > piece.value:
                            first_prio.append(square)
                            added = True
                            break
                if not added:
                    second_prio.append(square)
                    continue

            elif isinstance(piece, Knight) or isinstance(piece, Bishop):
                added = False
                if square in attacked and square not in defended:
                    first_prio.append(square)
                    continue
                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked or opponent_dict[square + move].value > piece.value:
                            first_prio.append(square)
                            added = True
                            break
                if not added and (square in attacked and square in defended):
                    second_prio.append(square)
                    continue
                if not added:
                    third_prio.append(square)
                    continue

            elif isinstance(piece, King):
                added = False
                if square in attacked:
                    first_prio.append(square)
                    continue
                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked:
                            first_prio.append(square)
                            added = True
                            break
                if not added:
                    fourth_prio.append(square)
                    continue

            elif isinstance(piece, Queen):
                added = False
                if square in attacked:
                    first_prio.append(square)
                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked:
                            first_prio.append(square)
                            added = True
                            break
                if not added:
                    fourth_prio.append(square)
                    continue

            elif isinstance(piece, Rook):
                added = False
                if square in attacked and square not in defended:
                    first_prio.append(square)
                    continue
                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked or opponent_dict[square + move].value > piece.value:
                            first_prio.append(square)
                            added = True
                            break
                if not added and square in attacked:
                    second_prio.append(square)
                    continue
                if not added:
                    fourth_prio.append(square)
                    continue

        prioritised_moves.extend(first_prio)
        prioritised_moves.extend(second_prio)
        prioritised_moves.extend(third_prio)
        prioritised_moves.extend(fourth_prio)
        return prioritised_moves

    
    def evaluate(self, game, board):
        game.evaluate_board(board)
        if self.color == "black":
            evaluation = (game.black_eval - game.white_eval)
        else:
            evaluation = (game.white_eval - game.black_eval)
        return evaluation


   
    def minimax(self, game, board, depth, alpha, beta, maximize, last_move, initial_call, depth_limit_count):
        self.count.value += 1
        original_alpha = alpha
        original_beta = beta
        move_path = []
        choosen_move = last_move
        cutoff_occured = False

        board_state = (hash(tuple(board.int_board)), game.turn)

        if self.use_memo and depth != 0:
            if board_state in self.transposition_table and self.transposition_table[board_state][1] >= depth:
                bound_type = self.transposition_table[board_state][3]  # Get the bound type
                if bound_type == "LOWER" and self.transposition_table[board_state][2] > alpha:
                    alpha = self.transposition_table[board_state][2]  # Raise alpha to the LOWER bound
                elif bound_type == "UPPER" and self.transposition_table[board_state][2] < beta:
                    beta = self.transposition_table[board_state][2]  # Lower beta to the UPPER bound
                elif bound_type == "EXACT":
                    #self.memo_exact_count.value += 1
                    return self.transposition_table[board_state][0], self.transposition_table[board_state][2], self.transposition_table[board_state][4]
                
                if alpha >= beta:
                    #self.memo_alpha_count.value += 1
                    return self.transposition_table[board_state][0], self.transposition_table[board_state][2], self.transposition_table[board_state][4]  # Alpha-beta cut-off

            

        if depth == 0:
            if self.use_depth_inc:
                inc = False

                if game.king_in_check(board, self.opponent) or game.king_in_check(board, self.color):
                    inc = True
                    depth_limit_count += 1
                 
                elif  depth_limit_count < self.depth_inc_limit:
                    piece_moved = board.last_move[0]
                    new_square = board.last_move[2]

                    if piece_moved.color == "white":
                        if new_square in game.attacked_squares_by_black and new_square not in game.attacked_squares_by_white:
                            inc = True
                            depth_limit_count += 1
                                
                    elif piece_moved.color == "black":
                        if new_square in game.attacked_squares_by_white and new_square not in game.attacked_squares_by_black:
                            inc = True
                            depth_limit_count += 1

                if inc == True and last_move != (None, None):
                    depth += 1
                    #self.extention_count.value += 1
                else:
                    if game.repetition:
                        evaluation = 0
                    else:
                        evaluation = self.evaluate(game, board)
                    return last_move, evaluation, move_path
                    
            else:
                if game.repetition:
                    evaluation = 0
                else:
                    evaluation = self.evaluate(game, board)
                return last_move, evaluation, move_path
                

        self.calc_count.value += 1       
    

        if maximize:
            max_eval = float("-inf")


            if initial_call:
                square, move = last_move
                temp_game = deepcopy(game)
                temp_board = deepcopy(board)
                temp_game.execute_move(temp_board, square, move)
                temp_game.update_gamestate(temp_board)
                
                _, evaluation, path = self.minimax(temp_game, temp_board, depth-1, alpha, beta, maximize=False, last_move=(square,move), initial_call=False, depth_limit_count=depth_limit_count)              
                
                if evaluation > max_eval:
                    max_eval = evaluation
                    choosen_move = (square, move)
                    move_path = [(square, move)] + path

                if max_eval > original_alpha:
                    bound_type = "LOWER"
                elif max_eval < original_beta:
                    bound_type = "UPPER"
                else:
                    bound_type = "EXACT"

                if choosen_move != (None, None):
                    self.transposition_table[board_state] = (choosen_move, depth, max_eval, bound_type, move_path)

            else:
                maximizer_valid_move_found = False
                squares_to_check = (self.get_prioritised_moves(game, board, self.color, self.opponent))
                #squares_to_check = (board.get_squares_for_color(self.color))
                for square in squares_to_check:
                    if beta <= alpha:
                        break # Beta cut-off
                    else:  
                        valid_moves = game.get_valid_moves(board, square)

                        if valid_moves:
                            maximizer_valid_move_found = True
                            for move in valid_moves:
                                temp_game = deepcopy(game)
                                temp_board = deepcopy(board)
                                temp_game.execute_move(temp_board, square, move)
                                temp_game.update_gamestate(temp_board)
                                
                                _, evaluation, path = self.minimax(temp_game, temp_board, depth-1, alpha, beta, maximize=False, last_move=(square,move), initial_call=False, depth_limit_count=depth_limit_count)
                                
                                if evaluation > max_eval:
                                    max_eval = evaluation
                                    choosen_move = (square, move)
                                    move_path = [(square, move)] + path

                                alpha = max(alpha, evaluation)
                                if beta <= alpha:
                                    cutoff_occured = True
                                    break # Beta cut-off

                            if not cutoff_occured:
                                bound_type = "EXACT"
                            else:
                                if max_eval > original_alpha:
                                    bound_type = "LOWER"
                                elif max_eval < original_beta:
                                    bound_type = "UPPER"
                        
                            if choosen_move != (None,None):
                                self.transposition_table[board_state] = (choosen_move, depth, max_eval, bound_type, move_path)
                            
                if not maximizer_valid_move_found:
                    choosen_move = (None, None)
                        

            if choosen_move == (None,None):  # No valid moves have been found
                
                if game.king_in_check(board, self.color):
                    self.transposition_table[board_state] = (choosen_move, depth, (-MATE-(depth*1000)), "EXACT", move_path)
                    return choosen_move, (-MATE-(depth*1000)), move_path  # Checkmate, return negative infinity
                else:
                    self.transposition_table[board_state] = (choosen_move, depth, 0, "EXACT", move_path)
                    return choosen_move, 0, move_path  # Stalemate, return 0
            else:
                return choosen_move, max_eval, move_path
            

        # minimizer
        else:
            min_eval = float("inf")
            minimizer_valid_move_found = False
            squares_to_check = (self.get_prioritised_moves(game, board, self.opponent, self.color))
            #squares_to_check = (board.get_squares_for_color(self.opponent))
            for square in (squares_to_check):
                if beta <= alpha:
                    break # cut-off
                else:
                    valid_moves = game.get_valid_moves(board, square)

                    if valid_moves:
                        minimizer_valid_move_found = True
                        for move in valid_moves:
                            temp_game = deepcopy(game)
                            temp_board = deepcopy(board)
                            temp_game.execute_move(temp_board, square, move)
                            temp_game.update_gamestate(temp_board)

                            _, evaluation, path = self.minimax(temp_game, temp_board, depth-1, alpha, beta, maximize=True, last_move=(square,move), initial_call=False, depth_limit_count=depth_limit_count)                        

                            if evaluation < min_eval:
                                min_eval = evaluation
                                choosen_move = (square, move)
                                move_path = [choosen_move] + path

                            beta = min(beta, evaluation)
                            if beta <= alpha:
                                cutoff_occured = True
                                break # cut-off

                        if not cutoff_occured:
                                bound_type = "EXACT"
                        else:
                            if min_eval > original_alpha:
                                bound_type = "LOWER"
                            elif min_eval < original_beta:
                                bound_type = "UPPER"

                        if choosen_move != (None, None):
                            self.transposition_table[board_state] = (choosen_move, depth, min_eval, bound_type, move_path)

            if not minimizer_valid_move_found: # No valid moves for minimzier
                choosen_move = (None, None)


            if choosen_move == (None, None):  # No valid moves have been found
                
                if game.king_in_check(board, self.opponent):
                    self.transposition_table[board_state] = (choosen_move, depth, (MATE+(depth*1000)), "EXACT", move_path)
                    return choosen_move, (MATE+(depth*1000)), move_path  # Checkmate, return infinity
                else:
                    self.transposition_table[board_state] = (choosen_move, depth, 0, "EXACT", move_path)
                    return choosen_move, 0, move_path  # Stalemate, return 0
            else:
                return choosen_move, min_eval, move_path


