from constants import *
import pygame as pg
import utility
import copy
 
class GUI:
    def __init__(self):
        self.board = BoardGUI()
        self.white_settings = PlayerSettings("white")
        self.black_settings = PlayerSettings("black")
        self.move_log = MoveLog()
        self.start_button = Button(text="   Play", frame_color=DARK_GREEN_COLOR, active_frame_color=LIGHT_GRAY_COLOR, color=GRAY_COLOR,width=200, height=75, position=(1000, 450), font_size=45)
        self.reset_button = Button(text="   Reset", frame_color=LIGHT_GRAY_COLOR, active_frame_color=LIGHT_GREEN_COLOR, color=GRAY_COLOR,width=150, height=50, position=(2000, 2000), font_size=30)
        self.buttons = self.list_buttons()
        self.white_player_capture = PlayerCaptureStats("white")
        self.black_player_capture = PlayerCaptureStats("black")
        self.font35 = pg.font.Font('freesansbold.ttf', 35)
        self.font25 = pg.font.Font('freesansbold.ttf', 25)
        

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
        buttons.append(self.reset_button)
        return buttons

    def mouse_click(self, event):
        x = event.pos[0]
        y = event.pos[1]  

        if y >= self.black_settings.y[0] and y <= (self.black_settings.y[0] + self.black_settings.height):
            self.black_settings.mouse_click(event)
        elif y > self.white_settings.y[0] and y <= (self.white_settings.y[0] + self.white_settings.height):
            self.white_settings.mouse_click(event)

        # Start / Pause button press
        elif x > self.start_button.x and x < (self.start_button.x + self.start_button.width)  and \
            y > self.start_button.y and y < (self.start_button.y + self.start_button.height):
            if self.start_button.text == "   Play":
                self.start_button.x = 950
                self.start_button.y = 750
                self.start_button.width = 150
                self.start_button.height = 50
                self.start_button.frame_color = LIGHT_GRAY_COLOR
                self.start_button.font = pg.font.Font('freesansbold.ttf', 30)
                self.reset_button.x = 1100
                self.reset_button.y = 750
                self.reset_button.disable()
            return self.start_pressed()

        elif x > self.reset_button.x and x < (self.reset_button.x + self.reset_button.width)  and \
            y > self.reset_button.y and y < (self.reset_button.y + self.reset_button.height):
            self.reset_pressed()

    def start_pressed(self):
        if not self.start_button.active:
            self.start_button.activate()
            self.start_button.text = "  Pause"
            self.reset_button.disable()
        else:
            self.start_button.deactivate()
            self.start_button.text = " Resume"
            self.reset_button.enable()
        return True

    def reset_pressed(self):
        self.reset_button.activate()

    def disable_settings(self):
        self.black_settings.disable()
        self.white_settings.disable()

    def enable_settings(self):
        self.black_settings.enable()
        self.white_settings.enable()

    def draw(self, window, board, game, selected_square=None, checked_square=None ):
        self.board.draw(window, board, selected_square, checked_square)
        self.white_settings.draw(window)
        self.black_settings.draw(window)
        self.move_log.draw(window, game)
        self.start_button.draw(window)
        self.reset_button.draw(window)
        self.draw_stats(window, game)

        game.eval_piece_count_value(board)
        self.white_player_capture.draw(window, game, board)
        self.black_player_capture.draw(window, game, board)

    def draw_stats(self, window, game):  
        self.draw_move_time(window, game, "black", 0)
        self.draw_move_time(window, game, "white", 9)
        self.draw_clock(window, game)

    def draw_text(self, window, text, x, y, font_size=35,  color=WHITE_COLOR, font=None):
        if not font:
            font = pg.font.Font('freesansbold.ttf', font_size)
        render_text = font.render(text, 1, color)
        window.blit(render_text, (x, y, SQUARE_SIZE, SQUARE_SIZE))

    def draw_text_move_log(self, window, text, x, y, font_size=35, color=WHITE_COLOR):
        font = self.font20
        render_text = font.render(text, 1, color)
        window.blit(render_text, (x, y, SQUARE_SIZE, SQUARE_SIZE))

    def draw_move_time(self, window, game, color, position_multiplier):
        font_size = 25
        if color == "white":
            self.draw_text(window, f'{utility.format_time(game.white_move_clock)}', (COLS-1)*SQUARE_SIZE-20, BOARD_FRAME_WIDTH+15 + position_multiplier*SQUARE_SIZE, font_size, WHITE_COLOR, self.font25)
        else: 
            self.draw_text(window, f'{utility.format_time(game.black_move_clock)}', (COLS-1)*SQUARE_SIZE-20, (BOARD_FRAME_WIDTH/2)-5 + position_multiplier*SQUARE_SIZE, font_size, WHITE_COLOR, self.font25)

    def draw_clock(self, window, game):
        self.draw_text(window, f'{utility.format_time(game.white_clock)}', COLS*SQUARE_SIZE, BOARD_FRAME_WIDTH+10 + 9*SQUARE_SIZE, 35, WHITE_COLOR, self.font35)
        self.draw_text(window, f'{utility.format_time(game.black_clock)}', COLS*SQUARE_SIZE, (BOARD_FRAME_WIDTH/2)-10 + 0*SQUARE_SIZE, 35, WHITE_COLOR, self.font35)


class PlayerCaptureStats(GUI):
    def __init__(self, color="white"):
        self.color = color
        self.piece_mini_images = utility.load_piece_images(width=50, height=50)
        if self.color == "white":
            self.x = LEFT_SIDE_PADDING 
            self.y = 10*SQUARE_SIZE - SQUARE_SIZE/2
        else:
            self.x = LEFT_SIDE_PADDING
            self.y = 0

    def draw(self, window, game, board):
        if self.color == "white":
            opponent = "black"  
        else:
            opponent = "white"
            
        opponent_pieces = board.get_pieces_for_color(opponent)
        piece_count_dict = {}
        for piece in opponent_pieces:
            if piece.name in piece_count_dict:
                piece_count_dict[piece.name] += 1
            else:
                piece_count_dict[piece.name] = 1 

        pieces_base_count = (("Pawn", 8), ("Knight", 2), ("Bishop", 2), ("Rook", 2), ("Queen", 1))
        current_x = self.x
        for name, count in pieces_base_count:
            filename = f'{opponent}_{name.lower()}.png'
            image = self.piece_mini_images[filename]
            if name in piece_count_dict:
                piece_count = piece_count_dict[name]
            else:
                piece_count = 0
            for _ in range (count - piece_count):
                window.blit(image, (current_x, self.y))
                if name == "Pawn":
                    current_x += 10
                else:
                    current_x += 20
            if name == "Pawn":
                current_x += 10
                
        if self.color == "white":
            piece_advantage = game.white_piece_value - game.black_piece_value
        else:
            piece_advantage = game.black_piece_value - game.white_piece_value

        if piece_advantage > 0:
            self.draw_text(window, f'+{piece_advantage}', current_x +30, self.y+15, 25)
        
        


class MoveLog(GUI):
    def __init__(self, x=10*SQUARE_SIZE, y=(3*SQUARE_SIZE)-50, rect_color=GRAY_COLOR):
        self.start_x = x
        self.start_y = y
        self.rect_color = rect_color
        self.font20 = pg.font.Font('freesansbold.ttf', 20)

    def draw(self,window, game):
        x = self.start_x
        y = self.start_y

        pg.draw.rect(window, self.rect_color, (x-50, y-15,  300 , 475 ), 5) # log border outline

        current_y = y
        if len(game.move_notation_log) <= 30:
            offset = 0
            move_count = len(game.move_notation_log)
        else:
            move_count = 30
            offset = len(game.move_notation_log) - move_count
            if offset % 2 != 0:
                move_count -= 1
                offset += 1
            
        for i in range (move_count):
            if i+offset == 0:
                move_num = f'{(i+offset) + 1}.'
                self.draw_text(window, move_num, x-20, current_y, 20, WHITE_COLOR, self.font20)
                self.draw_text(window, game.move_notation_log[i+offset], x + 50, current_y, 20, WHITE_COLOR, self.font20)
            elif (i+offset) % 2 != 0:
                self.draw_text(window, game.move_notation_log[i+offset], x + 150, current_y, 20, WHITE_COLOR, self.font20)
                current_y += 30
                pg.draw.rect(window, self.rect_color, (x-25, current_y-5,  250 , 1 ))
                
            else:
                move_num = f'{((i+offset)//2) + 1}.'
                self.draw_text(window, move_num, x-20, current_y, 20, WHITE_COLOR, self.font20)
                self.draw_text(window, game.move_notation_log[i+offset], x + 50, current_y, 20, WHITE_COLOR, self.font20)
            


class Button(GUI):
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
        self.font_size = font_size
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
        self.draw_text(window, self.text, self.x+10, self.y+15, self.font_size, self.text_color, self.font)   

class PlayerSettings(GUI):
    def __init__(self, color):
        self.enabled = True
        self.radio_group_player = []
        self.radio_group_diff = []
        self.color = color
        self.width = 310
        self.height = 115
        button_labels = ["     Player", "       CPU", "   Easy", "Medium", "  Hard"]
        self.x = (950, 1100, 950, 1050 ,1150)
        width = (150, 150, 100, 100, 100)
        if color == "white":
            self.frame_color = LIGHT_SQUARE_COLOR
            self.y = (840, 840, 895 ,895 ,895)
        else:
            self.frame_color = DARK_SQUARE_COLOR
            begin_at = TOP_PADDING-BOARD_FRAME_WIDTH+5
            self.y = (begin_at, begin_at ,begin_at+55, begin_at+55 ,begin_at+55)

        for i, label in enumerate(button_labels):
            name = f'{label.lower()}'
            if i < 2:
                self.radio_group_player.append(Button(player=color, text=label, frame_color=self.frame_color, position=(self.x[i],self.y[i]), width=width[i]))
            else:
                self.radio_group_diff.append(Button(player=color, text=label, frame_color=self.frame_color, position=(self.x[i],self.y[i]), width=width[i] ))
        self.apply_default_settings()


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


    def apply_default_settings(self):
        if self.color == "white":
            self.radio_group_player[0].activate()
            for btn in self.radio_group_diff:
                btn.disable()
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
                if btn.text == "       CPU":
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



class BoardGUI:
    def __init__(self):
        self.piece_images = utility.load_piece_images(width=SQUARE_SIZE, height=SQUARE_SIZE)
        self.font40 = pg.font.Font('freesansbold.ttf', 40)


    def draw(self, window, board, selected_square=None, checked_square=None):
        window.fill(DARK_GRAY_COLOR)
        self.draw_board(window)
        self.draw_last_move(window, board)
        if checked_square is not None:
            self.draw_checked_square(window, checked_square)
        self.draw_pieces(window, board, selected_square)
        

    def draw_board(self, window):
        for row in range(ROWS):
            for col in range (COLS):
                if row % 2 == 0:
                    if col % 2 == 0:
                        square_color = LIGHT_SQUARE_COLOR
                    else:
                        square_color = DARK_SQUARE_COLOR   
                else: # Alternate row starting color
                    if col % 2 == 0:
                        square_color = DARK_SQUARE_COLOR  
                    else:
                        square_color = LIGHT_SQUARE_COLOR    
                pg.draw.rect(window, square_color, (row*SQUARE_SIZE + LEFT_SIDE_PADDING, col*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))
        self.draw_board_frame(window)

    def draw_board_frame(self, window):
        font = self.font40
        frame_color = BOARD_FRAME_COLOR
        seperator_line_color = LIGHT_GRAY_COLOR
        char_color = WHITE_COLOR
        chars = "ABCDEFGH"
        pg.draw.rect(window, frame_color, (0, TOP_PADDING-BOARD_FRAME_WIDTH,  COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2), BOARD_FRAME_WIDTH )) #top
        pg.draw.rect(window, frame_color, (0, ROWS*SQUARE_SIZE + (TOP_PADDING),  COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2), BOARD_FRAME_WIDTH )) #bot
        pg.draw.rect(window, frame_color, (0, TOP_PADDING-BOARD_FRAME_WIDTH,   BOARD_FRAME_WIDTH, COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2) )) #left
        pg.draw.rect(window, frame_color, (COLS*SQUARE_SIZE + BOARD_FRAME_WIDTH, TOP_PADDING-BOARD_FRAME_WIDTH,   BOARD_FRAME_WIDTH, COLS*SQUARE_SIZE + (BOARD_FRAME_WIDTH*2) )) #right
        for i, char in enumerate(chars):
            char_text = font.render(char, 1 , char_color)
            window.blit(char_text, ((i+1)*SQUARE_SIZE - 15 , ROWS*SQUARE_SIZE + TOP_PADDING + 10, SQUARE_SIZE, SQUARE_SIZE))
            num = str(i+1)
            num_text = font.render(num, 1 , char_color)
            window.blit(num_text, ((BOARD_FRAME_WIDTH/2) - 15 , (8 - (i+1))*SQUARE_SIZE + TOP_PADDING + (BOARD_FRAME_WIDTH/2) + 5, SQUARE_SIZE, SQUARE_SIZE))
        pg.draw.rect(window, seperator_line_color, (BOARD_FRAME_WIDTH-5, TOP_PADDING-5,  COLS*SQUARE_SIZE+5 , 5 )) #top
        pg.draw.rect(window, seperator_line_color, (BOARD_FRAME_WIDTH-5, ROWS*SQUARE_SIZE + (TOP_PADDING),  COLS*SQUARE_SIZE + 5, 5 )) #bot
        pg.draw.rect(window, seperator_line_color, (BOARD_FRAME_WIDTH-5, TOP_PADDING-5,   5, COLS*SQUARE_SIZE + 5 )) #left
        pg.draw.rect(window, seperator_line_color, (COLS*SQUARE_SIZE + BOARD_FRAME_WIDTH, TOP_PADDING-5,   5, COLS*SQUARE_SIZE + 10) ) #right


    def draw_pieces(self, window, board, selected_square):
        for square, piece in enumerate(board.get()):
            if piece is not None and square != selected_square:
                row = square // 8
                col = square % 8
                filename = f'{piece.color}_{piece.name.lower()}.png'
                image = self.piece_images[filename]
                window.blit(image, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING))
        

    def draw_selected_piece(self, window, board, selected_square, mouse_cords):
        piece = board.get_piece(selected_square)
        x_cor = mouse_cords[0]
        y_cor = mouse_cords[1]
        #print(x_cor, y_cor)
        filename = f'{piece.color}_{piece.name.lower()}.png'
        image = self.piece_images[filename]
        window.blit(image, (x_cor-(SQUARE_SIZE/2), y_cor-(SQUARE_SIZE/2)))
        
    def draw_last_move(self, window, board):
        if board.last_move[2] or board.last_move[2] == 0:
            old_square = board.last_move[1]
            new_square = board.last_move[2]
            row =  new_square // 8
            col = new_square % 8
            pg.draw.rect(window, GRAY_COLOR, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))
            row =  old_square // 8
            col = old_square % 8
            pg.draw.rect(window, LIGHT_GRAY_COLOR, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))

    def draw_checked_square(self, window, square):
            row =  square // 8
            col = square % 8
            pg.draw.rect(window, CHECK_COLOR, (col*SQUARE_SIZE + LEFT_SIDE_PADDING, (ROWS - row - 1)*SQUARE_SIZE + TOP_PADDING, SQUARE_SIZE, SQUARE_SIZE))

    def draw_valid_moves(self, window, moves):
        for move in moves:
            row = move // ROWS
            col = move % COLS
            pg.draw.circle(window, GRAY_COLOR, ((col*SQUARE_SIZE + (SQUARE_SIZE/2)) + LEFT_SIDE_PADDING, ((ROWS - row - 1)*SQUARE_SIZE + (SQUARE_SIZE/2)) + TOP_PADDING), 5)

    def draw_attacked_squares(self, window, attacked_squares):
        for square in attacked_squares:
            row = square // ROWS
            col = square % COLS
            pg.draw.circle(window, RED_COLOR, ((col*SQUARE_SIZE + (SQUARE_SIZE/2)) + LEFT_SIDE_PADDING, ((ROWS - row - 1)*SQUARE_SIZE + (SQUARE_SIZE/2)) + TOP_PADDING), 2)



   