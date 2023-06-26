from constants import *
import pygame as pg
from utility import format_time
import copy

# All GUI excluding board

def draw_text(window, font, text, x, y, color=WHITE_COLOR):
    render_text = font.render(text, 1, color)
    window.blit(render_text, (x, y, SQUARE_SIZE, SQUARE_SIZE))

def draw_eval(window, font, game):
    draw_text(window, font, f'White eval: {game.white_eval}', SQUARE_SIZE/2, BOARD_FRAME_WIDTH+10 + 9*SQUARE_SIZE)
    draw_text(window, font, f'Black eval: {game.black_eval}', SQUARE_SIZE/2, (BOARD_FRAME_WIDTH/2)-10 + 0*SQUARE_SIZE)

def draw_move_time(window,game, font, color, time, position_multiplier):
    font = pg.font.Font('freesansbold.ttf', 25)
    if color == "white":
        #draw_text(window, font, f'{format_time(time)}', (COLS-1)*SQUARE_SIZE-20, BOARD_FRAME_WIDTH+15 + position_multiplier*SQUARE_SIZE)
        draw_text(window, font, f'{format_time(game.white_move_clock)}', (COLS-1)*SQUARE_SIZE-20, BOARD_FRAME_WIDTH+15 + position_multiplier*SQUARE_SIZE)
    else:
        #draw_text(window, font, f'{format_time(time)}', (COLS-1)*SQUARE_SIZE-20, (BOARD_FRAME_WIDTH/2)-5 + position_multiplier*SQUARE_SIZE)
        draw_text(window, font, f'{format_time(game.black_move_clock)}', (COLS-1)*SQUARE_SIZE-20, (BOARD_FRAME_WIDTH/2)-5 + position_multiplier*SQUARE_SIZE)

def draw_clock(window, game, font):
    draw_text(window, font, f'{format_time(game.white_clock)}', COLS*SQUARE_SIZE, BOARD_FRAME_WIDTH+10 + 9*SQUARE_SIZE)
    draw_text(window, font, f'{format_time(game.black_clock)}', COLS*SQUARE_SIZE, (BOARD_FRAME_WIDTH/2)-10 + 0*SQUARE_SIZE)


def draw_stats(window, game, font, white_time, black_time):
    #draw_eval(window, font, game)  
    draw_move_time(window, game, font, "black", black_time[-1], 0)
    draw_move_time(window, game, font, "white", white_time[-1], 9)
    draw_clock(window, game, font)

def mouse_click_on_gui(event):
    x = event.pos[0]
    y = event.pos[1]

class Button:
    def __init__(self, player=None, text="button", color=GRAY_COLOR, active_frame_color=LIGHT_GREEN_COLOR, frame_color=WHITE_COLOR, text_color=WHITE_COLOR, width=150, height=50, position=(1000,500), font_size=20):
        self.active = False
        self.enabled = True
        self.player = player
        self.text = text
        self.color = color
        self.current_frame_color = frame_color
        self.active_frame_color = active_frame_color
        self.frame_color = frame_color
        self.text_color = text_color
        self.width = width
        self.height = height
        self.x = position[0]
        self.y = position[1]
        self.font = pg.font.Font('freesansbold.ttf', font_size)

    def activate(self):
        if self.enabled:
            self.active = True
            self.current_frame_color = copy.copy(self.active_frame_color)

    def deactivate(self):
        self.active = False
        self.current_frame_color = copy.copy(self.frame_color)

    def enable(self):
        self.enabled = True
        self.text_color = WHITE_COLOR

    def disable(self, deactivate=True):
        self.enabled = False
        self.text_color = DARK_GRAY_COLOR
        if deactivate:
            self.deactivate()

    def draw(self, window):
        pg.draw.rect(window, self.current_frame_color, (self.x, self.y, self.width, self.height))
        pg.draw.rect(window, self.color, (self.x+5, self.y+5, self.width-10, self.height-10))
        draw_text(window, self.font, self.text, self.x+10, self.y+15, self.text_color)

    
class GUI:
    def __init__(self):
        self.white_settings = PlayerSettings("white")
        self.white_settings.reset()
        self.black_settings = PlayerSettings("black")
        self.black_settings.reset()
        self.start_button = Button(text="Start", frame_color=DARK_GREEN_COLOR, active_frame_color=LIGHT_GREEN_COLOR, color=GRAY_COLOR,width=150, height=50, position=(1025, 600), font_size=30)
        self.buttons = self.list_buttons()

    def list_buttons(self):
        buttons = []
        for btn in self.white_settings.radio_group_player:
            buttons.append(btn)
        for btn in self.white_settings.radio_group_diff:
            buttons.append(btn)
        for btn in self.black_settings.radio_group_player:
            buttons.append(btn)
        for btn in self.black_settings.radio_group_diff:
            buttons.append(btn)
        buttons.append(self.start_button)
        return buttons

    def mouse_click(self, event):
        x = event.pos[0]
        y = event.pos[1]  

        if y > self.black_settings.y[0] and y < self.white_settings.y[0]:
            self.black_settings.mouse_click(event)
        elif y > self.white_settings.y[0]:
            self.white_settings.mouse_click(event)

        elif x > self.start_button.x and x < (self.start_button.x + self.start_button.width)  and \
            y > self.start_button.y and y < (self.start_button.y + self.start_button.height):
            return self.start_pressed()

    def start_pressed(self):
        if not self.start_button.active:
            self.start_button.activate()
            self.start_button.text = "Pause"
        else:
            self.start_button.deactivate()
            self.start_button.text = "Resume"
        return True

    def disable_settings(self):
        self.black_settings.disable()
        self.white_settings.disable()

    def enable_settings(self):
        self.black_settings.enable()
        self.white_settings.enable()

    def draw(self, window):
        self.white_settings.draw(window)
        self.black_settings.draw(window)
        self.start_button.draw(window)


class PlayerSettings:
    def __init__(self, color):
        self.enabled = True
        self.radio_group_player = []
        self.radio_group_diff = []
        self.color = color
        self.width = 310
        self.height = 115
        button_labels = ["Player", "CPU", "Easy", "Medium", "Hard"]
        self.x = (950, 1100, 950, 1050 ,1150)
        width = (150, 150, 100, 100, 100)
        if color == "white":
            self.frame_color = LIGHT_SQUARE_COLOR
            self.y = (840, 840, 895 ,895 ,895)
        else:
            self.frame_color = DARK_SQUARE_COLOR
            self.y = (715, 715 ,770, 770 ,770)

        for i, label in enumerate(button_labels):
            name = f'{label.lower()}'
            if i < 2:
                self.radio_group_player.append(Button(player=color, text=label, frame_color=self.frame_color, position=(self.x[i],self.y[i]), width=width[i]))
            else:
                self.radio_group_diff.append(Button(player=color, text=label, frame_color=self.frame_color, position=(self.x[i],self.y[i]), width=width[i] ))

    def disable(self):
        self.enabled = False
        for btn in self.radio_group_player:
            btn.disable(deactivate=False)
        for btn in self.radio_group_diff:
            btn.disable(deactivate=False)

    def enable(self):
        self.enabled = True
        for btn in self.radio_group_player:
            btn.enable()
        for btn in self.radio_group_diff:
            btn.enable()


    def reset(self):
        if self.color == "white":
            self.radio_group_player[0].activate()
            for btn in self.radio_group_diff:
                btn.deactivate()
        else:
            self.radio_group_player[1].activate()
            for btn in self.radio_group_diff:
                btn.enable()
            self.radio_group_diff[1].activate()

    def mouse_click(self, event):
        if not self.enabled:
            return
        x = event.pos[0]
        y = event.pos[1]
       
        for btn in self.radio_group_player:
            if x > btn.x and x < (btn.x + btn.width) and y > btn.y and y < (btn.y + btn.height):
                if btn.text == "CPU":
                    if not btn.active:
                        for button in self.radio_group_diff:
                            button.enable()
                        self.radio_group_diff[0].activate()
                        self.radio_group_diff[1].deactivate()
                        self.radio_group_diff[2].deactivate()
                else:
                    for button in self.radio_group_diff:
                        button.disable()
                for button in self.radio_group_player:
                    if button != btn:
                        button.deactivate()
                btn.activate()
                

        for btn in self.radio_group_diff:
            if x > btn.x and x < (btn.x + btn.width) and y > btn.y and y < (btn.y + btn.height):
                btn.activate()
                for button in self.radio_group_diff:
                    if button != btn:
                        button.deactivate()
                       
                
    def draw(self, window):
        pg.draw.rect(window, self.frame_color, (self.x[0]-5, self.y[0]-5 , self.width, self.height))
        for btn in self.radio_group_player:
            btn.draw(window)
        for btn in self.radio_group_diff:
            btn.draw(window)