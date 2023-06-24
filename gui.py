from constants import *

# All GUI excluding board

def draw_text(window, font, text, x, y, color=WHITE_COLOR):
    render_text = font.render(text, 1, color)
    window.blit(render_text, (x, y, SQUARE_SIZE, SQUARE_SIZE))

def draw_eval(window, font, game):
    draw_text(window, font, f'White eval: {game.white_eval}', SQUARE_SIZE/2, BOARD_FRAME_WIDTH+10 + 9*SQUARE_SIZE)
    draw_text(window, font, f'Black eval: {game.black_eval}', SQUARE_SIZE/2, (BOARD_FRAME_WIDTH/2)-10 + 0*SQUARE_SIZE)

def draw_move_time(window, font, color, time, position_multiplier):
    if color == "white":
        draw_text(window, font, f'{time:.2f}s', 4*SQUARE_SIZE, BOARD_FRAME_WIDTH+10 + position_multiplier*SQUARE_SIZE)
    else:
        draw_text(window, font, f'{time:.2f}s', 4*SQUARE_SIZE, (BOARD_FRAME_WIDTH/2)-10 + position_multiplier*SQUARE_SIZE)

def draw_stats(window, game, font, white_time, black_time):
    draw_eval(window, font, game)  
    draw_move_time(window, font, "black", black_time[-1], 0)
    draw_move_time(window, font, "white", white_time[-1], 9)