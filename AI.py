from pieces import *
from game import KING_MOVES_BY_SQUARE, KNIGHT_MOVES_BY_SQUARE, PAWN_ATTACKS_BY_COLOR, SLIDING_RAYS
import timeit
import time as t
from multiprocessing import Pool, cpu_count
import random as rnd
from copy import deepcopy
from opening_book import get_opening_book, uci_to_move

MATE = 10000
AI_LOG_SEARCH_STATS = False


class SearchTimeout(Exception):
    pass


class LocalCounter:
    def __init__(self, initial=0):
        self.value = initial


def square_to_uci(square):
    return chr(ord("a") + square % 8) + str(square // 8 + 1)


def move_to_uci(move):
    if move is None or move == (None, None):
        return "none"
    return square_to_uci(move[0]) + square_to_uci(move[1])


def multiprocess_minimax(args):
    ai, game, board, depth, alpha, beta, maximize, last_move, initial_call, total_inc = args

    # reset stats
    ai.reset_search_stats()

    # move gen
    try:
        move, eval, path = ai.minimax(
            game, board, depth, alpha, beta,
            maximize, last_move, initial_call, total_inc
        )
    except SearchTimeout:
        move, eval, path = last_move, None, []
        ai.search_timed_out = True

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
    search_game = deepcopy(game)
    search_board = deepcopy(board)
    result = ai.generate_move(search_game, search_board)
    selected_square, new_square, eval = result[0][0], result[0][1], result[1]
    used_opening_book = ai.last_move_from_opening_book
    end_time = timeit.default_timer()
    time = end_time - start_time
    ai.total_think_time += time
    try:
        print(format_ai_move_log(ai, (selected_square, new_square), eval, time))
    except:
        pass
    return selected_square, new_square, eval, time


def ai_level(ai):
    if ai.depth <= 1:
        return "Easy"
    if ai.depth <= 3:
        return "Medium"
    return "Hard"


def format_ai_move_log(ai, move, evaluation, elapsed):
    summary = ai.last_search_summary or {}
    source = "book" if ai.last_move_from_opening_book else "search"
    depth_text = "book"
    if source != "book":
        depth = summary.get("depth", ai.depth)
        if ai.use_dynamic_depth:
            completed = summary.get("completed_depth", depth)
            target = summary.get("target_depth", depth)
            depth_text = f"{completed}/{target}"
        else:
            depth_text = str(depth)

    parts = [
        f"AI move | level={ai_level(ai):<6}",
        f"color={ai.color:<5}",
        f"move={move_to_uci(move):<5}",
        f"eval={evaluation}",
        f"time={elapsed:.2f}s",
        f"source={source}",
        f"depth={depth_text}",
    ]

    if ai.use_dynamic_depth and source != "book":
        if summary.get("status"):
            parts.append(f"status={summary['status']}")
        if summary.get("budget"):
            parts.append(f"budget={summary['budget']}")
        if summary.get("partial_roots"):
            completed_roots, total_roots = summary["partial_roots"]
            parts.append(f"partial_roots={completed_roots}/{total_roots}")

    if source != "book":
        parts.extend(
            [
                f"nodes={summary.get('nodes', 0)}",
                f"cutoffs={summary.get('cutoffs', 0)}",
                f"tt={summary.get('tt_exact', 0)}/{summary.get('tt_lower', 0)}/{summary.get('tt_upper', 0)}",
            ]
        )

    return "  ".join(parts)

def handle_ai_move(ai, game, board):
    selected_square, new_square, eval, time = generate_ai_move(ai, game, board)
    if time < 0.1:
        t.sleep(0.1)
    if new_square is None:
        game.ai_move = None
    else:
        game.ai_move = (selected_square, new_square)


def describe_ai(ai):
    if not ai:
        return "Player"
    features = []
    if ai.use_dynamic_depth:
        features.append(f"dynamic soft={ai.soft_time_limit}s hard={ai.time_limit}s")
    if ai.use_opening_book:
        features.append("opening_book")
    if ai.use_quiescence:
        features.append(f"quiescence={ai.quiescence_depth}")
    if ai.use_memo:
        features.append("TT")
    if ai.use_pvs:
        features.append("PVS")
    mode = ", ".join(features) if features else "plain search"
    return f"CPU depth={ai.depth} inc={ai.depth_inc_limit if ai.use_depth_inc else 0} {mode}"
        

class ChessAI:
    def __init__(self, depth, depth_inc, ai_color):
        self.use_multiprocessing = True
        self.randomness = False
        self.use_memo = True
        self.use_pvs = True
        self.use_quiescence = True
        self.use_quiescence_checks = False
        self.use_killer_history = False
        self.use_root_score_ordering = True
        self.use_opening_book = depth >= 4
        self.use_iterative_deepening = False
        self.iterative_deepening_min_depth = 4
        self.iterative_deepening_prep_depth = 2
        self.use_dynamic_depth = False
        self.time_limit = None
        self.soft_time_limit = None
        self.search_deadline = None
        self.search_timed_out = False
        self.last_search_root_count = 0
        self.last_search_completed_roots = 0
        self.last_move_from_opening_book = False
        self.last_search_summary = {}
        self.quiescence_depth = 1

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
        self.killer_moves = {}
        self.history_scores = {}
        self.root_move_scores = {}
        self._pool = None
        self._pool_core_count = None
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

    def reset_search_stats(self):
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

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_pool"] = None
        state["_pool_core_count"] = None
        return state

    def get_pool(self, core_count):
        if self._pool is None or self._pool_core_count != core_count:
            self.close_pool()
            self._pool = Pool(core_count)
            self._pool_core_count = core_count
        return self._pool

    def close_pool(self):
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None
            self._pool_core_count = None

    def check_search_deadline(self):
        if self.search_deadline is None:
            return
        if (self.nodes.value & 1023) == 0 and timeit.default_timer() >= self.search_deadline:
            self.search_timed_out = True
            raise SearchTimeout

    def generate_move(self, game, board):
        self.last_move_from_opening_book = False
        self.last_search_summary = {}
        if self.use_opening_book:
            book_move = self.get_opening_book_move(game, board)
            if book_move is not None:
                self.last_move_from_opening_book = True
                self.last_search_summary = {"source": "book"}
                return book_move, self.evaluate(game, board), [book_move]
        if self.use_dynamic_depth:
            return self.generate_move_dynamic(game, board)
        self.root_move_scores = {}
        return self.search_depth(game, board, self.depth, print_stats=False)

    def get_opening_book_move(self, game, board):
        book_candidates = get_opening_book().get(game.get_position_key(board))
        if not book_candidates:
            return None

        legal_moves = set()
        for square, _ in board.get_squares_with_piece(game.turn):
            for move in game.get_valid_moves(board, square, game.turn) or []:
                legal_moves.add((square, move))

        legal_candidates = []
        for uci, weight in book_candidates.items():
            move = uci_to_move(uci)
            if move in legal_moves:
                legal_candidates.append((uci, weight, move))

        if not legal_candidates:
            return None

        legal_candidates.sort(key=lambda item: (-item[1], item[0]))
        if not self.randomness or len(legal_candidates) == 1:
            return legal_candidates[0][2]

        return rnd.choices(
            [candidate[2] for candidate in legal_candidates],
            weights=[candidate[1] for candidate in legal_candidates],
            k=1,
        )[0]

    def generate_move_dynamic(self, game, board):
        self.root_move_scores = {}
        hard_time_limit = self.time_limit if self.time_limit is not None else 15.0
        soft_time_limit = self.soft_time_limit if self.soft_time_limit is not None else min(5.0, hard_time_limit)
        start_time = timeit.default_timer()
        deadline_margin = 0.30 if self.use_multiprocessing else 0.05
        hard_deadline = start_time + max(0.1, hard_time_limit - deadline_margin)
        soft_deadline = start_time + max(0.1, soft_time_limit - deadline_margin)
        root_moves = self.get_ordered_moves(game, board, self.color, self.opponent, 1)
        normal_depth, max_dynamic_depth, force_long_think = self.estimate_dynamic_target_depth(game, board, root_moves)
        target_depth = normal_depth
        use_long_budget = force_long_think
        best_completed_result = None
        best_completed_depth = 0
        last_partial_result = None
        last_partial_depth = 0
        last_partial_roots = (0, 0)
        previous_move = None
        previous_eval = None
        elapsed = 0

        search_depth = 1
        while search_depth <= target_depth and search_depth <= self.depth:
            deadline = hard_deadline if use_long_budget else soft_deadline
            if timeit.default_timer() >= deadline:
                break

            result = self.search_depth(game, board, search_depth, deadline=deadline, print_stats=False)
            elapsed = timeit.default_timer() - start_time

            if result[0] != (None, None) and result[1] is not None:
                if not self.search_timed_out:
                    best_completed_result = result
                    best_completed_depth = search_depth
                    if previous_eval is not None:
                        eval_swing = abs(result[1] - previous_eval)
                        move_changed = result[0] != previous_move
                        if self.should_use_long_dynamic_budget(
                            game,
                            board,
                            root_moves,
                            search_depth,
                            eval_swing,
                            move_changed,
                        ):
                            use_long_budget = True
                            target_depth = min(max_dynamic_depth, target_depth + 1)
                    previous_move = result[0]
                    previous_eval = result[1]
                else:
                    last_partial_result = result
                    last_partial_depth = search_depth
                    last_partial_roots = (self.last_search_completed_roots, self.last_search_root_count)

            if self.search_timed_out:
                break
            if elapsed >= soft_time_limit and not use_long_budget:
                break
            search_depth += 1

        chosen_result = best_completed_result or last_partial_result
        partial_roots_text = ""
        if self.search_timed_out and last_partial_result is not None and last_partial_depth > best_completed_depth:
            completed_roots, total_roots = last_partial_roots
            min_partial_roots = max(6, total_roots // 6)
            if completed_roots >= min_partial_roots:
                chosen_result = last_partial_result
                partial_roots_text = f" partial_depth={last_partial_depth} partial_roots={completed_roots}/{total_roots}"

        if chosen_result is None:
            chosen_result = self.search_depth(game, board, 1, deadline=None, print_stats=False)
            best_completed_depth = 1

        status = "timeout" if self.search_timed_out else "complete"
        budget = "long" if use_long_budget else "soft"
        summary = dict(self.last_search_summary)
        summary.update(
            {
                "status": status,
                "completed_depth": best_completed_depth,
                "target_depth": target_depth,
                "max_depth": self.depth,
                "elapsed": elapsed,
                "budget": budget,
                "soft_time_limit": soft_time_limit,
                "hard_time_limit": hard_time_limit,
            }
        )
        if partial_roots_text:
            summary["partial_roots"] = last_partial_roots
            summary["partial_depth"] = last_partial_depth
        self.last_search_summary = summary
        return chosen_result

    def estimate_dynamic_target_depth(self, game, board, root_moves):
        if self.depth <= 3:
            return self.depth, self.depth, False

        normal_depth = min(self.depth, 5)
        max_dynamic_depth = normal_depth
        pressure = 0
        root_count = len(root_moves)

        if game.king_in_check(board, self.color):
            pressure += 4
        if game.king_in_check(board, self.opponent):
            pressure += 2

        noisy_moves = 0
        for square, move in root_moves:
            if self.is_noisy_move(game, board, square, move):
                noisy_moves += 1

        if root_count >= 40:
            pressure += 1
        if root_count >= 52:
            pressure += 1
        if noisy_moves >= 8:
            pressure += 2
        if noisy_moves >= 14:
            pressure += 2

        if pressure >= 3:
            max_dynamic_depth += 1
        if pressure >= 6:
            max_dynamic_depth += 1

        force_long_think = pressure >= 6
        return normal_depth, min(self.depth, max_dynamic_depth), force_long_think

    def should_use_long_dynamic_budget(self, game, board, root_moves, completed_depth, eval_swing, move_changed):
        if completed_depth < 3:
            return False
        if game.king_in_check(board, self.color):
            return True

        noisy_moves = 0
        for square, move in root_moves:
            if self.is_noisy_move(game, board, square, move):
                noisy_moves += 1

        if eval_swing >= 220:
            return True
        if move_changed and eval_swing >= 120:
            return True
        if move_changed and noisy_moves >= 10:
            return True
        return False

    def search_depth(self, game, board, search_depth, deadline=None, print_stats=True):
        core_count = max(cpu_count() - 1, 1)

        results = []

        self.search_deadline = deadline
        self.search_timed_out = False
        self.reset_search_stats()
    
        root_moves = self.get_ordered_moves(game, board, self.color, self.opponent, search_depth)
        root_moves = self.order_root_moves_with_iterative_deepening(game, board, root_moves)
        if self.use_root_score_ordering and self.root_move_scores:
            original_root_order = {move: index for index, move in enumerate(root_moves)}
            root_moves.sort(
                key=lambda move: (
                    -self.root_move_scores.get(move, float("-inf")),
                    original_root_order.get(move, 0),
                )
            )
        self.last_search_root_count = len(root_moves)
        self.last_search_completed_roots = 0
        self.reset_search_stats()

        args_list = []  
        for square, move in root_moves:
            args_list.append(
                (self, game, board,
                search_depth,
                float("-inf"), float("inf"),
                True, (square, move),
                True, 0)
            )
        
        if args_list:
            # multiprocessing
            if self.use_multiprocessing:
                first_result = multiprocess_minimax(args_list[0])
                results = [first_result]

                if len(args_list) > 1 and not self.search_timed_out:
                    first_eval = first_result[1] if first_result[1] is not None else float("-inf")
                    bounded_args = []
                    for ai, g, b, depth, _, beta, maximize, last_move, initial_call, total_inc in args_list[1:]:
                        bounded_args.append(
                            (ai, g, b, depth, first_eval, beta, maximize, last_move, initial_call, total_inc)
                        )
                    pool = self.get_pool(core_count)
                    results.extend(pool.map(multiprocess_minimax, bounded_args))
            else:
               # single
                results = []
                root_alpha = float("-inf")
                for (ai, g, b, depth, alpha, beta, maximize, last_move, initial_call, total_inc) in args_list:
                    temp_game = deepcopy(g)
                    temp_board = deepcopy(b)
                    try:
                        res = ai.minimax(temp_game, temp_board, depth, root_alpha, beta,
                                        maximize, last_move, initial_call, total_inc)
                    except SearchTimeout:
                        res = (last_move, None, [])
                    results.append(res)
                    if res[1] is not None and res[1] > root_alpha:
                        root_alpha = res[1]
                    if self.search_timed_out:
                        break

        if results:
            completed_results = [result for result in results if result[1] is not None]
            self.last_search_completed_roots = len(completed_results)
            if not completed_results:
                self.search_timed_out = True
                self.search_deadline = None
                return ((None, None), None, None)

            if any(result[1] is None for result in results):
                self.search_timed_out = True

            # best
            max_result = max(completed_results, key=lambda x: x[1])
            self.root_move_scores = {
                result[0]: result[1]
                for result in completed_results
                if result[0] != (None, None)
            }

            if self.randomness:
                try:
                    moves = sorted(completed_results, key=lambda x: x[1], reverse=True)
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

            self.last_search_summary = {
                "source": "search",
                "depth": search_depth,
                "status": "timeout" if self.search_timed_out else "complete",
                "nodes": self.nodes.value,
                "leafs": self.leafs.value,
                "cutoffs": self.ab_cutoffs.value,
                "memo_exact": self.memo_exact_count.value,
                "memo_alpha_cut": self.memo_alpha_cut_count.value,
                "memo_alpha_improve": self.memo_alpha_improve_count.value,
                "memo_beta_decrease": self.memo_beta_decrease_count.value,
                "extensions": self.extention_count.value,
                "tt_upper": self.tt_store_upper.value,
                "tt_lower": self.tt_store_lower.value,
                "tt_exact": self.tt_store_exact.value,
                "completed_roots": self.last_search_completed_roots,
                "root_count": self.last_search_root_count,
            }

            if print_stats and AI_LOG_SEARCH_STATS:
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

            self.search_deadline = None
            return (best_move, best_eval, best_path)
        else:
            self.search_deadline = None
            return ((None, None), None, None)   # No possible moves
           

    def order_root_moves_with_iterative_deepening(self, game, board, root_moves):
        if (
            not self.use_iterative_deepening
            or self.depth < self.iterative_deepening_min_depth
            or len(root_moves) < 2
        ):
            return root_moves

        ordered_moves = list(root_moves)
        original_order = {move: index for index, move in enumerate(ordered_moves)}
        prep_depth = min(self.depth - 1, self.iterative_deepening_prep_depth)

        results = self.search_root_moves_single(game, board, ordered_moves, prep_depth)
        scores = {move: evaluation for move, evaluation, _ in results}
        ordered_moves.sort(
            key=lambda move: (
                -scores.get(move, float("-inf")),
                original_order.get(move, 0),
            )
        )

        return ordered_moves

    def search_root_moves_single(self, game, board, root_moves, depth):
        results = []
        root_alpha = float("-inf")

        for square, move in root_moves:
            temp_game = deepcopy(game)
            temp_board = deepcopy(board)
            result = self.minimax(
                temp_game,
                temp_board,
                depth,
                root_alpha,
                float("inf"),
                True,
                (square, move),
                True,
                0
            )
            results.append(result)
            if result[1] > root_alpha:
                root_alpha = result[1]

        return results


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

        seen = set()
        unique_moves = []
        for square in prioritised_moves:
            if square in seen:
                continue
            seen.add(square)
            unique_moves.append(square)
        return unique_moves

    def get_ordered_moves(self, game, board, for_color, opponent, depth, preferred_move=None):
        ordered_moves = []
        seen = set()
        prioritised_squares = self.get_prioritised_moves(game, board, for_color, opponent)

        for square_order, square in enumerate(prioritised_squares):
            valid_moves = game.get_valid_moves(board, square, for_color)
            if not valid_moves:
                continue

            for move in valid_moves:
                if (square, move) in seen:
                    continue
                seen.add((square, move))
                score = self.score_move(game, board, square, move, for_color)
                if preferred_move == (square, move):
                    score += 30000
                if self.use_killer_history:
                    if (square, move) in self.killer_moves.get(depth, ()):
                        score += 2500
                    score += self.history_scores.get((for_color, square, move), 0)
                ordered_moves.append((score, square_order, square, move))

        ordered_moves.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))
        return [(square, move) for _, _, square, move in ordered_moves]

    def get_piece_ordered_moves(self, game, board, for_color, opponent, preferred_move=None):
        seen = set()
        if preferred_move is None:
            for square in self.get_prioritised_moves(game, board, for_color, opponent):
                valid_moves = game.get_valid_moves(board, square, for_color)
                if valid_moves:
                    for move in valid_moves:
                        if (square, move) in seen:
                            continue
                        seen.add((square, move))
                        yield square, move
            return

        deferred_moves = []
        for square in self.get_prioritised_moves(game, board, for_color, opponent):
            valid_moves = game.get_valid_moves(board, square, for_color)
            if valid_moves:
                for move in valid_moves:
                    if (square, move) in seen:
                        continue
                    seen.add((square, move))
                    if preferred_move == (square, move):
                        yield square, move
                    else:
                        deferred_moves.append((square, move))
        for move in deferred_moves:
            yield move

    def get_moves_for_search(self, game, board, for_color, opponent, depth, preferred_move=None):
        if depth >= 2:
            return self.get_ordered_moves(game, board, for_color, opponent, depth, preferred_move)
        return self.get_piece_ordered_moves(game, board, for_color, opponent, preferred_move)

    def score_move(self, game, board, square, move, for_color):
        piece = board.get_piece(square)
        score = 0

        if for_color == "white":
            attacked = game.attacked_squares_by_black
            defended = game.attacked_squares_by_white
        else:
            attacked = game.attacked_squares_by_white
            defended = game.attacked_squares_by_black

        captured_piece = board.get_piece(move) if board.contains_piece(move) else None
        if captured_piece is not None:
            score += 10000 + (captured_piece.value * 10) - piece.value
        elif (
            isinstance(piece, Pawn)
            and abs(square - move) in (7, 9)
            and game.get_en_passant_target(board) == move
        ):
            score += 10000 + 1000 - piece.value

        if isinstance(piece, Pawn):
            if (piece.color == "white" and move >= 56) or (piece.color == "black" and move <= 7):
                score += 20000

        if square in attacked and square not in defended:
            score += 500
        elif square in attacked:
            score += 100

        if isinstance(piece, King) and abs(square - move) == 2:
            score += 50

        if self.move_likely_gives_check(board, piece, square, move, for_color):
            score += 1200

        return score

    def move_likely_gives_check(self, board, piece, square, move, for_color):
        opponent_king = board.black_king_square if for_color == "white" else board.white_king_square

        if isinstance(piece, Pawn):
            return opponent_king in PAWN_ATTACKS_BY_COLOR[piece.color][move]
        if isinstance(piece, Knight):
            return opponent_king in KNIGHT_MOVES_BY_SQUARE[move]
        if isinstance(piece, King):
            return opponent_king in KING_MOVES_BY_SQUARE[move]

        if not isinstance(piece, (Bishop, Rook, Queen)):
            return False

        allowed_moves = piece.moves
        rays = SLIDING_RAYS[move]
        board_squares = board.board
        for direction in allowed_moves:
            for target_square in rays[direction]:
                if target_square == opponent_king:
                    return True
                if target_square == square:
                    continue
                if board_squares[target_square] is not None:
                    break
        return False

    def remember_cutoff_move(self, game, board, depth, color, square, move):
        if self.is_noisy_move(game, board, square, move):
            return

        killers = list(self.killer_moves.get(depth, ()))
        move_key = (square, move)
        if move_key in killers:
            killers.remove(move_key)
        killers.insert(0, move_key)
        self.killer_moves[depth] = tuple(killers[:2])

        history_key = (color, square, move)
        self.history_scores[history_key] = min(
            2000,
            self.history_scores.get(history_key, 0) + depth * depth,
        )

    def is_noisy_move(self, game, board, square, move):
        piece = board.get_piece(square)
        if board.contains_piece(move):
            return True
        if (
            isinstance(piece, Pawn)
            and abs(square - move) in (7, 9)
            and game.get_en_passant_target(board) == move
        ):
            return True
        if isinstance(piece, Pawn):
            return (piece.color == "white" and move >= 56) or (piece.color == "black" and move <= 7)
        return False

    def should_quiesce(self, game, board):
        last_piece, _, new_square, is_capture = board.last_move
        if is_capture:
            return True
        if game.king_in_check(board, self.color) or game.king_in_check(board, self.opponent):
            return True
        if last_piece is None:
            return False
        if last_piece.color == "white":
            return new_square in game.attacked_squares_by_black
        return new_square in game.attacked_squares_by_white

    def gives_check(self, game, board, square, move, opponent):
        state = game.make_move_for_search(board, square, move)
        try:
            return game.king_in_check(board, opponent)
        finally:
            game.unmake_move_for_search(board, state)

    def get_quiescence_moves(self, game, board, for_color, opponent, include_checks=False):
        moves = []
        seen = set()
        for square in self.get_prioritised_moves(game, board, for_color, opponent):
            valid_moves = game.get_valid_moves(board, square, for_color)
            if not valid_moves:
                continue
            for move in valid_moves:
                if (square, move) in seen:
                    continue
                seen.add((square, move))
                is_noisy = self.is_noisy_move(game, board, square, move)
                is_check = False
                if include_checks and not is_noisy:
                    is_check = self.gives_check(game, board, square, move, opponent)
                if is_noisy or is_check:
                    score = self.score_move(game, board, square, move, for_color)
                    if is_check:
                        score += 1500
                    moves.append((score, square, move))
        moves.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [(square, move) for _, square, move in moves]

    def quiescence(self, game, board, alpha, beta, maximize, remaining_depth):
        self.nodes.value += 1
        self.check_search_deadline()

        if game.repetition:
            return self.repetition_evaluation(game, board)

        stand_pat = self.evaluate(game, board)
        if remaining_depth <= 0:
            self.leafs.value += 1
            return stand_pat

        if maximize:
            if stand_pat >= beta:
                self.ab_cutoffs.value += 1
                return stand_pat
            alpha = max(alpha, stand_pat)
            moves = self.get_quiescence_moves(
                game,
                board,
                self.color,
                self.opponent,
                include_checks=self.use_quiescence_checks and remaining_depth > 0,
            )
            if not moves:
                self.leafs.value += 1
                return alpha

            for square, move in moves:
                state = game.make_move_for_search(board, square, move)
                try:
                    evaluation = self.quiescence(game, board, alpha, beta, False, remaining_depth - 1)
                finally:
                    game.unmake_move_for_search(board, state)

                if evaluation >= beta:
                    self.ab_cutoffs.value += 1
                    return evaluation
                alpha = max(alpha, evaluation)
            return alpha

        if stand_pat <= alpha:
            self.ab_cutoffs.value += 1
            return stand_pat
        beta = min(beta, stand_pat)
        moves = self.get_quiescence_moves(
            game,
            board,
            self.opponent,
            self.color,
            include_checks=self.use_quiescence_checks and remaining_depth > 0,
        )
        if not moves:
            self.leafs.value += 1
            return beta

        for square, move in moves:
            state = game.make_move_for_search(board, square, move)
            try:
                evaluation = self.quiescence(game, board, alpha, beta, True, remaining_depth - 1)
            finally:
                game.unmake_move_for_search(board, state)

            if evaluation <= alpha:
                self.ab_cutoffs.value += 1
                return evaluation
            beta = min(beta, evaluation)
        return beta

    
    def evaluate(self, game, board):
        game.evaluate_board(board)
        if self.color == "black":
            evaluation = (game.black_eval - game.white_eval)
        else:
            evaluation = (game.white_eval - game.black_eval)
        return evaluation

    def draw_evaluation(self, game, board):
        evaluation = self.evaluate(game, board)
        if evaluation > 250:
            return -max(300, evaluation)
        return 0

    def repetition_evaluation(self, game, board):
        return self.draw_evaluation(game, board)

    def stalemate_evaluation(self, game, board):
        return self.draw_evaluation(game, board)

   
    def minimax(self, game, board, depth, alpha, beta, maximize, last_move, initial_call, depth_limit_count):
        self.nodes.value += 1
        self.check_search_deadline()
        original_alpha = alpha
        original_beta = beta
        move_path = []
        choosen_move = last_move

        if game.repetition:
            self.leafs.value += 1
            return last_move, self.repetition_evaluation(game, board), move_path

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
                    if game.repetition:
                        self.leafs.value += 1
                        evaluation = self.repetition_evaluation(game, board)
                    elif self.use_quiescence and self.should_quiesce(game, board):
                        evaluation = self.quiescence(game, board, alpha, beta, maximize, self.quiescence_depth)
                    else:
                        self.leafs.value += 1
                        evaluation = self.evaluate(game, board)
                    return last_move, evaluation, move_path
                    
            else:
                # end
                if game.repetition:
                    self.leafs.value += 1
                    evaluation = self.repetition_evaluation(game, board)
                elif self.use_quiescence and self.should_quiesce(game, board):
                    evaluation = self.quiescence(game, board, alpha, beta, maximize, self.quiescence_depth)
                else:
                    self.leafs.value += 1
                    evaluation = self.evaluate(game, board)
                return last_move, evaluation, move_path
                
        board_state = game.get_position_key(board)
        preferred_move = None

        if self.use_memo and not initial_call:
            entry = self.transposition_table.get(board_state)
            if entry is not None:
                move_tt, stored_depth, stored_eval, bound_type = entry
                preferred_move = move_tt
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
                moves_to_check = self.get_moves_for_search(game, board, self.color, self.opponent, depth, preferred_move)
                searched_moves = 0
                for square, move in moves_to_check:
                    if beta <= alpha:
                        break # Beta cut-off
                    maximizer_valid_move_found = True
                    state = game.make_move_for_search(board, square, move)
                    try:
                        if self.use_pvs and searched_moves > 0 and depth >= 2:
                            _, evaluation, path = self.minimax(
                                game,
                                board,
                                depth-1,
                                alpha,
                                alpha + 1,
                                False,                # minimizing
                                (square, move),
                                initial_call=False,
                                depth_limit_count=depth_limit_count
                            )
                            if alpha < evaluation < beta:
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
                        else:
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
                    searched_moves += 1

                    if evaluation > max_eval:
                        max_eval = evaluation
                        choosen_move = (square, move)
                        move_path = [(square, move)] + path

                    alpha = max(alpha, evaluation)
                    if beta <= alpha:
                        cutoff_occured = True
                        self.ab_cutoffs.value += 1
                        if self.use_killer_history:
                            self.remember_cutoff_move(game, board, depth, self.color, square, move)
                        break # beta cutoff

                if not maximizer_valid_move_found:
                    choosen_move = (None, None)
                elif self.use_memo and choosen_move != (None, None):
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
                        
            if choosen_move == (None,None):  # No valid moves have been found
                self.leafs.value += 1
                if game.king_in_check(board, self.color):
                    self.transposition_table[board_state] = (choosen_move, depth, (-MATE-(depth*1000)), "EXACT")
                    return choosen_move, (-MATE-(depth*1000)), move_path  # Checkmate
                else:
                    evaluation = self.stalemate_evaluation(game, board)
                    self.transposition_table[board_state] = (choosen_move, depth, evaluation, "EXACT")
                    return choosen_move, evaluation, move_path  # Stalemate
            else:
                return choosen_move, max_eval, move_path
            

        # minimizer
        else:
            min_eval = float("inf")
            minimizer_valid_move_found = False
            moves_to_check = self.get_moves_for_search(game, board, self.opponent, self.color, depth, preferred_move)
            searched_moves = 0
            for square, move in moves_to_check:
                if beta <= alpha:
                    break # cut-off
                minimizer_valid_move_found = True
                state = game.make_move_for_search(board, square, move)
                try:
                    if self.use_pvs and searched_moves > 0 and depth >= 2:
                        _, evaluation, path = self.minimax(
                            game,
                            board,
                            depth-1,
                            beta - 1,
                            beta,
                            True,                 # maximizing
                            (square, move),
                            initial_call=False,
                            depth_limit_count=depth_limit_count
                        )
                        if alpha < evaluation < beta:
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
                    else:
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
                searched_moves += 1

                if evaluation < min_eval:
                    min_eval = evaluation
                    choosen_move = (square, move)
                    move_path = [(square, move)] + path

                beta = min(beta, evaluation)
                if beta <= alpha:
                    cutoff_occured = True
                    self.ab_cutoffs.value += 1
                    if self.use_killer_history:
                        self.remember_cutoff_move(game, board, depth, self.opponent, square, move)
                    break # cut-off

            if not minimizer_valid_move_found: # No valid moves for minimzier
                choosen_move = (None, None)
            elif self.use_memo and choosen_move != (None, None):
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

            if choosen_move == (None, None):  # No valid moves have been found
                self.leafs.value += 1
                if game.king_in_check(board, self.opponent):
                    if self.use_memo:
                        self.transposition_table[board_state] = (choosen_move, depth, (MATE+(depth*1000)), "EXACT")
                    return choosen_move, (MATE+(depth*1000)), move_path  # Checkmate
                else:
                    evaluation = self.stalemate_evaluation(game, board)
                    if self.use_memo:
                        self.transposition_table[board_state] = (choosen_move, depth, evaluation, "EXACT")
                    return choosen_move, evaluation, move_path  # Stalemate
            else:
                return choosen_move, min_eval, move_path
