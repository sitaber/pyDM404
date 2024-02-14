import math

import pygame
from pygame.locals import *

from pygame import Rect
from pygame import Surface

# =============================================================================
'''Factory Module: Consists of Helper funtions for building GUI elements'''

# -- Perfom elements
def make_pad_names(lcd, pads):
    # Need to get file names from bank/snd_engine or pads
    pad_letters = []
    x = lcd.font.width+12 #offset
    i = 0
    for pad in pads.values():
        text = pad.sound_file
        if text == "None":
            text = ""
        else:
            text = text.split(".")[0]
        y = lcd.body_y + lcd.font.height*i
        text_surface = lcd.font.render(text[0:], 1, (0,0,0)) #text[0:8]
        textrect = text_surface.get_rect()
        textrect.topleft = (x, y)
        pad_letters.append([text_surface, textrect])
        i += 1

    return pad_letters

def make_pad_letters(lcd):
    pad_letters = []
    x = lcd.font.width-5
    for i, text in enumerate(['A','S','D','F','G','H','J','K']):
        y = lcd.body_y + lcd.font.height*i
        text_surface = lcd.font.render(text, 1, (0,0,0))
        textrect = text_surface.get_rect()
        textrect.topleft = (x, y)
        pad_letters.append([text_surface, textrect])

    return pad_letters

def make_grid_beats(lcd):
    grid_beats = []
    coords = []
    num = 16 #8
    for i in range(1,num): # offset | use body_x for starting point?
        coords.append((lcd.font_w + 5 + (lcd.body_w/num)*i, lcd.font_h))

    text = ["╻", "|", "╻", "2", "╻", "|", "╻", "3", "╻", "|", "╻","4", "╻","|", "╻" ]
    text_coords = list(zip(text, coords))

    for text, coords in text_coords:
        func_text = lcd.font.render(text, True, (0,0,0))
        grid_beats.append([func_text, coords])

    return grid_beats

def make_grid_rects(mode):
    sequencer = mode.sequencer
    grid_rects = {key: [] for key in sequencer.auto_cor}

    xstart = mode.lcd.body_x #20
    ystart = mode.lcd.body_y #42
    width = mode.lcd.body_w # 560
    rect_h = mode.lcd.font.height #21

    for length, key in zip([4, 8, 12, 16, 24, 32, 48, 96], grid_rects.keys()) :
        rects = grid_rects[key] # Ref to the list
        rect_w = width / length
        for i in range(8): #32
            for j in range(length): #left, top, width, height
                rect = (xstart + j*rect_w, ystart + i*rect_h, rect_w, rect_h)
                rects.append(Rect(rect))

    return grid_rects

# =============================================================================
# Panel GUI
def make_text(text, font, color, x=0, y=0):
    text_surface = font.render(text, 1, color)
    textrect = text_surface.get_rect()
    textrect.topleft = (x, y)
    return [text_surface, textrect]

def make_transport(font, starty):
    # Play and Record Buttons
    buttons = {}
    text_rects = []
    led_rects = []
    x = 640 #630

    buttons['play'] = pygame.Rect((x, starty, 40, 40))

    t_surf, t_rect = make_text("PLAY", font, (255,255,255))
    t_rect.center = buttons['play'].center
    t_rect.y = buttons['play'].y+60
    t_rect.x += 1
    text_rects.append([t_surf, t_rect])

    play_led = pygame.Rect((0,0,8,8))
    play_led.center = buttons['play'].center
    play_led.y = buttons['play'].y+48
    led_rects.append(play_led)

    # -----
    buttons['record'] = pygame.Rect((x+60, starty, 40, 40))

    t_surf, t_rect = make_text("REC", font, (255,255,255))
    t_rect.center = buttons['record'].center
    t_rect.y = buttons['record'].y+60
    t_rect.x += 1
    text_rects.append([t_surf, t_rect])

    led = pygame.Rect((0,0,8,8))
    led.center = buttons['record'].center
    led.y = buttons['record'].y+48
    led_rects.append(led)

    return buttons, text_rects, led_rects

def make_control_buttons(font, starty, buttons = {}, text_rects = []):
    button_y = starty #-220 #300 #440 - 140
    button_x = 648 # 95+50+520
    button_w = 40
    button_h = 20

    for i, text in enumerate(["SEQ","BPM","AC","MET"]):
        if text == "BPM":
            rect_minus = Rect(button_x, button_y + 27*i, button_w-12, button_h)
            rect_plus = Rect(button_x+45+12, button_y + 27*i, button_w-12, button_h)

            rect_mm = Rect(button_x+button_w-10, button_y + 27*i, button_w-30, button_h)
            rect_pp = Rect(button_x+45, button_y + 27*i, button_w-30, button_h)

            buttons[f"BPM_--"] = rect_mm
            buttons[f"BPM_++"] = rect_pp
        else:
            rect_minus = Rect(button_x, button_y + 27*i, button_w, button_h)
            rect_plus = Rect(button_x+45, button_y + 27*i, button_w, button_h)

        buttons[f"{text}_minus"] = rect_minus
        buttons[f"{text}_plus"] = rect_plus

        label_surf, label_rect = make_text(text, font, color=(255,255,255))
        label_rect.center = rect_minus.center
        label_rect.right = rect_minus.left-5

        text_rects.append([label_surf, label_rect])

        if text == "MET":
            t_surf, t_rect = make_text("OFF", font, (255,255,255))
            t_rect.center = rect_minus.center
            t_rect.top = rect_minus.bottom+5
            t_rect.x += 1
            text_rects.append([t_surf, t_rect])

            t_surf, t_rect = make_text("ON", font, (255,255,255))
            t_rect.center = rect_plus.center
            t_rect.top = rect_minus.bottom+5
            t_rect.x += 1
            text_rects.append([t_surf, t_rect])
        else:
            t_surf, t_rect = make_text("-", font, (0,0,0))
            t_rect.center = rect_minus.center
            t_rect.x += 2
            text_rects.append([t_surf, t_rect])

            t_surf, t_rect = make_text("+", font, (0,0,0))
            t_rect.center = rect_plus.center
            t_rect.x += 2
            text_rects.append([t_surf, t_rect])

    return buttons, text_rects

def make_softkeys(start=95, spacing=100): #95 | lcd.blitloc[0]-5 | 20,95 | offset 100 = lcd.WIDTH / 6
    return {f"softkey_{str(i+1)}": Rect(start+25+spacing*i, 238, 50, 15) for i in range(6)}

def make_lcd_controls(font, starty, buttons = {}, text_rects = []):
    button_y = starty-27 #-220 #300 #440 - 140
    button_x = 648 # 95+50+520
    button_w = 40
    button_h = 20

    rect_minus = Rect(button_x, button_y, button_w-12, button_h)
    rect_plus = Rect(button_x+45+12, button_y, button_w-12, button_h)

    rect_mm = Rect(button_x+button_w-10, button_y, button_w-30, button_h)
    rect_pp = Rect(button_x+45, button_y, button_w-30, button_h)

    buttons[f"page-"] = rect_mm
    buttons[f"page+"] = rect_pp

    buttons["idx-"] = rect_minus
    buttons["idx+"] = rect_plus

    label_surf, label_rect = make_text("LCD", font, color=(255,255,255))
    label_rect.center = rect_minus.center
    label_rect.right = rect_minus.left-5

    text_rects.append([label_surf, label_rect])

    t_surf, t_rect = make_text("-", font, (0,0,0))
    t_rect.center = rect_minus.center
    t_rect.x += 2
    text_rects.append([t_surf, t_rect])

    t_surf, t_rect = make_text("+", font, (0,0,0))
    t_rect.center = rect_plus.center
    t_rect.x += 2
    text_rects.append([t_surf, t_rect])

    return buttons, text_rects

# ==============================================================================
class VolumeKnob:
    def __init__(self, x, y, radius=15, ticks=10):
        self.clicked = False
        self.num_ticks = ticks
        self.index = ticks

        self.center = [x, y]
        self.radius = radius
        self.rect = Rect(0,0,radius*2,radius*2)
        self.rect.center = [x, y]
        self.coords = self.make_tick_coords(scale=self.radius-2)
        self.coords2 = self.make_tick_coords(scale=self.radius+4)
        self.end = [self.coords[self.index][0], self.coords[self.index][1]]

    def make_tick_coords(self, scale=15):
        coords = []
        for i in range(-45, 225+27, 27):
            rads = math.radians(i)
            xi = math.cos(rads)
            yi = math.sin(rads)
            x = round(self.center[0]+xi*scale)
            y = round(self.center[1]+yi*-scale)
            coords.append([x, y])
        coords.reverse()
        return coords

    def build_base(self, screen):
        self.screen = screen
        for c in self.coords2:
            pygame.draw.circle(screen, (255,255,255), c, 1) # Tick marks

        pygame.draw.circle(screen, (55,55,55), self.center, self.radius+1,1) # Knob outline
        self.draw_indicator()
        return

    def draw_indicator(self):
        pygame.draw.circle(self.screen, (0,0,0), self.center, self.radius) # Center knob color
        pygame.draw.line(self.screen, (255,255,255), self.center, self.end, 2) # Line indicator

    def handle_click(self):
        if self.clicked is False:
            mx,my = pygame.mouse.get_pos()
            self.start_y = my
            self.clicked = True
        else:
            self.clicked = False
        return

    def update(self):
        mx,my = pygame.mouse.get_pos()
        end_y = self.start_y - my
        if abs(end_y)//10 == 1:
            self.start_y = my
            self.index += end_y//10
            self.index = max(0, min(self.num_ticks, self.index))
            self.end = [self.coords[self.index][0], self.coords[self.index][1]]
            self.draw_indicator()
        return

# =============================================================================
# -- Mixer / Faders factory functions
def build_chan():
    BASE = pygame.Surface((40,210))
    BASE.fill((40,40,41))
    rect = BASE.get_rect()
    rect.w -= 1
    rect.h -= 1
    notch_y = [200-(y*8) for y in range(0,25)]
    for i, y in enumerate(notch_y):
        if i == 12:
            color = (160,160,160)
        else:
            color = (80,80,80)
        pygame.draw.line(BASE, color, (0, y), (5,y), 2)
    pygame.draw.line(BASE, (255,255,255), (19,0), (19,210), 1)
    pygame.draw.rect(BASE, (0,0,0), rect, 4)
    return BASE

def build_mixer():
    MIXER = pygame.Surface((460,210))
    MIXER.fill((90,91,107))
    #MIXER.fill((40,40,40))
    BASE = build_chan()
    for i in range(8):
        MIXER.blit(BASE, (i*60,0))
    return MIXER

def make_fader_surf():
    fader = pygame.Surface( (30, 35) )
    fader.fill((0,0,0))
    knob = fader.get_rect()
    pygame.draw.rect(fader, (144,144,141), knob, 1)
    pygame.draw.line(fader, (255,255,255), knob.midleft, (knob.midright[0]-1, knob.midright[1]))
    return fader

# =============================================================================
def build_base(panel, lcd, knoby):
    '''Prerender all static gui elements using module helper functions
    A lot of things are specific to the drum machine like the mode of the mixer
    '''
    bc = (200,200,200)
    bg = (90,91,107) #(144,144,141)
    screen = panel.SURFACE
    screen.fill(bg)

    # ----------------------------------------------------------------------
    # -- Master Volume Knob | Build object and make GUI text and other elements
    knob_x = 690 #89 #686
    knob_y = knoby #450 #310 #pass starty
    vol = VolumeKnob(knob_x, knob_y)
    vol.build_base(screen)
    panel.vol_knob = vol

    text_b = panel.font.render("Vol", True, (255, 255, 255))
    screen.blit(text_b, (knob_x-70,knob_y-10)) #320 #-38

    text_b = panel.font.render("Min", True, (255, 255, 255))
    text_rect = text_b.get_rect()
    text_rect.topright = vol.coords2[0]
    text_rect.y += 3
    screen.blit(text_b, text_rect) #320

    text_b = panel.font.render("Max", True, (255, 255, 255))
    text_rect = text_b.get_rect()
    text_rect.topleft = vol.coords2[-1]
    text_rect.y += 3
    screen.blit(text_b, text_rect) #320

    # ----------------------------------------------------------------------
    # -- Mixer Mode LEDs and TEXT 
    for i, t in enumerate(["MIX","TUNE"]):
        text_b = panel.font.render(t, True, (255, 255, 255))
        screen.blit(text_b, (80,365+i*20))

    text_b = panel.font.render("SPREAD", True, (255, 255, 255))
    screen.blit(text_b, (20,370+80))

    # -- Bank toggle text
    for i, t in enumerate(["A", "B", "C", "D"]):  # Move this to make_buttons?
        text_b = panel.font.render(t, True, (255, 255, 255))
        screen.blit(text_b, (80, 488+i*20))

    # -- Menu/soft Keys text
    for i, t in enumerate(["Q", "W", "E", "R", "T", "Y"]):
        text_b = panel.font.render(t, True, (255, 255, 255))
        x = panel.buttons[f'softkey_{str(i+1)}'].centerx-2
        y = panel.buttons[f'softkey_{str(i+1)}'].centery+8
        screen.blit(text_b, (x, y))
   
    # ----------------------------------------------------------------------
    # -- PADS
    for rect in panel.pad_buttons.values():
        pygame.draw.rect(screen, (8,9,2), rect)
        pygame.draw.rect(screen, bc, rect, 1)

    # -- Controls, LCD softkeys, and toggles rects/buttons
    for rect in panel.buttons.values():
        pygame.draw.rect(screen, bc, rect)
        pygame.draw.rect(screen, (0,0,0), rect, 2)

    screen.blits(panel.text_rects) # We always draw on the scene surface

#
