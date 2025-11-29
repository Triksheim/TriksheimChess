from pieces import *
import timeit
import time as t
from multiprocessing import Pool, cpu_count
import random as rnd
from copy import deepcopy

MATE = 10000

class LocalCounter:
    def __init__(self, initial=0):
        self.value = initial


def multiprocess_minimax(args):
    ai, game, board, depth, alpha, beta, maximize, last_move, initial_call, total_inc = args

    # reset stats
    ai.nodes.value = 0
    ai.leafs.value = 0
    ai.ab_cutoffs.value = 0
    ai.memo_exact_count.value = 0
    ai.memo_alpha_cut_count.value = 0
    ai.memo_beta_decrease_count.value = 0
    ai.extention_count.value = 0
    ai.tt_store_upper.value = 0
    ai.tt_store_lower.value = 0
    ai.tt_store_exact.value = 0

    # move gen
    move, eval, path = ai.minimax(
        game, board, depth, alpha, beta,
        maximize, last_move, initial_call, total_inc
    )

    # current worker stats
    stats = (
        ai.nodes.value,
        ai.leafs.value,
        ai.ab_cutoffs.value,
        ai.memo_exact_count.value,
        ai.memo_alpha_cut_count.value,
        ai.memo_alpha_improve_count.value,
        ai.memo_beta_decrease_count.value,
        ai.extention_count.value,
        ai.tt_store_upper.value,
        ai.tt_store_lower.value,
        ai.tt_store_exact.value,
    )
    return move, eval, path, stats

def generate_ai_move(ai, game, board):
    start_time = timeit.default_timer()
    result = ai.generate_move(game, board)
    selected_square, new_square, eval = result[0][0], result[0][1], result[1]
    end_time = timeit.default_timer()
    time = end_time - start_time
    ai.total_think_time += time
    try:
        print(f'{ai.color} move:({selected_square},{new_square})  Eval:{eval}  Time:{time:.2f}s' '\n')
    except:
        pass
    return selected_square, new_square, eval, time

def handle_ai_move(ai, game, board):
    selected_square, new_square, eval, time = generate_ai_move(ai, game, board)
    if time < 0.1:
        t.sleep(0.1)
    if new_square is None:
        game.ai_move = None
    else:
        game.ai_move = (selected_square, new_square)
        

class ChessAI:
    def __init__(self, depth, depth_inc, ai_color):
        self.use_multiprocessing = True
        self.randomness = False
        self.use_memo = True

        self.depth = depth
        self.color = ai_color
        if self.color == "white":
            self.opponent = "black"
        else:
            self.opponent = "white"
        if depth_inc > 0:
            self.use_depth_inc = True
            self.depth_inc_limit = depth_inc
        else:
            self.use_depth_inc = False
        
        self.transposition_table = {}
        self.total_think_time = 0
        self.nodes = LocalCounter(0)
        self.leafs = LocalCounter(0)
        self.ab_cutoffs = LocalCounter(0)
        self.memo_exact_count = LocalCounter(0)
        self.memo_alpha_cut_count = LocalCounter(0)
        self.memo_alpha_improve_count = LocalCounter(0)
        self.memo_beta_decrease_count = LocalCounter(0)
        self.extention_count = LocalCounter(0)
        self.tt_store_upper = LocalCounter(0)
        self.tt_store_lower = LocalCounter(0)
        self.tt_store_exact = LocalCounter(0)

    def generate_move(self, game, board):
        core_count = (cpu_count() - 1)

        results = []

        if not self.use_multiprocessing:
            self.nodes.value = 0
            self.leafs.value = 0
            self.ab_cutoffs.value = 0
            self.memo_exact_count.value = 0
            self.memo_alpha_cut_count.value = 0
            self.memo_alpha_improve_count.value = 0
            self.memo_beta_decrease_count.value = 0
            self.extention_count.value = 0
            self.tt_store_upper.value = 0
            self.tt_store_lower.value = 0
            self.tt_store_exact.value = 0
    
        squares_to_check = self.get_prioritised_moves(game, board, self.color, self.opponent)
        args_list = []  
        for square in squares_to_check:
            valid_moves = game.get_valid_moves(board, square, self.color)
            if valid_moves:
                for move in valid_moves:
                    args_list.append(
                        (self, game, board,
                        self.depth,
                        float("-inf"), float("inf"),
                        True, (square, move),
                        True, 0)
                    )
        
        if args_list:
            # multiprocessing
            if self.use_multiprocessing:
                pool = Pool(core_count)
                results = pool.map(multiprocess_minimax, args_list)
                pool.close()
                pool.join()
            else:
               # single
                results = []
                for (ai, g, b, depth, alpha, beta, maximize, last_move, initial_call, total_inc) in args_list:
                    temp_game = deepcopy(g)
                    temp_board = deepcopy(b)
                    res = ai.minimax(temp_game, temp_board, depth, alpha, beta,
                                    maximize, last_move, initial_call, total_inc)
                    results.append(res)

        if results:
            # best
            max_result = max(results, key=lambda x: x[1])

            if self.randomness:
                try:
                    moves = sorted(results, key=lambda x: x[1], reverse=True)
                    if len(moves) >= 3:
                        top_moves = []
                        weights = []
                        for i in range(0, 3):
                            top_moves.append(moves[i])
                            weights.append(moves[i][1])

                        min_weight = min(weights)
                        for weight in weights:
                            weight += abs(min_weight + 1)

                        chosen_result = rnd.choices(top_moves, weights)[0]
                        if abs(chosen_result[1] - max_result[1]) >= 100:
                            chosen_result = max_result
                    else:
                        chosen_result = max_result
                except:
                    chosen_result = max_result
            else:
                chosen_result = max_result

            # aggregate stats from workers
            if self.use_multiprocessing:
                total_nodes = 0
                total_leafs = 0
                total_ab_cutoffs = 0
                total_memo_exact = 0
                total_memo_alpha_cut = 0
                total_memo_alpha_improve = 0
                total_memo_beta_decrease = 0
                total_ext = 0
                total_tt_u = 0
                total_tt_l = 0
                total_tt_e = 0

                for (_, _, _, stats) in results:
                    nodes, leafs, ab_c, memo_ex, memo_al, memo_al_imp, memo_beta_dec, ext, tt_u, tt_l, tt_e = stats
                    
                    total_nodes += nodes
                    total_leafs += leafs
                    total_ab_cutoffs += ab_c
                    total_memo_exact += memo_ex
                    total_memo_alpha_cut += memo_al
                    total_memo_alpha_improve += memo_al_imp
                    total_memo_beta_decrease += memo_beta_dec
                    total_ext += ext
                    total_tt_u += tt_u
                    total_tt_l += tt_l
                    total_tt_e += tt_e

                self.nodes.value = total_nodes
                self.leafs.value = total_leafs
                self.ab_cutoffs.value = total_ab_cutoffs
                self.memo_exact_count.value = total_memo_exact
                self.memo_alpha_cut_count.value = total_memo_alpha_cut
                self.memo_alpha_improve_count.value = total_memo_alpha_improve
                self.memo_beta_decrease_count.value = total_memo_beta_decrease
                self.extention_count.value = total_ext
                self.tt_store_upper.value = total_tt_u
                self.tt_store_lower.value = total_tt_l
                self.tt_store_exact.value = total_tt_e

            print(f'Total nodes: {self.nodes.value}, Total leafs: {self.leafs.value}')
            print(f'Alpha-Beta cutoffs: {self.ab_cutoffs.value}')
            print(f'Memo stats: Exact: {self.memo_exact_count.value}, Alpha>Beta: {self.memo_alpha_cut_count.value}, Alpha inc: {self.memo_alpha_improve_count.value}, Beta dec: {self.memo_beta_decrease_count.value}')
            print(f'TT stored: UPPER={self.tt_store_upper.value}, LOWER={self.tt_store_lower.value}, EXACT={self.tt_store_exact.value}')
            print(f'Extensions: {self.extention_count.value}')
            
            self.nodes.value = 0
            self.leafs.value = 0
            self.ab_cutoffs.value = 0
            self.memo_exact_count.value = 0
            self.memo_alpha_cut_count.value = 0
            self.memo_alpha_improve_count.value = 0
            self.memo_beta_decrease_count.value = 0
            self.extention_count.value = 0

            if self.use_multiprocessing:
                best_move, best_eval, best_path, _ = chosen_result
            else:
                best_move, best_eval, best_path = chosen_result

            return (best_move, best_eval, best_path)
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
        self.nodes.value += 1
        original_alpha = alpha
        original_beta = beta
        move_path = []
        choosen_move = last_move

        board_state = (hash(tuple(board.int_board)), game.turn)

        if self.use_memo and depth != 0 and not initial_call:
            entry = self.transposition_table.get(board_state)
            if entry is not None:
                move_tt, stored_depth, stored_eval, bound_type = entry
                if stored_depth >= depth:
                    if bound_type == "LOWER" and stored_eval > alpha:
                        self.memo_alpha_improve_count.value += 1
                        alpha = stored_eval
                    elif bound_type == "UPPER":# and stored_eval < beta:
                        self.memo_beta_decrease_count.value += 1
                        if stored_eval < beta:
                            beta = stored_eval
                    elif bound_type == "EXACT":
                        self.memo_exact_count.value += 1
                        return move_tt, stored_eval, []

                    if alpha >= beta:
                        self.memo_alpha_cut_count.value += 1
                        return move_tt, stored_eval, []

    
        if depth == 0:

            if self.use_depth_inc:
                inc = False

                if game.king_in_check(board, self.opponent) or game.king_in_check(board, self.color):
                    if depth_limit_count < self.depth_inc_limit:
                        inc = True
                    
                elif depth_limit_count < self.depth_inc_limit:
                    piece_moved = board.last_move[0]
                    new_square = board.last_move[2]

                    if piece_moved.color == "white":
                        if new_square in game.attacked_squares_by_black and new_square not in game.attacked_squares_by_white:
                            inc = True 
                                
                    elif piece_moved.color == "black":
                        if new_square in game.attacked_squares_by_white and new_square not in game.attacked_squares_by_black:
                            inc = True
                            

                if inc == True and last_move != (None, None):
                    # extend
                    if depth_limit_count + 1 < self.depth_inc_limit:
                        n = 1
                    else: n = 1
                    depth += n
                    depth_limit_count += n
                    self.extention_count.value += n
                else:
                    # end
                    self.leafs.value += 1

                    if game.repetition:
                        evaluation = 0
                    else:
                        evaluation = self.evaluate(game, board)
                    return last_move, evaluation, move_path
                    
            else:
                # end
                self.leafs.value += 1

                if game.repetition:
                    evaluation = 0
                else:
                    evaluation = self.evaluate(game, board)
                return last_move, evaluation, move_path
                

              
        if maximize:
            max_eval = float("-inf")

            if initial_call:
                square, move = last_move
                state = game.make_move_for_search(board, square, move)
                try:
                    _, evaluation, path = self.minimax(
                        game,
                        board,
                        depth-1,
                        alpha,
                        beta,
                        False,                 # minimizing
                        (square, move),
                        initial_call=False,
                        depth_limit_count=depth_limit_count
                    )
                finally:
                    game.unmake_move_for_search(board, state)

                if evaluation > max_eval:
                    max_eval = evaluation
                    choosen_move = (square, move)
                    move_path = [(square, move)] + path

                if max_eval <= original_alpha:
                    self.tt_store_upper.value += 1
                    bound_type = "UPPER"
                elif max_eval >= original_beta:
                    self.tt_store_lower.value += 1
                    bound_type = "LOWER"
                else:
                    self.tt_store_exact.value += 1
                    bound_type = "EXACT"

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
                                state = game.make_move_for_search(board, square, move)
                                try:
                                    _, evaluation, path = self.minimax(
                                        game,
                                        board,
                                        depth-1,
                                        alpha,
                                        beta,
                                        False,                # minimizing
                                        (square, move),
                                        initial_call=False,
                                        depth_limit_count=depth_limit_count
                                    )
                                finally:
                                    game.unmake_move_for_search(board, state)

                                if evaluation > max_eval:
                                    max_eval = evaluation
                                    choosen_move = (square, move)
                                    move_path = [(square, move)] + path

                                alpha = max(alpha, evaluation)
                                if beta <= alpha:
                                    cutoff_occured = True
                                    self.ab_cutoffs.value += 1
                                    break # beta cutoff

                            if self.use_memo and choosen_move != (None, None):
                                if max_eval <= original_alpha:
                                    self.tt_store_upper.value += 1
                                    bound_type = "UPPER"
                                elif max_eval >= original_beta:
                                    self.tt_store_lower.value += 1
                                    bound_type = "LOWER"
                                else:
                                    self.tt_store_exact.value += 1
                                    bound_type = "EXACT"
                                self.transposition_table[board_state] = (choosen_move, depth, max_eval, bound_type)
                                
                if not maximizer_valid_move_found:
                    choosen_move = (None, None)
                        
            if choosen_move == (None,None):  # No valid moves have been found
                self.leafs.value += 1
                if game.king_in_check(board, self.color):
                    self.transposition_table[board_state] = (choosen_move, depth, (-MATE-(depth*1000)), "EXACT")
                    return choosen_move, (-MATE-(depth*1000)), move_path  # Checkmate
                else:
                    self.transposition_table[board_state] = (choosen_move, depth, 0, "EXACT")
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
                            state = game.make_move_for_search(board, square, move)
                            try:
                                _, evaluation, path = self.minimax(
                                    game,
                                    board,
                                    depth-1,
                                    alpha,
                                    beta,
                                    True,                 # maximizing
                                    (square, move),
                                    initial_call=False,
                                    depth_limit_count=depth_limit_count
                                )
                            finally:
                                game.unmake_move_for_search(board, state)

                            if evaluation < min_eval:
                                min_eval = evaluation
                                choosen_move = (square, move)
                                move_path = [(square, move)] + path

                            beta = min(beta, evaluation)
                            if beta <= alpha:
                                cutoff_occured = True
                                self.ab_cutoffs.value += 1
                                break # cut-off

                        if self.use_memo and choosen_move != (None, None):
                            if min_eval <= original_alpha:
                                self.tt_store_upper.value += 1
                                bound_type = "UPPER"
                            elif min_eval >= original_beta:
                                self.tt_store_lower.value += 1
                                bound_type = "LOWER"
                            else:
                                self.tt_store_exact.value += 1
                                bound_type = "EXACT"
                            self.transposition_table[board_state] = (choosen_move, depth, min_eval, bound_type)

            if not minimizer_valid_move_found: # No valid moves for minimzier
                choosen_move = (None, None)

            if choosen_move == (None, None):  # No valid moves have been found
                self.leafs.value += 1
                if game.king_in_check(board, self.opponent):
                    if self.use_memo:
                        self.transposition_table[board_state] = (choosen_move, depth, (MATE+(depth*1000)), "EXACT")
                    return choosen_move, (MATE+(depth*1000)), move_path  # Checkmate
                else:
                    if self.use_memo:
                        self.transposition_table[board_state] = (choosen_move, depth, 0, "EXACT")
                    return choosen_move, 0, move_path  # Stalemate, return 0
            else:
                return choosen_move, min_eval, move_path
