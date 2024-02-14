import pygame
from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command
from pydm.gui import factory

# ------ Commands
sequencer_cmds = {
    "SEQ_minus": Command(target='sequencer', method='change_seq', arg=-1),
    "SEQ_plus": Command('sequencer', 'change_seq', 1),
    "BPM_minus": Command('sequencer', 'set_bpm', -0.5),
    "BPM_plus": Command('sequencer', 'set_bpm', 0.5),
    "BPM_--": Command('sequencer', 'set_bpm', -10),
    "BPM_++": Command('sequencer', 'set_bpm', 10),
    "AC_minus": Command('sequencer', 'set_tc', -1),
    "AC_plus": Command('sequencer', 'set_tc', 1),
    "MET_minus": Command('sequencer', 'toggle_met'),
    "MET_plus": Command('sequencer', 'toggle_met'),
    "play": Command('sequencer', 'toggle_play'),
    "record": Command('sequencer', 'toggle_rec'),
    "delete": Command('sequencer', 'toggle_delete'),
    "mixer_toggle": Command('panel', 'toggle_mixer'),
    "bank_toggle": Command('panel', 'toggle_bank'),
    "spreadlevels": Command('panel', 'spread_levels'),
}

pad_perform = {
    K_a: Command(None, 'handle_pads', K_a),
    K_s: Command(None, 'handle_pads', K_s),
    K_d: Command(None, 'handle_pads', K_d),
    K_f: Command(None, 'handle_pads', K_f),
    K_g: Command(None, 'handle_pads', K_g),
    K_h: Command(None, 'handle_pads', K_h),
    K_j: Command(None, 'handle_pads', K_j),
    K_k: Command(None, 'handle_pads', K_k)
}

grid_softkeys = {
    'softkey_1': Command(None, 'set_bar', -1),
    'softkey_2': Command(None, 'set_bar', 1),
    'softkey_3': Command(None, 'toggle_follow'),
    'softkey_4': Command(None, 'make_menu', 'swing'),
    'softkey_5': Command(None, 'toggle_names'),
    'softkey_6': Command(None, 'make_menu', 'main'),
}

perform_softkeys = {
    'softkey_1': Command(None, 'make_menu', 'grid'),
    'softkey_2': Command('dm', 'change_mode', 'assign'),
    'softkey_3': Command('dm', 'change_mode', 'sounds'),
    'softkey_4': Command('dm', 'change_mode', 'seq'),
    'softkey_5': Command('dm', 'change_mode', 'song'),
    'softkey_6': Command('dm', 'change_mode', 'disk'),
}

swing_softkeys = {
    'softkey_1': Command(None, 'set_swing', -1),
    'softkey_2': Command(None, 'set_swing', 1),
    'softkey_3': Default(),
    'softkey_4': Default(),
    'softkey_5': Default(),
    'softkey_6': Command(None, 'make_menu', 'grid'),
}

# ------ LCD ------ #
header = {0: {0:"SEQ:", 1:" BPM:", 2:"AC:", 3:"COUNT:"}}
headers = {'main': header, 'grid': header, 'swing': header,}

perform = ["<GRID>", "<PADS>", "<SNDS>", "<SEQS>", "<SONG>", "<DISK>"]
grid = ["<BAR->", "<BAR+>", "<FOLLOW>", "<SWING>", "<NAMES>", "<MAIN>"]
swing = ["<SWING->", "<SWING+>", "", "", "", "<GRID>"]

footers = {'main': perform, 'grid': grid, 'swing': swing}

# ==============================================================================
'''Mode specific variables and functions'''
ekey_map = {97: 0, 115: 1, 100: 2, 102: 3, 103: 4, 104: 5, 106: 6, 107: 7}
fill_colors = {"A": (0,0,0), "B": (0,0,255), "C": (134, 0, 179), "D":(77, 51, 25)}

BANK_MAP = {"A": 0, "B": 8, "C": 16, "D": 24}
#SWING = {0: "50%", 1: "54%", 2: "58%", 3: "63%", 4: "66%", 5:"71%"}
SWING = {0: "0", 1: "1", 2: "2", 3: "3"}

# ==============================================================================
class Perform(Mode):
    def __init__(self, dm):
        super().__init__(dm)
        # Subclass specific
        self.name = 'perform'
        self.header_dict = headers
        self.footer_dict = footers

        self.commands.update(pad_perform)
        self.commands.update(sequencer_cmds)

        self.bar = 0
        self.grid_rects = factory.make_grid_rects(self)
        self.grid = self.grid_rects[self.sequencer.ac]
        self.fill_rects = []

        self.grid_text = factory.make_pad_letters(self.lcd) #do sound name | update
        self.grid_text.extend(factory.make_grid_beats(self.lcd))
        #self.grid_text = factory.make_grid_beats(self.lcd)

        self.show_names = False
        self.follow = False
        self.seqs = self.dm.disk.config['seqs']

        self.make_menu('main')

    # --------------------------------------------------------------------------
    def make_menu(self, menu='main'):
        if menu == 'main':
            self.commands.update(perform_softkeys)
        elif menu == "grid":
            self.commands.update(grid_softkeys)
        elif menu == "swing":
            self.commands.update(swing_softkeys)

        self.menu = menu
        self.lcd.make_header(self.header_dict[menu])
        self.lcd.make_footer(self.footer_dict[menu])
        return

    # --------------------------------------------------------------------------
    def events(self, event):
        '''Main Mode Evenct Handler'''
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            self.panel.handle_click(self)
            if self.menu == 'grid' and self.sequencer.current_seq.size != 1:
                self.handle_mouse() # Only for grid

        elif (self.panel.vol_knob.clicked or self.panel.fader_clicked):
            if event.type == MOUSEMOTION:
                if self.panel.fader_clicked:
                    self.panel.fader_motion()

                elif self.panel.vol_knob.clicked:
                    self.panel.vol_knob.update()
                    self.snd_engine.volume = self.panel.vol_knob.index/10

            elif event.type == MOUSEBUTTONUP and event.button == 1:
                if self.panel.fader_clicked:
                    self.panel.fader_clicked = False

                elif self.panel.vol_knob.clicked:
                    self.panel.vol_knob.handle_click()

        if event.type == KEYDOWN:
            if event.key in self.pad_keys:# and self.sequencer.state.delete == False:
                self.handle_pads(event.key) # Only PlayRec
            else:
                self.handle_input(event)

        elif event.type == KEYUP and event.key == K_BACKSPACE: #K_l:
            self.handle_input(event)

        if self.sequencer.state.delete and self.sequencer.state.rec: #Only delete in rec state?
            self.delete_pads()
        return

    # --------------------------------------------------------------------------
    '''UPDATEs'''
    def update(self):
        if self.sequencer.error is True:
            self.snd_engine.play_error()
            self.sequencer.error = False

        check_seq, play_met = self.sequencer.update()
        if play_met:
            self.snd_engine.play_met(self.sequencer.beat)

        if check_seq:
            self.snd_engine.sequncer_play(self.sequencer, self.panel.banks)

        self.lcd_update()
        return

    def lcd_update(self):
        lcd = self.lcd
        sequencer = self.sequencer
        seq = sequencer.seq
        seq_num = int(seq.split("*")[0])
        bpm = sequencer.bpm
        count = sequencer.count
        ac = sequencer.ac

        vals = [f"{seq} {self.seqs[seq_num]['name'][0:8]}", f"{bpm}", f"{ac}", f"{count}" ]
        content = [lcd.make_text(loc, text, (0,0,0)) for loc, text in zip(lcd.v_coords, vals)]
        to_blit = [self.lcd.keys, self.lcd.menu, content]

        if self.menu == 'swing':
            text = f"Set Swing: {SWING[self.seqs[seq_num]['swing']]}"
            dialog = lcd.make_text(lcd.typer_lines[0], text, (0,0,0), menu=True)
            to_blit.append([dialog])
            text = "Cannot be set during playback"
            dialog = lcd.make_text(lcd.typer_lines[1], text, (0,0,0), menu=True)
            to_blit.append([dialog])

        elif self.menu == 'grid' and self.follow:
            to_blit.append([self.lcd.menu_hilites[2]])

        self.lcd.DISPLAY.fill(self.lcd.g2)
        for item in to_blit:
            self.lcd.DISPLAY.blits(item)

        if self.menu == 'grid':
            if self.sequencer.current_seq.size != 1:
                self.make_fill_rects()
            self.draw_grid()
        else:
            self.lcd.draw_menu_line()

    # --------------------------------------------------------------------------
    '''Methods'''
    def set_bar(self, val):
        if self.sequencer.current_seq.size != 1:
            max_bar = self.sequencer.seq_play.shape[1] // 96
            self.bar = max(0, min(max_bar-1, self.bar + val))

    def set_swing(self, val):
        seq = self.sequencer.seq
        seq_num = int(seq.split("*")[0])
        seq_init = self.sequencer.current_seq.size != 1

        if self.sequencer.state.playing is False and seq_init:
            self.seqs[seq_num]['swing'] = max(0, min(3, self.seqs[seq_num]['swing']+val))
            self.sequencer.copy_rec_to_play()

        return

    def toggle_follow(self):
        self.follow = not self.follow
        return

    def toggle_names(self):
        self.show_names = not self.show_names
        return

    def handle_pads(self, ekey):
        '''Play a sound store in a Pad object, record if sequncers is in REC state'''
        pad = self.panel.pads[ekey]
        if self.sequencer.state.delete == False:
            self.snd_engine.play_sound(pad)
            if self.sequencer.state.playing and self.sequencer.state.rec:
                idx = BANK_MAP[pad.bank] + ekey_map[ekey] # doc how banks and ekeys maps work
                self.sequencer.record(idx, pad.pitch)
        return

    def delete_pads(self):
        '''Delete Single "note" from sequence if playing, else remove all notes'''
        seqr = self.sequencer
        pressed = pygame.key.get_pressed()

        for ekey in self.pad_keys:
            idx = self.pad_keys.index(ekey)
            idx += BANK_MAP[self.panel.bank_name]
            if pressed[ekey] and seqr.state.playing:
                seqr.delete(idx)
            elif pressed[ekey] and seqr.state.playing == False:
                seqr.delete(idx, whole=True)
        return

    def handle_mouse(self): # needs callback to seqr and pads
        '''Handles mouse events when in GRID mode and interacting with the LCD'''
        mx, my = pygame.mouse.get_pos()
        # Translate mouse x to '0' relative to LCD | Changing LCD width impacts this...
        mouse_rect = pygame.Rect((mx-self.lcd.blitloc[0], my), (1, 1))

        grid_clicked = mouse_rect.collidelistall(self.grid) # Did we click inside the grid?
        is_filled = mouse_rect.collidelistall(self.fill_rects) # Did we click a filled rect?

        if grid_clicked and self.sequencer.state.rec:
            idx = grid_clicked[0]
            clicked_rect = self.grid[idx]
            rect_x, rect_y = clicked_rect.topleft

            pad_idx = int((rect_y - self.lcd.body_y) / self.lcd.font_h) # Translate rect_y to pad_idx
            # Translate rect_x to pulse | based on quantize value
            pulse = round(((rect_x - self.lcd.body_x) / self.lcd.pulse_w) + 96*self.bar)
            pitch = self.panel.pads[self.pad_keys[pad_idx]].pitch # Get pitch from current pads

            # Need to add bank value to pad_idx for seq edit
            pad_idx += BANK_MAP[self.panel.bank_name]
            if is_filled: # Remove from fill_rects
                self.fill_rects.pop(is_filled[0])
                self.sequencer.grid_edit(pad_idx, pulse, False, pitch)
            else:
                self.sequencer.grid_edit(pad_idx, pulse, True, pitch)

        return

    # --------------------------------------------------------------------------
    '''GRID METHODS'''
    def draw_grid(self):
        if self.follow and self.sequencer.state.playing:
            self.bar = self.sequencer.bar

        y1 = self.lcd.columns[0][2][1] #65
        y2 = self.lcd.columns[0][10][1] #145
        x1 = False
        pulse = self.sequencer.pulse
        pulse_w = self.lcd.pulse_w # # The Red vertical line in Grid | width/96

        # bar is the visual bar, not the bar based on time
        if pulse < 96 and self.bar == 0:
            x1 = self.lcd.body_x + pulse*pulse_w

        elif pulse > 96*self.bar and self.bar > 0:
            x1 = self.lcd.body_x + (pulse-96*self.bar)*pulse_w

        if x1:
            pygame.draw.lines(
                surface = self.lcd.DISPLAY,
                color = self.lcd.RED,
                closed = False,
                points = [(x1,y1), (x1,y2)],
                width = 2
            )

        fill_color = fill_colors[self.panel.bank_name]

        for rect in self.fill_rects:
            pygame.draw.rect(self.lcd.DISPLAY, fill_color, rect)
            pygame.draw.rect(self.lcd.DISPLAY, self.lcd.g2, rect, width=1)

        for rect in self.grid:
            pygame.draw.rect(self.lcd.DISPLAY, (255,255,255), rect, width=1)

        bar_text = self.lcd.font.render(f"{self.bar+1}", True, (0,0,0))
        bar_coords = (self.lcd.font_w + 5, self.lcd.font_h) #offset

        if self.show_names:
            pad_text = factory.make_pad_names(self.lcd, self.panel.pads)
            self.lcd.DISPLAY.blits(pad_text)

        self.lcd.DISPLAY.blits(self.grid_text) # do grid beats, but update pad names
        self.lcd.DISPLAY.blit(bar_text, bar_coords)
        return None

    def make_fill_rects(self):
        sequencer = self.sequencer
        self.grid = self.grid_rects[self.sequencer.ac]
        self.fill_rects = []

        #64 looks good | max 96 with large LCD @ 750
        steps = [4, 8, 12, 16, 24, 32, 48, 96]
        length = steps[sequencer.tc]

        xstart = self.lcd.body_x
        ystart = self.lcd.body_y
        width = self.lcd.body_w

        rect_h = self.lcd.font.height #10
        # Set Rect width based on quantize value
        rect_w =  width / 32
        if length == 96 or length == 48:
            rect_w = width / length

        bar = self.bar
        m = BANK_MAP[self.panel.bank_name]
        for i in range(m, m+8):
            for j in range(96 * bar, 96 * (bar+1)):
                if sequencer.seq_record[i, j][0]:
                    left = xstart + (width/96)*(j-96*bar)
                    top = ystart + (i%8)*rect_h
                    rect = (left, top, rect_w, rect_h)
                    self.fill_rects.append(pygame.Rect(rect))

        return None


# EOF
