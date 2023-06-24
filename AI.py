from pieces import *
import random
from copy import deepcopy
import timeit
import time as t

def generate_ai_move(ai, game, board, color, algo, depth):
    start_time = timeit.default_timer()
    result = ai.generate_move(game, board, algo, depth, color)
    selected_square, new_square, eval = result[0][0], result[0][1], result[1]
    end_time = timeit.default_timer()
    time = end_time - start_time
    #print(f'{color}: depth:{depth} time:{time:.2f}s')
    return selected_square, new_square, eval, time

def handle_ai_move(ai, game, board, ai_color, algo, depth, times, min_time=1, max_time=30, depth_step=1):
    if times[-1] < min_time and len(times) > 1:
        depth += depth_step
    # elif times[-1] > max_time:
    #     depth -= depth_step
    selected_square, new_square, eval, time = generate_ai_move(ai, game, board, ai_color, algo, depth)
    times.append(time)
    if time < 0.5:
        t.sleep(0.5)

    if new_square is None:
        return False    # No valid moves found
    else:
        game.execute_move(board, selected_square, new_square)
        game.update_attacked_squares(board)
        game.swap_turn()
        game.update_attacked_squares(board)
        game.evaluate_board(board)
        return True


class ChessAI:
    def __init__(self):
       self.transposition_table = {}

    def generate_move(self, game, board, algorithm, depth=2, ai_color="black"):
        if ai_color == "black":
            opponent = "white"
        else:
            opponent = "black"

        if algorithm == "random":
            return self.random_move(game, board, ai_color)
        elif algorithm == "minimax":
            result = self.minimax(game, board, ai_color, opponent, depth)
            return result
        
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
            
            if isinstance(piece, King):
                added = False
                if square in attacked:
                    first_prio.append((square, piece))
                    continue
                
                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked:
                            first_prio.append((square, piece))
                            added = True
                            break
                    
                if not added:
                    fourth_prio.append((square, piece))
                    continue


            elif isinstance(piece, Queen):
                added = False
                if square in attacked:
                    first_prio.append((square, piece))

                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked:
                            first_prio.append((square, piece))
                            added = True
                            break

                if not added:
                    third_prio.append((square, piece))
                    continue


            elif isinstance(piece, Rook):
                added = False
                if square in attacked and square not in defended:
                    first_prio.append((square, piece))
                    continue

                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked or opponent_dict[square + move].value > piece.value:
                            first_prio.append((square, piece))
                            added = True
                            break

                if not added and square in attacked:
                    second_prio.append((square, piece))
                    continue
                if not added:
                    fourth_prio.append((square, piece))
                    continue


            elif isinstance(piece, Knight) or isinstance(piece, Bishop):
                added = False
                if square in attacked and square not in defended:
                    first_prio.append((square, piece))
                    continue

                for move in piece.moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked or opponent_dict[square + move].value > piece.value:
                            first_prio.append((square, piece))
                            added = True
                            break

                if not added and (square in attacked and square in defended):
                    second_prio.append((square, piece))
                    continue
                if not added and square not in defended:
                    third_prio.append((square, piece))
                    continue
                if not added:
                    fourth_prio.append((square, piece))
                    continue


            elif isinstance(piece, Pawn):
                added = False
                if square in attacked and square not in defended:
                    first_prio.append((square, piece))
                    continue

                for move in piece.attack_moves:
                    if opponent_dict.get(square + move):
                        if (square + move) not in attacked or opponent_dict[square + move].value > piece.value:
                            first_prio.append((square, piece))
                            added = True
                            break

                if not added and square in attacked:
                    second_prio.append((square, piece))
                    continue
                if not added and square not in defended:
                    second_prio.append((square, piece))
                    continue
                if not added:
                    third_prio.append((square, piece))
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
        
        board_hash = (hash(tuple(board.int_board)), game.turn)

        # Check if board hash in transposition table
        if board_hash in self.transposition_table and self.transposition_table[board_hash][1] >= depth:
            # if initial_call:
            #     print(self.transposition_table[board_hash][0], " Final Evaluation:", self.transposition_table[board_hash][2])
            #     print("From transposision table")
            return self.transposition_table[board_hash][0], self.transposition_table[board_hash][2], move_path
        
        if depth == 0:
            evaluation = self.evaluate(game, board, ai_color)
            return best_move, evaluation, move_path


        if maximize:
            max_eval = float("-inf")
            squares_to_check = (self.get_prioritised_moves(game, board, ai_color, opponent))
            
            if initial_call:
                    try:
                        for square, piece in squares_to_check:
                            moves = game.get_valid_moves(board, square, ai_color)
                            if moves:
                                move = random.choice(moves)
                                best_move = (square, move)
                                break
                    except:
                        pass
            
            for square, piece in squares_to_check:
                if beta <= alpha:
                    break # Beta cut-off
                else:  
                    valid_moves = game.get_valid_moves(board, square, ai_color)

                    if valid_moves:
                        for move in valid_moves:
                            temp_game = deepcopy(game)
                            temp_board = deepcopy(board)
                            temp_game.execute_move(temp_board, square, move)
                            temp_game.update_attacked_squares(temp_board)
                            temp_game.swap_turn()
                            temp_game.update_attacked_squares(temp_board)
                            temp_game.evaluate_board(temp_board)

                            #new_move_path = move_path + [(square, move)]
                            _, evaluation, path = self.minimax(temp_game, temp_board, ai_color, opponent, depth-1, alpha, beta, maximize=False, move_path=[], initial_call=False)
                            if evaluation > max_eval:
                                max_eval = evaluation
                                best_move = (square, move)
                                move_path = [(square, move)] + path


                            alpha = max(alpha, evaluation)
                            if beta <= alpha:
                                break # Beta cut-off

                        self.transposition_table[board_hash] = (best_move, depth, max_eval)


            if best_move == (None,None):  # No valid moves have been found
                if game.king_in_check(board, ai_color):
                    # if initial_call:
                    #     print(best_move, " Final Evaluation:", max_eval)
                    return best_move, float("-inf"), move_path  # Checkmate, return negative infinity
                else:
                    # if initial_call:
                    #     print(best_move, " Final Evaluation:", max_eval)
                    return best_move, 0, move_path  # Stalemate, return 0
            else:
                # if initial_call:
                #     print(best_move, " Final Evaluation:", max_eval, " Path:", move_path)
                return best_move, max_eval, move_path


        else:
            min_eval = float("inf")
            squares_to_check = (self.get_prioritised_moves(game, board, opponent, ai_color))
            for square, piece in (squares_to_check):
                if beta <= alpha:
                    break # cut-off
                else:
                    valid_moves = game.get_valid_moves(board, square, opponent)

                    if valid_moves:
                        for move in valid_moves:
                            temp_game = deepcopy(game)
                            temp_board = deepcopy(board)
                            temp_game.execute_move(temp_board, square, move)
                            temp_game.update_attacked_squares(temp_board)
                            temp_game.swap_turn()
                            temp_game.update_attacked_squares(temp_board)
                            temp_game.evaluate_board(temp_board)
                            
                            _, evaluation, path = self.minimax(temp_game, temp_board, ai_color, opponent, depth-1, alpha, beta, maximize=True, move_path=[], initial_call=False)
                            if evaluation < min_eval:
                                min_eval = evaluation
                                best_move = (square, move)
                                move_path = [(square, move)] + path


                            beta = min(beta, evaluation)
                            if beta <= alpha:
                                break # cut-off

                        self.transposition_table[board_hash] = (best_move, depth, min_eval)


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
        