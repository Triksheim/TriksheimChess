import argparse
import sys
import time

from AI import ChessAI, handle_ai_move
from board import ChessBoard
from constants import STARTING_FEN, TEST2_FEN, TEST_FEN
from game import ChessGame
from pieces import King, Pawn, Queen, Rook


OPEN_TACTICAL_FEN = "r3k2r/pppq1ppp/2npbn2/3Np3/2B1P3/2N2Q2/PPP2PPP/R3K2R"


def build_game_from_fen(fen):
    board = ChessBoard()
    game = ChessGame()
    game.load_position_from_fen(board, fen)
    return game, board


def legal_moves(game, board):
    moves = []
    for square, _ in board.get_squares_with_piece(game.turn):
        for move in game.get_valid_moves(board, square, game.turn) or []:
            moves.append((square, move))
    return moves


def uci_to_square(text):
    file_idx = ord(text[0]) - ord("a")
    rank = int(text[1]) - 1
    return rank * 8 + file_idx


def uci_to_move(text):
    return uci_to_square(text[:2]), uci_to_square(text[2:4])


def build_game_from_moves(move_history):
    game, board = build_game_from_fen(STARTING_FEN)
    for uci in move_history:
        move = uci_to_move(uci)
        if move not in legal_moves(game, board):
            raise ValueError(f"Illegal replay move {uci} for {game.turn}")
        game.execute_move(board, move[0], move[1])
        game.update_gamestate(board)
        game.evaluate_board(board)
    return game, board


def perft(game, board, depth):
    if depth == 0:
        return 1

    total = 0
    for square, move in legal_moves(game, board):
        state = game.make_move_for_search(board, square, move)
        try:
            total += perft(game, board, depth - 1)
        finally:
            game.unmake_move_for_search(board, state)
    return total


def run_check(name, check_func):
    start = time.perf_counter()
    try:
        details = check_func()
        status = "PASS"
    except AssertionError as exc:
        details = str(exc)
        status = "FAIL"
    elapsed = time.perf_counter() - start
    print(f"{status} {name}: {details} ({elapsed:.3f}s)")
    return status == "PASS"


def check_starting_perft():
    expected = {1: 20, 2: 400, 3: 8902}
    game, board = build_game_from_fen(STARTING_FEN)
    observed = {}

    for depth in expected:
        observed[depth] = perft(game, board, depth)

    assert observed == expected, f"expected {expected}, got {observed}"
    return f"perft={observed}"


def check_en_passant_int_board_consistency():
    board = ChessBoard()
    game = ChessGame()

    board.add_piece(King("white"), 4)
    board.add_piece(King("black"), 60)
    board.add_piece(Pawn("white"), 36)
    board.add_piece(Pawn("black"), 51)

    board.move_piece(51, 35)
    game.turn = "white"
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")

    legal = game.get_valid_moves(board, 36, "white") or []
    assert 43 in legal, f"expected en passant square 43 in {legal}"

    game.execute_move(board, 36, 43)

    assert board.board[35] is None, "captured pawn still present on board"
    assert board.int_board[35] is None, "captured pawn still present on int_board"
    assert board.int_board[43] == 1, f"capturing pawn missing from int_board[43]: {board.int_board[43]}"
    return "board and int_board agree after en passant"


def check_position_key_castling_rights():
    game_a = ChessGame()
    board_a = ChessBoard()
    board_a.add_piece(King("white"), 4)
    board_a.add_piece(Rook("white"), 7)
    board_a.add_piece(King("black"), 60)

    game_b = ChessGame()
    board_b = ChessBoard()
    board_b.add_piece(King("white"), 4)
    board_b.add_piece(Rook("white"), 7)
    board_b.add_piece(King("black"), 60)
    board_b.get_piece(7).not_moved = False

    assert tuple(board_a.int_board) == tuple(board_b.int_board), "test setup should have identical piece placement"
    assert game_a.get_position_key(board_a) != game_b.get_position_key(board_b), "castling rights missing from key"
    return "same pieces with different castling rights produce different keys"


def check_position_key_en_passant_rights():
    game_a = ChessGame()
    board_a = ChessBoard()
    board_a.add_piece(King("white"), 4)
    board_a.add_piece(King("black"), 60)
    board_a.add_piece(Pawn("white"), 36)
    board_a.add_piece(Pawn("black"), 51)
    board_a.move_piece(51, 35)
    game_a.turn = "white"

    game_b = ChessGame()
    board_b = ChessBoard()
    board_b.add_piece(King("white"), 4)
    board_b.add_piece(King("black"), 60)
    board_b.add_piece(Pawn("white"), 36)
    board_b.add_piece(Pawn("black"), 35)
    game_b.turn = "white"

    assert tuple(board_a.int_board) == tuple(board_b.int_board), "test setup should have identical piece placement"
    assert game_a.get_position_key(board_a) != game_b.get_position_key(board_b), "en-passant rights missing from key"
    return "same pieces with different en-passant rights produce different keys"


def check_gui_ai_search_does_not_mutate_live_position():
    game, board = build_game_from_fen(TEST_FEN)
    game.turn = "black"
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")
    game.evaluate_board(board)

    before = (
        list(board.board),
        list(board.int_board),
        board.last_move,
        list(board.move_log),
        list(board.board_state_log),
        board.white_king_square,
        board.black_king_square,
        game.turn,
        game.repetition,
        game.move_count,
        list(game.attacked_squares_by_white),
        list(game.attacked_squares_by_black),
        game.white_eval,
        game.black_eval,
    )

    ai = ChessAI(depth=3, depth_inc=0, ai_color="black")
    ai.use_multiprocessing = False
    ai.use_opening_book = False
    try:
        handle_ai_move(ai, game, board)
    finally:
        ai.close_pool()

    after = (
        list(board.board),
        list(board.int_board),
        board.last_move,
        list(board.move_log),
        list(board.board_state_log),
        board.white_king_square,
        board.black_king_square,
        game.turn,
        game.repetition,
        game.move_count,
        list(game.attacked_squares_by_white),
        list(game.attacked_squares_by_black),
        game.white_eval,
        game.black_eval,
    )

    assert before == after, "GUI-facing AI search mutated the live game or board"
    assert game.ai_move in legal_moves(game, board), "AI returned an illegal move for the live position"
    return f"live position unchanged while AI selected {game.ai_move}"


def check_winning_ai_avoids_threefold_repetition():
    move_history = (
        "e2e4 b8c6 d2d4 d7d5 b1c3 d5e4 d4d5 c8g4 d1g4 g8f6 "
        "g4d1 d8d6 d5c6 d6d1 c3d1 b7c6 c1f4 a8d8 d1c3 e7e5 "
        "f4e5 f8b4 e5f6 g7f6 g1e2 b4c3 e2c3 f6f5 f1c4 e8g8 "
        "e1g1 d8d2 a1d1 d2c2 d1b1 c2d2 f1d1 d2d1 b1d1 c6c5 "
        "d1d7 g8h8 c4f7 f8c8 f7e6 c8f8 d7c7 a7a6 c7c5 f8d8 "
        "e6f5 e4e3 f2e3 d8g8 c5c7 g8g5 c7h7 h8g8 f5e4 a6a5 "
        "g2g3 g5g4 h7d7 g8f8 d7d8 f8g7 g1h1 g4g5 d8d5 g5d5 "
        "e4d5 g7f6 h1g2 f6e5 e3e4 e5d4 g2f3 d4c5 f3e3 c5b6 "
        "e3d4 a5a4 c3a4 b6b5 a4c3 b5b4 h2h4 b4a5 d4c5 a5a6 "
        "b2b4 a6a7 b4b5 a7b8 c5c6 b8a7 a2a4 a7a8 b5b6 a8b8 "
        "d5e6 b8a8 e6d5 a8b8 d5e6 b8a8"
    ).split()
    game, board = build_game_from_moves(move_history)

    ai = ChessAI(depth=5, depth_inc=1, ai_color="white")
    ai.use_multiprocessing = False
    ai.use_opening_book = False
    try:
        move, evaluation, _ = ai.generate_move(game, board)
    finally:
        ai.close_pool()

    bad_repetition_move = (44, 35)
    assert move != bad_repetition_move, "winning AI chose the immediate threefold repetition move Be6-d5"
    assert move in legal_moves(game, board), "AI returned an illegal move in repetition regression"
    return f"selected {move} eval={evaluation} instead of repeating"


def build_stalemate_trap_position():
    board = ChessBoard()
    game = ChessGame()
    board.add_piece(King("white"), 0)   # a1
    board.add_piece(Queen("white"), 1)  # b1
    board.add_piece(King("black"), 63)  # h8
    game.turn = "white"
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")
    game.evaluate_board(board)
    return game, board


def check_winning_ai_avoids_immediate_stalemate():
    game, board = build_stalemate_trap_position()
    bad_stalemate_move = (1, 46)  # Qb1-g6

    assert bad_stalemate_move in legal_moves(game, board), "test stalemate trap move is not legal"
    state = game.make_move_for_search(board, *bad_stalemate_move)
    try:
        assert not legal_moves(game, board), "trap move should leave black with no legal moves"
        assert not game.king_in_check(board, "black"), "trap move should be stalemate, not checkmate"
    finally:
        game.unmake_move_for_search(board, state)

    ai = ChessAI(depth=3, depth_inc=0, ai_color="white")
    ai.use_multiprocessing = False
    ai.use_opening_book = False
    try:
        move, evaluation, _ = ai.generate_move(game, board)
    finally:
        ai.close_pool()

    assert move != bad_stalemate_move, "winning AI chose an immediate stalemate"
    assert move in legal_moves(game, board), "AI returned an illegal move in stalemate regression"
    return f"selected {move} eval={evaluation} instead of stalemating"


def check_stalemate_draw_score_depends_on_position():
    game, board = build_stalemate_trap_position()
    state = game.make_move_for_search(board, 1, 46)  # Qb1-g6 stalemate
    try:
        winning_ai = ChessAI(depth=1, depth_inc=0, ai_color="white")
        losing_ai = ChessAI(depth=1, depth_inc=0, ai_color="black")
        try:
            winning_score = winning_ai.stalemate_evaluation(game, board)
            losing_score = losing_ai.stalemate_evaluation(game, board)
        finally:
            winning_ai.close_pool()
            losing_ai.close_pool()
    finally:
        game.unmake_move_for_search(board, state)

    assert winning_score < 0, f"winning AI should treat stalemate as bad, got {winning_score}"
    assert losing_score == 0, f"losing AI should accept stalemate as a draw, got {losing_score}"
    return f"winning_score={winning_score}, losing_score={losing_score}"


def run_ai_case(
    name,
    fen,
    color,
    depth,
    use_multiprocessing=False,
    use_iterative_deepening=False,
    use_dynamic_depth=False,
    soft_time_limit=None,
    time_limit=None,
):
    game, board = build_game_from_fen(fen)
    game.turn = color
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")
    root_moves = len(legal_moves(game, board))

    ai = ChessAI(depth=depth, depth_inc=0, ai_color=color)
    ai.use_multiprocessing = use_multiprocessing
    ai.use_memo = True
    ai.use_iterative_deepening = use_iterative_deepening
    ai.use_dynamic_depth = use_dynamic_depth
    ai.soft_time_limit = soft_time_limit
    ai.time_limit = time_limit

    start = time.perf_counter()
    try:
        move, evaluation, path = ai.generate_move(game, board)
        elapsed = time.perf_counter() - start
    finally:
        ai.close_pool()

    return {
        "name": name,
        "move": move,
        "eval": evaluation,
        "path_len": len(path or []),
        "elapsed": elapsed,
        "depth": depth,
        "root_moves": root_moves,
    }


def run_ai_ep_case(depth, use_multiprocessing=False, use_iterative_deepening=False, use_dynamic_depth=False, soft_time_limit=None, time_limit=None):
    board = ChessBoard()
    game = ChessGame()

    board.add_piece(King("white"), 4)
    board.add_piece(King("black"), 60)
    board.add_piece(Pawn("white"), 36)
    board.add_piece(Pawn("black"), 51)
    board.move_piece(51, 35)

    game.turn = "white"
    game.update_attacked_squares(board, "white")
    game.update_attacked_squares(board, "black")
    game.evaluate_board(board)
    root_moves = len(legal_moves(game, board))

    ai = ChessAI(depth=depth, depth_inc=0, ai_color="white")
    ai.use_multiprocessing = use_multiprocessing
    ai.use_memo = True
    ai.use_iterative_deepening = use_iterative_deepening
    ai.use_dynamic_depth = use_dynamic_depth
    ai.soft_time_limit = soft_time_limit
    ai.time_limit = time_limit

    start = time.perf_counter()
    try:
        move, evaluation, path = ai.generate_move(game, board)
        elapsed = time.perf_counter() - start
    finally:
        ai.close_pool()

    return {
        "name": "en_passant_available",
        "move": move,
        "eval": evaluation,
        "path_len": len(path or []),
        "elapsed": elapsed,
        "depth": depth,
        "root_moves": root_moves,
    }


def run_ai_benchmarks(
    include_very_deep=False,
    include_depth5=False,
    include_depth6=False,
    include_depth7=False,
    use_multiprocessing=False,
    use_iterative_deepening=False,
    use_dynamic_depth=False,
    soft_time_limit=None,
    time_limit=None,
):
    mode = "multiprocessing" if use_multiprocessing else "single-process"
    if use_iterative_deepening:
        mode += " + iterative-deepening"
    if use_dynamic_depth:
        soft_label = 4.0 if soft_time_limit is None else soft_time_limit
        limit_label = 15.0 if time_limit is None else time_limit
        mode += f" + dynamic-depth(soft={soft_label:.2f}s hard={limit_label:.2f}s)"
    print(f"AI mode: {mode}")

    quick_cases = [
        run_ai_case("starting_position", STARTING_FEN, "white", depth=2, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        run_ai_case("test_fen_black", TEST_FEN, "black", depth=2, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        run_ai_ep_case(depth=2, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
    ]

    print("AI benchmarks:")
    for case in quick_cases:
        print(
            "  "
            f"{case['name']}: depth={case['depth']} root_moves={case['root_moves']} "
            f"move={case['move']} eval={case['eval']} "
            f"path_len={case['path_len']} time={case['elapsed']:.3f}s"
        )

    deep_cases = [
        run_ai_case("test2_fen_white_deep", TEST2_FEN, "white", depth=3, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        run_ai_case("open_tactical_white_deep", OPEN_TACTICAL_FEN, "white", depth=3, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        run_ai_case("open_tactical_black_deep", OPEN_TACTICAL_FEN, "black", depth=3, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
    ]

    print("Deep AI benchmarks:")
    for case in deep_cases:
        print(
            "  "
            f"{case['name']}: depth={case['depth']} root_moves={case['root_moves']} "
            f"move={case['move']} eval={case['eval']} "
            f"path_len={case['path_len']} time={case['elapsed']:.3f}s"
        )

    if include_very_deep:
        very_deep_cases = [
            run_ai_case("test2_fen_white_very_deep", TEST2_FEN, "white", depth=4, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
            run_ai_case("open_tactical_white_very_deep", OPEN_TACTICAL_FEN, "white", depth=4, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        ]

        print("Very deep AI benchmarks:")
        for case in very_deep_cases:
            print(
                "  "
                f"{case['name']}: depth={case['depth']} root_moves={case['root_moves']} "
                f"move={case['move']} eval={case['eval']} "
                f"path_len={case['path_len']} time={case['elapsed']:.3f}s"
            )
    else:
        print("Very deep AI benchmarks: skipped, use --very-deep")

    if not include_depth5:
        print("Depth-5 AI benchmarks: skipped, use --depth5")
    else:
        depth5_cases = [
            run_ai_case("test2_fen_white_depth5", TEST2_FEN, "white", depth=5, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
            run_ai_case("open_tactical_white_depth5", OPEN_TACTICAL_FEN, "white", depth=5, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        ]

        print("Depth-5 AI benchmarks:")
        for case in depth5_cases:
            print(
                "  "
                f"{case['name']}: depth={case['depth']} root_moves={case['root_moves']} "
                f"move={case['move']} eval={case['eval']} "
                f"path_len={case['path_len']} time={case['elapsed']:.3f}s"
            )

    if not include_depth6:
        print("Depth-6 AI benchmarks: skipped, use --depth6")
    else:
        depth6_cases = [
            run_ai_case("test2_fen_white_depth6", TEST2_FEN, "white", depth=6, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
            run_ai_case("open_tactical_white_depth6", OPEN_TACTICAL_FEN, "white", depth=6, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        ]

        print("Depth-6 AI benchmarks:")
        for case in depth6_cases:
            print(
                "  "
                f"{case['name']}: depth={case['depth']} root_moves={case['root_moves']} "
                f"move={case['move']} eval={case['eval']} "
                f"path_len={case['path_len']} time={case['elapsed']:.3f}s"
            )

    if not include_depth7:
        print("Depth-7 AI benchmarks: skipped, use --depth7")
        return

    depth7_cases = [
        run_ai_case("test2_fen_white_depth7", TEST2_FEN, "white", depth=7, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
        run_ai_case("open_tactical_white_depth7", OPEN_TACTICAL_FEN, "white", depth=7, use_multiprocessing=use_multiprocessing, use_iterative_deepening=use_iterative_deepening, use_dynamic_depth=use_dynamic_depth, soft_time_limit=soft_time_limit, time_limit=time_limit),
    ]

    print("Depth-7 AI benchmarks:")
    for case in depth7_cases:
        print(
            "  "
            f"{case['name']}: depth={case['depth']} root_moves={case['root_moves']} "
            f"move={case['move']} eval={case['eval']} "
            f"path_len={case['path_len']} time={case['elapsed']:.3f}s"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--very-deep",
        action="store_true",
        help="Run depth-4 AI benchmarks that can take close to a minute.",
    )
    parser.add_argument(
        "--multiprocessing",
        action="store_true",
        help="Run AI benchmarks with the engine's multiprocessing mode enabled.",
    )
    parser.add_argument(
        "--depth5",
        action="store_true",
        help="Run depth-5 AI benchmarks. Prefer combining with --multiprocessing.",
    )
    parser.add_argument(
        "--depth6",
        action="store_true",
        help="Run depth-6 AI benchmarks. Prefer combining with --multiprocessing.",
    )
    parser.add_argument(
        "--depth7",
        action="store_true",
        help="Run depth-7 AI benchmarks. Prefer combining with --multiprocessing and --dynamic-depth.",
    )
    parser.add_argument(
        "--iterative-deepening",
        action="store_true",
        help="Enable the AI's iterative-deepening root ordering during benchmarks.",
    )
    parser.add_argument(
        "--dynamic-depth",
        action="store_true",
        help="Use iterative deepening with a time limit instead of fixed-depth search.",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=15.0,
        help="Time limit in seconds for --dynamic-depth.",
    )
    parser.add_argument(
        "--soft-time-limit",
        type=float,
        default=4.0,
        help="Normal-move time limit in seconds for --dynamic-depth.",
    )
    args = parser.parse_args()

    print(f"Python: {sys.version.split()[0]}")
    checks = [
        run_check("starting_position_perft", check_starting_perft),
        run_check("en_passant_int_board_consistency", check_en_passant_int_board_consistency),
        run_check("position_key_castling_rights", check_position_key_castling_rights),
        run_check("position_key_en_passant_rights", check_position_key_en_passant_rights),
        run_check("gui_ai_search_does_not_mutate_live_position", check_gui_ai_search_does_not_mutate_live_position),
        run_check("winning_ai_avoids_threefold_repetition", check_winning_ai_avoids_threefold_repetition),
        run_check("winning_ai_avoids_immediate_stalemate", check_winning_ai_avoids_immediate_stalemate),
        run_check("stalemate_draw_score_depends_on_position", check_stalemate_draw_score_depends_on_position),
    ]
    run_ai_benchmarks(
        include_very_deep=args.very_deep,
        include_depth5=args.depth5,
        include_depth6=args.depth6,
        include_depth7=args.depth7,
        use_multiprocessing=args.multiprocessing,
        use_iterative_deepening=args.iterative_deepening,
        use_dynamic_depth=args.dynamic_depth,
        soft_time_limit=args.soft_time_limit,
        time_limit=args.time_limit,
    )

    if not all(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
