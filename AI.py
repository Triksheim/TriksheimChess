from pieces import *
import random
from copy import deepcopy
import time

class ChessAI:
    def __init__(self):
       self.hash_set = set()

    def generate_move(self, game, board, algorithm, depth=2, ai_color="black"):
        if ai_color == "black":
            opponent = "white"
        else:
            opponent = "black"

    
        if algorithm == "random":
            return self.random_move(game, board)
        elif algorithm == "minimax":
            return self.minimax(game, board, ai_color, depth)
        elif algorithm == "minimax_pruning":
            result = self.minimax_pruning(game, board, ai_color, opponent, depth)
            #self.hash_set = set()
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
                    third_prio.append((square, piece))
                    continue
                if not added:
                    fourth_prio.append((square, piece))
                    continue

        prioritised_moves.extend(first_prio)
        prioritised_moves.extend(second_prio)
        prioritised_moves.extend(third_prio)
        prioritised_moves.extend(fourth_prio)

        return prioritised_moves

    
    def evaluate(self, game, board, ai_color):
        if ai_color == "black":
            evaluation = (game.black_eval - game.white_eval)
            if board.white_king_square in game.attacked_squares_by_black:
                evaluation += 50
            if game.white_king_is_pinned:
                evaluation += 20

        else:
            evaluation = (game.white_eval - game.black_eval)
            if board.black_king_square in game.attacked_squares_by_white:
                evaluation += 50
            if game.black_king_is_pinned:
                evaluation += 20
        return evaluation


    def minimax_pruning(self, game, board, ai_color, opponent, depth, alpha=float("-inf"), beta=float("inf"), maximize=True, best_move=(None,None), initial_call=True ):
        # board_hash = hash(tuple(board.board))
        # if board_hash in self.hash_set:
        #     print("duplicate board")
        #     evaluation = self.evaluate(game, board, ai_color)
        #     return best_move, evaluation
        # else:
        #     self.hash_set.add(hash(tuple(board.board)))

        if depth == 0:
            evaluation = self.evaluate(game, board, ai_color)
            return best_move, evaluation


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
                            
                            _, evaluation= self.minimax_pruning(temp_game, temp_board, ai_color, opponent, depth-1, alpha, beta, maximize=False, initial_call=False)
                            if evaluation > max_eval:
                                max_eval = evaluation
                                best_move = (square, move)
                            alpha = max(alpha, evaluation)
                            if beta <= alpha:
                                break # Beta cut-off


            if best_move == (None,None):  # No valid moves have been found
                if game.king_in_check(board, ai_color):  # Check if it's checkmate
                    if initial_call:
                        print(best_move, " Final Evaluation:", max_eval)
                    return best_move, float("-inf")  # Checkmate, return negative infinity
                else:
                    if initial_call:
                        print(best_move, " Final Evaluation:", max_eval)
                    return best_move, 0  # Stalemate, return 0
            else:
                if initial_call:
                    print(best_move, " Final Evaluation:", max_eval)
                return best_move, max_eval


            

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
                            _, evaluation = self.minimax_pruning(temp_game, temp_board, ai_color, opponent, depth-1, alpha, beta, maximize=True, initial_call=False)
                            if evaluation < min_eval:
                                min_eval = evaluation
                                best_move = (square, move)
                            beta = min(beta, evaluation)
                            if beta <= alpha:
                                break # cut-off

            if best_move == (None,None):  # No valid moves have been found
                if game.king_in_check(board, opponent):  # Check if it's checkmate
                    return best_move, float("inf")  # Checkmate, return infinity
                else:
                    return best_move, 0  # Stalemate, return 0
            else:
                return best_move, min_eval









    # def minimax(self, game, board, ai_color, depth, maximize=True, best_move=(None,None) ):
    #     if depth == 0:
    #         if ai_color == "black":
    #             evaluation = (board.black_board_value - board.white_board_value)
    #         else:
    #             evaluation = (board.white_board_value - board.black_board_value)
    #         return best_move, evaluation

    #     if maximize:
    #         max_eval = float("-inf")
    #         for square, piece in enumerate(board.get()):
    #             if piece and piece.color == ai_color:
    #                 valid_moves = game.get_valid_moves(board, square, ai_color)
    #                 if valid_moves:
    #                     for move in valid_moves:
    #                         temp_board = deepcopy(board)
    #                         temp_board.move_piece(square, move)
    #                         move_candidate, evaluation= self.minimax(game, temp_board, ai_color, depth-1, maximize=False)
    #                         if evaluation > max_eval:
    #                             max_eval = evaluation
    #                             best_move = (square, move)
    #                         elif evaluation == max_eval and random.random() > 0.9:
    #                             best_move = (square, move)
    #         return best_move, max_eval

    #     else:
    #         min_eval = float("inf")
    #         if ai_color == "black":
    #             opponent = "white"
    #         else:
    #             opponent = "black"
    #         for square, piece in enumerate(board.get()):
    #             if piece and piece.color == opponent:
    #                 valid_moves = game.get_valid_moves(board, square, opponent)
    #                 if valid_moves:
    #                     for move in valid_moves:
    #                         temp_board = deepcopy(board)
    #                         temp_board.move_piece(square, move)
    #                         move_candidate, evaluation = self.minimax(game, temp_board, ai_color, depth-1, maximize=True)
    #                         if evaluation < min_eval:
    #                             min_eval = evaluation
    #                             best_move = (square, move)
    #                         elif evaluation == min_eval and random.random() > 0.9:
    #                             best_move = (square, move)
    #         return best_move, min_eval







    # def minimax2(self, game, board, ai_color, depth=3):
    #     if depth == 0:
    #         eval = (board.black_board_value - board.white_board_value)
    #         return eval, best_move

    #     if ai_color:
    #         max_eval = float("-inf")
    #         best_move = [(None, None)]
    #         for square, piece in enumerate(board.get()):
    #             if piece:
    #                 if piece.color == ai_color:
    #                     valid_moves = game.get_valid_moves(board, square)
    #                     if valid_moves:
    #                         for move in valid_moves:
    #                             temp_board = deepcopy(board)
    #                             temp_board.move_piece(square, move)

    #                             evaluation = self.minimax(game, temp_board, ai_color, depth-1)[0]
    #                             max_eval = max(evaluation, max_eval)
    #                             if (temp_board.black_board_value - temp_board.white_board_value == best_eval ):
    #                                 best_move.append((square, move))
    #                             elif (temp_board.black_board_value - temp_board.white_board_value > best_eval ):
    #                                 best_eval = temp_board.black_board_value - temp_board.white_board_value
    #                                 best_move = [(square, move)]
                                
    #                             return max_eval, best_move

    #     else:                     
    #         min_eval = float("inf")
    #         best_move = [(None, None)]
    #         for square, piece in enumerate(board.get()):
    #             if piece:
    #                 if piece.color != ai_color:
    #                     valid_moves = game.get_valid_moves(board, square)
    #                     if valid_moves:
    #                         for move in valid_moves:
    #                             temp_board = deepcopy(board)
    #                             temp_board.move_piece(square, move)

    #                             evaluation = self.minimax(game, temp_board, False, depth-1)[0]
    #                             min_eval = min(evaluation, min_eval)

    #                             if (temp_board.white_board_value - temp_board.black_board_value == best_eval ):
    #                                 best_move.append((square, move))
    #                             elif (temp_board.white_board_value - temp_board.black_board_value > best_eval ):
    #                                 best_eval = temp_board.white_board_value - temp_board.black_board_value
    #                                 best_move = [(square, move)]

    #                             return min_eval, best_move

        
    # def minimax_move(self, game, board, ai_color):
    #     best_eval = -999999999999999
    #     best_move = [(None, None)] # original square, new square
    #     time.sleep(0.2)
    #     for square, piece in enumerate(board.get()):
    #         if piece:
    #             if piece.color == ai_color:
    #                 valid_moves = game.get_valid_moves(board, square)
                    
    #                 if valid_moves:
    #                     for move in valid_moves:
    #                         temp_board = deepcopy(board)
    #                         temp_board.move_piece(square, move)
    #                         if ai_color == "black":
    #                             if (temp_board.black_board_value - temp_board.white_board_value == best_eval ):
    #                                 best_move.append((square, move))
    #                             elif (temp_board.black_board_value - temp_board.white_board_value > best_eval ):
    #                                 best_eval = temp_board.black_board_value - temp_board.white_board_value
    #                                 best_move = [(square, move)]
    #                         else:
    #                             if (temp_board.white_board_value - temp_board.black_board_value == best_eval ):
    #                                 best_move.append((square, move))
    #                             elif (temp_board.white_board_value - temp_board.black_board_value > best_eval ):
    #                                 best_eval = temp_board.white_board_value - temp_board.black_board_value
    #                                 best_move = [(square, move)]
    #     choice = random.choice(best_move)
    #     #return best_move if len(best_move) <= 1 else choice[0], choice[1]                     
    #     #choice = random.choice(best_move)
    #     return choice[0], choice[1], best_eval
                            


            
    def random_move(self, game, board):
        """ Dont look at this """
        valid_moves = []
        selected_square = None
        for _ in range(100):
            rnd_square = random.randint(0, 63)
            if board.contains_piece(rnd_square):
                if board.get()[rnd_square].color == "black":
                    selected_square = rnd_square
                    valid_moves = game.get_valid_moves(board, selected_square)
                    if valid_moves:
                        break
        if valid_moves:
            move = random.choice(valid_moves)
            return selected_square, move
        
        else:
            for i, square in enumerate(board.get()):
                if square:
                    if square.color == "black":
    
                        valid_moves = game.get_valid_moves(board, i)
                        if valid_moves:
                            move = random.choice(valid_moves)
                            return square, move
                        
            return None, None
        