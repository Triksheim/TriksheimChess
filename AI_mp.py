from pieces import *
import random
from copy import deepcopy, copy
import timeit
import time as t
from multiprocessing import Pool, Manager, cpu_count


def multiprocess_minimax(args):
    ai, game, board, ai_color, opponent, depth, alpha, beta, maximize, best_move, move_path, initial_call = args
    return ai.minimax(game, board, ai_color, opponent, depth, alpha, beta, maximize, best_move, move_path, initial_call)

def generate_ai_move(ai, game, board, color, algo, depth):
    start_time = timeit.default_timer()
    result = ai.generate_move(game, board, algo, depth, color)
    selected_square, new_square, eval = result[0][0], result[0][1], result[1]
    end_time = timeit.default_timer()
    time = end_time - start_time
    #print(f'{color}: depth:{depth} time:{time:.2f}s')
    return selected_square, new_square, eval, time

def handle_ai_move(ai, game, board, ai_color, algo, depth, times, depth_step=1, min_time=3):
    if game.piece_count < 16:
        depth += depth_step
    if game.piece_count < 8:
        depth += depth_step
    if game.piece_count < 5:
        depth += depth_step
    
    selected_square, new_square, eval, time = generate_ai_move(ai, game, board, ai_color, algo, depth)
    times.append(time)
    if time < 0.5:
        t.sleep(0.5)

    if new_square is None:
        game.ai_move = None
        return
    else:
        game.ai_move = (selected_square, new_square)
        return

def execute_ai_move(game, board, selected_square, new_square):
    game.execute_move(board, selected_square, new_square)
    game.update_gamestate(board)



class ChessAI:
    def __init__(self, depth, algo, depth_step=0, ai_color="black"):
       self.color = ai_color
       self.depth = depth
       self.algo = algo
       self.depth_step = depth_step
       manager = Manager()
       self.transposition_table = manager.dict()
       self.count = 0
       

    def generate_move(self, game, board, algorithm, depth=2, ai_color="black"):
        if ai_color == "black":
            opponent = "white"
        else:
            opponent = "black"

        if algorithm == "random":
            return self.random_move(game, board, ai_color)
           
        elif algorithm == "minimax":
            squares_to_check = self.get_prioritised_moves(game, board, ai_color, opponent)
            core_count = (cpu_count() - 1)
            pool = Pool(core_count)  
            args_list = []  
            for square in squares_to_check:
                valid_moves = game.get_valid_moves(board, square, ai_color)
                if valid_moves:
                    #print(square , valid_moves)
                    for move in valid_moves:
                        args_list.append((self, game, board, ai_color, opponent, depth, float("-inf"), float("inf"), True, (square, move), [], True))
            if args_list:
                results = pool.map(multiprocess_minimax, args_list)
                pool.close()
                pool.join()
                if results:
                    best_move = max(results, key=lambda x: x[1])
                #print(best_move)
                #print(best_move[0], best_move[1])
                return best_move
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

    
    def evaluate(self, game, board, ai_color):
        if ai_color == "black":
            evaluation = (game.black_eval - game.white_eval)
        else:
            evaluation = (game.white_eval - game.black_eval)
        return evaluation


   
    def minimax(self, game, board, ai_color, opponent, depth, alpha=float("-inf"), beta=float("inf"), maximize=True, best_move=(None,None), move_path=[], initial_call=True ):
        original_alpha = alpha
        original_beta = beta

        board_state = (hash(tuple(board.int_board)), game.turn)
       
        if board_state in self.transposition_table and self.transposition_table[board_state][1] >= depth:
            bound_type = self.transposition_table[board_state][3]  # Get the bound type
            if bound_type == "LOWER" and self.transposition_table[board_state][2] > alpha:
                alpha = self.transposition_table[board_state][2]  # Raise alpha to the LOWER bound
            elif bound_type == "UPPER" and self.transposition_table[board_state][2] < beta:
                beta = self.transposition_table[board_state][2]  # Lower beta to the UPPER bound
            elif bound_type == "EXACT":
                return self.transposition_table[board_state][0], self.transposition_table[board_state][2], move_path
            if alpha >= beta:
                return self.transposition_table[board_state][0], self.transposition_table[board_state][2], move_path  # Alpha-beta cut-off


        if depth == 0:
            game.evaluate_board(board)
            if game.repetition:
                evaluation = 0
            else:
                evaluation = self.evaluate(game, board, ai_color)
            return best_move, evaluation, move_path


        if maximize:
            max_eval = float("-inf")

            if initial_call:
                square, move = best_move
                temp_game = deepcopy(game)
                temp_board = deepcopy(board)
                temp_game.execute_move(temp_board, square, move)
                temp_game.update_gamestate(temp_board)
                
                _, evaluation, path = self.minimax(temp_game, temp_board, ai_color, opponent, depth-1, alpha, beta, maximize=False, move_path=[], initial_call=False)              
                
                if evaluation > max_eval:
                    max_eval = evaluation
                    best_move = (square, move)
                    move_path = [(square, move)] + path

                if max_eval > original_alpha:
                    bound_type = "LOWER"
                elif max_eval < original_beta:
                    bound_type = "UPPER"
                else:
                    bound_type = "EXACT"
                self.transposition_table[board_state] = (best_move, depth, max_eval, bound_type)

            else:
                squares_to_check = (self.get_prioritised_moves(game, board, ai_color, opponent))
                for square in squares_to_check:
                    if beta <= alpha:
                        break # Beta cut-off
                    else:  
                        valid_moves = game.get_valid_moves(board, square)

                        if valid_moves:
                            for move in valid_moves:
                                temp_game = deepcopy(game)
                                temp_board = deepcopy(board)
                                temp_game.execute_move(temp_board, square, move)
                                temp_game.update_gamestate(temp_board)
                                
                                _, evaluation, path = self.minimax(temp_game, temp_board, ai_color, opponent, depth-1, alpha, beta, maximize=False, move_path=[], initial_call=False)
                                
                                if evaluation > max_eval:
                                    max_eval = evaluation
                                    best_move = (square, move)
                                    move_path = [(square, move)] + path

                                alpha = max(alpha, evaluation)
                                if beta <= alpha:
                                    break # Beta cut-off

                            if max_eval > original_alpha:
                                bound_type = "LOWER"
                            elif max_eval < original_beta:
                                bound_type = "UPPER"
                            else:
                                bound_type = "EXACT"
                            self.transposition_table[board_state] = (best_move, depth, max_eval, bound_type)


            if best_move == (None,None):  # No valid moves have been found
                if game.king_in_check(board, ai_color):
                    return best_move, float("-inf"), move_path  # Checkmate, return negative infinity
                else:
                    return best_move, 0, move_path  # Stalemate, return 0
            else:
                return best_move, max_eval, move_path


        else:
            min_eval = float("inf")
            squares_to_check = (self.get_prioritised_moves(game, board, opponent, ai_color))
            for square in (squares_to_check):
                if beta <= alpha:
                    break # cut-off
                else:
                    valid_moves = game.get_valid_moves(board, square)

                    if valid_moves:
                        for move in valid_moves:
                            temp_game = deepcopy(game)
                            temp_board = deepcopy(board)
                            temp_game.execute_move(temp_board, square, move)
                            temp_game.update_gamestate(temp_board)
                            
                            _, evaluation, path = self.minimax(temp_game, temp_board, ai_color, opponent, depth-1, alpha, beta, maximize=True, move_path=[], initial_call=False)                        

                            if evaluation < min_eval:
                                min_eval = evaluation
                                best_move = (square, move)
                                move_path = [(square, move)] + path

                            beta = min(beta, evaluation)
                            if beta <= alpha:
                                break # cut-off

                        if min_eval > original_alpha:
                            bound_type = "LOWER"
                        elif min_eval < original_beta:
                            bound_type = "UPPER"
                        else:
                            bound_type = "EXACT"
                        self.transposition_table[board_state] = (best_move, depth, min_eval, bound_type)


            if best_move == (None,None):  # No valid moves have been found
                if game.king_in_check(board, opponent):
                    return best_move, float("inf"), move_path  # Checkmate, return infinity
                else:
                    return best_move, 0, move_path  # Stalemate, return 0
            else:
                return best_move, min_eval, move_path









    
                            

 
    def random_move(self, game, board, color):
        """ Dont look at this """
        evaluation = "n/a"
        valid_moves = []
        ally_pieces = board.get_squares_with_piece(color)

        for square, piece in ally_pieces:
            moves = game.get_valid_moves(board, square, color)
            if moves:
                for move in moves:
                    valid_moves.append((square, move))

        if valid_moves:
            random_move = random.choice(valid_moves)
            return random_move, evaluation
               
        return (None, None), evaluation
        