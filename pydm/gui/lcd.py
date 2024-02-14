from itertools import cycle

import pygame

# =============================================================================
class Typer:
    '''Typer gets text input from user, and formsts for display'''
    def __init__(self, mode='text'):
        self.mode = mode # may be deprecated
        self.text_to_render = ''
        self.active = False

    def check_blink(self):
        '''Check if we should set "blinking" cursor'''
        if self.active:
            self.text_to_render = self.text_to_render.replace('|', '')
            self.text_to_render += "|"
        else:
            self.text_to_render = self.text_to_render.replace('|', '')
        return

    # ---------
    def typer_event(self, event):
        '''If typer is "active", get text input and store in "text_to_render" 
        and check if we need to set to inactive to stop getting text input
        '''
        if self.active:
            if event.type == pygame.TEXTINPUT:
                # Dont add "."
                if event.text != ".":
                    self.text_to_render += event.text

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                self.text_to_render = self.text_to_render[:-2]

            elif event.type == pygame.KEYDOWN and event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                self.active = False
        else:
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                self.active = True
        return

# ============================================================================
class MenuFont:
    '''Font object for setting font parameters used in rendering'''
    def __init__(self, fontsize=20, path=None):
        self.font = pygame.font.Font(path, fontsize)
        self.width = self.font.size("=")[0]
        self.height = self.font.size("=")[1]
        self.render = self.font.render

class LCD:
    '''3 parts:
    1) Header Area - 2 rows with 4 columns Dict(row_num1:{col_num: text} , row_numi:{col_num: text}
    2) Body - override update to define functionality
    3) Footer - the menu items aviliable (1 row, 5-6 items)
    '''
    FLAGS = 0
    WIDTH = 720 #720 #600
    HEIGHT = 231
    WHITE = (255,255,255)
    RED = (255,0,0)
    GREEN = (0,255,0)
    g2 = (11,210,31)
    blitloc = ((800-WIDTH)//2, 0)

    def __init__(self, root_dir):
        header = {0: {0:"No Header"}}
        body = None
        footer = {'main': ['<NONE>']}

        self.font = MenuFont(18, root_dir / 'assets/mononoki-Regular.ttf')
        self.font_w = self.font.width # 10
        self.font_h = self.font.height # 21

        self.DISPLAY = pygame.Surface((self.WIDTH, self.HEIGHT))
        self.DISPLAY.fill(self.g2)

        # --- MSG Overlay | For display error messages or loading/saving messages 
        self.overlay = self.DISPLAY.copy()
        self.overlay = self.overlay.convert_alpha()
        self.overlay.fill((80, 80, 0, 150)) #, flags=pygame.SRCALPHA
        self.overlay_rect = self.overlay.get_rect()

        self.msg_rect = pygame.Rect(0,0,350,100)
        self.msg_rect.center = self.overlay_rect.center
        self.msg_surf = pygame.Surface((self.msg_rect.w, self.msg_rect.h))
        self.msg_surf.fill(self.g2)
        pygame.draw.rect(self.msg_surf, (0,0,0), (0,0,350,100), 5)

        # -- Rect and lines for typers
        rect = self.DISPLAY.get_rect()
        line1_x = rect.centerx-30
        line1_y = rect.centery-50
        line2_x = line1_x
        line2_y = rect.centery-30
        self.typer_lines = [(line1_x, line1_y), (line2_x, line2_y)]

        # -- Coordinate Matrix nrows x 4 cols
        self.maxrows = (self.HEIGHT // self.font.height) # max rows = 11
        self.maxwidth = self.WIDTH - 2*self.font.width # 558

        col_width = self.maxwidth // 4 # 139
        width = self.font.width
        height = self.font.height

        # -- Column / row coords | 4 columns, 11 rows
        self.columns = []
        for j in range(4):
            col_list = []
            for i in range(self.maxrows):
                x = width + j*col_width
                y = height*(i % self.maxrows)
                col_list.append((x, y))
            self.columns.append(col_list)

        # -- Set LCD display variables
        self.cursor_idx = 0

        # -- Body settings
        self.offset = self.blitloc[0]
        self.spacing = self.WIDTH / 6
        self.nrows = self.maxrows-3 # Number of rows in body (should be 11)
        self.body_w = (self.WIDTH - 4*self.font.width) # 560
        self.body_x = 2*self.font.width # 20 | body x start positon
        self.body_y = 2*self.font.height # 42
        self.pulse_w = self.body_w / 96 # 5.8333 -> round to 6?
        
        # --- HEADER --- #
        self.make_header(header) # Extract rows and columns

        # --- BODY --- #
        if body is not None:
            self.make_body()

        # --- FOOTER --- #
        self.make_footer(footer)

    # --------------------------------- #
    def make_header(self, header):
        '''Extract 2 rows and the 4 cols | col[columns][row]
        example: header = {0: {0:"No Header"}} | {row: {col: text}}
        '''
        cols = self.columns
        # The indexes should be args to function
        row1 = [cols[0][0], cols[1][0], cols[2][0], cols[3][0]]
        row2 = [cols[0][1], cols[1][1], cols[2][1], cols[3][1]]
        rows = [row1, row2]
        self.keys, self.v_coords = [], []

        # Keys are row numbers
        for row in header.keys():
            for col, text in header[row].items():
                keys, v_coords = self.make_data_field(rows[row][col], text)
                self.keys.append(keys)
                self.v_coords.append(v_coords)
        return

    def make_body(self, body):
        '''Build Text and Rect pairs with hilites for each row in body_text'''
        self.body_text = body['text']
        self.length = len(self.body_text)
        rows = self.columns[0]
        # Repeat the row coords for every maxrow-1 elements in body_text
        cycled_zipped = zip(cycle(rows[2:self.maxrows-1]), self.body_text)
        self.get_hilite_pair(cycled_zipped, chars=56)
        self.to_display = self.content[0:self.nrows] # content from hilite pairs
        return

    def make_footer(self, menu_list):
        end = self.columns[0][-1][1] # y-coordinate = 210
        self.menu = []
        self.menu_hilites = []
        for i, text in enumerate(menu_list): # 100 = lcd.WIDTH / 6
            item = self.make_text((15 + self.spacing*i, end), text, (0,0,0), menu=True)
            self.menu.append(item)

        for i, text in enumerate(menu_list):
            item = self.make_text((15 + self.spacing*i, end), text, (11,210,31), b_color=(0,0,0), menu=True)
            self.menu_hilites.append(item)
        return

    # -------------------------------------------------------------------------
    def make_data_field(self, loc, text):
        '''Make parmeter text and set location - Deprecated'''
        parm_text, parm_rect = self.make_text(loc, text, (0,0,0))
        value_loc = parm_rect.topright
        parm = [parm_text, parm_rect]
        return parm, value_loc

    # -------------------------------------------------------------------------
    def make_text(self, loc, text, t_color, b_color=None, menu=False):
        '''help Function to make text surface and rect for rendering'''
        text = self.font.render(text, 1, t_color, b_color)
        text_rect = text.get_rect()
        if menu:
            # Below is menu text centered over key
            text_rect.centerx = loc[0]+30
            text_rect.y = loc[1]
        else:
            text_rect.topleft = loc
        return [text, text_rect]

    # -------------------------------- #
    def get_hilite_pair(self, cycled_zipped, chars=24): #24
        '''Loop over coord. text pairs and make Surface, Rect pairs'''
        self.content, self.hilites = [], []
        for coord, text in cycled_zipped:
            values, hilite = self.make_hilite_pair(coord, text, num_chars=chars)
            self.content.append(values)
            self.hilites.append(hilite)

    def make_hilite_pair(self, loc, text, num_chars):
        '''Make one coord, text pair to Surface, Rect pair'''
        maxwidth = self.font.width * num_chars
        maxchars = maxwidth // self.font.width
        c_text, c_rect = self.make_text(loc, text[0:maxchars], (0,0,0))
        h_text, h_rect = self.make_text(loc, text[0:maxchars], self.g2, (0,0,0))
        return [c_text, c_rect], [h_text, h_rect]

    # -------------------------------- #
    def change_idx_row(self, val):
        '''Clamp cursor index to be in bound of length'''
        self.cursor_idx = max(0, min(self.length-1, self.cursor_idx+val))

    def change_idx_col(self, val):
        '''Change Page, clamp index'''
        if self.length <= 8:
            if val == -1:
                self.cursor_idx = 0
            else:
                self.cursor_idx = self.length-1
        else:
            check = self.cursor_idx + val*self.nrows
            if (0 <= check < self.length):
                self.cursor_idx = check

    def update_page(self):
        '''Set Surface,Rect pairs that can be displayed. Based on curosr index'''
        current_page = self.cursor_idx // (self.nrows)
        self.to_display = self.content[0:self.nrows]
        if self.cursor_idx > self.nrows-1:
            start = self.nrows*current_page
            self.to_display = self.content[start:start+self.nrows]#self.content[start:start*2]

    # --------------------------------------------------------------------------
    def draw_menu_line(self):
        # Draw horizontal line over menu text
        pygame.draw.line(
            surface = self.DISPLAY,
            color = (0,0,0),
            start_pos = (0, self.HEIGHT - self.font.height),
            end_pos = (self.WIDTH, self.HEIGHT - self.font.height),
            width = 2
        )
        return

    def draw_header_line(self):
        pygame.draw.line(
            surface = self.DISPLAY,
            color = (0,0,0),
            start_pos = (0, self.font.height*2),
            end_pos = (self.WIDTH, self.font.height*2),
            width = 2
        )
        return

# EOF
