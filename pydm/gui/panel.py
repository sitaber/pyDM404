import itertools

import pygame
from pygame.locals import *

from pydm.modes.mode import Default
from pydm.gui import factory


class Pad:
    '''Pad stores sound file name/path and pitch/volume data used for playback
    Also loads and saves settings to dictinary for converting to JSON for persistent storage
    '''
    _keys = ("sound_file", "pitch", "channel", "volume", "bank", "ekey")

    def __init__(self, bank, pad_key):
        self.sound_file = 'None'
        self.bank = bank
        self.ekey = pad_key
        self.pitch = 12
        self.channel = 1
        self.volume = 12

    @property
    def to_dict(self):
        return {k: getattr(self, k) for k in self._keys}

    def from_dict(self, pad_dict):
        for key, val in pad_dict.items():
          setattr(self, key, val)

# =============================================================================
PAD_KEYS = [K_a, K_s, K_d, K_f, K_g, K_h, K_j, K_k]

class Panel:
    '''Main GUI componet: Most elements are pre-rendered/static to speed up application
    * Builds main GUI -> makes buttons, sets text 
    * loads/saves pads and banks
    * Checks and handles mouse clicks
    * Handles Fader postions/settings
    * renders GUI elements (LEDs for play/rec state, Metronome Button coloring etc)
    '''
    WIDTH = 800
    HEIGHT = 600
    WHITE = (255,255,255)
    RED = (255,0,0)

    def __init__(self, lcd, root_dir):
        self.font = pygame.font.Font(root_dir / 'assets/Kenney Future Narrow.ttf', 12)
        self.SURFACE = pygame.Surface((self.WIDTH, self.HEIGHT))

        # --- Control BUTTONS  --- #
        control_y = 315
        self.buttons, self.text_rects = factory.make_control_buttons(self.font, starty=control_y)
        new_buttons, new_text_rects, self.led_rects = factory.make_transport(self.font, starty=control_y+190)

        self.text_rects.extend(new_text_rects)
        self.buttons.update(new_buttons)

        nbuttons, ntext_rects = factory.make_lcd_controls(self.font, starty=control_y)
        self.text_rects.extend(ntext_rects)
        self.buttons.update(nbuttons)

        self.buttons.update(factory.make_softkeys(lcd.blitloc[0]-5, lcd.spacing))
        self.buttons["mixer_toggle"] = pygame.Rect((30, 370, 25,25))
        self.buttons["spreadlevels"] = pygame.Rect((30, 370+50, 25,25))
        self.buttons["bank_toggle"] = pygame.Rect((30, self.HEIGHT-87, 25,25))

        # --- PADS BUTTONS AND TEXT --- #
        self.pad_buttons = {PAD_KEYS[i]: pygame.Rect((115+i*60, 500, 50,50)) for i in range(8)}

        pad_text = ['A','S','D','F','G','H','J','K']
        for i, pad in enumerate(self.pad_buttons.values()):
            text = factory.make_text(pad_text[i], self.font, (255,255,255),
                                     pad.centerx-4, pad.bottom+5)
            self.text_rects.append(text)

        self.make_pad_banks() # We all this again in dm init...

        # --- Faders --- #
        self.fader_clicked = False
        self.mixer_surface = factory.build_mixer()
        self.fader = factory.make_fader_surf()
        self.fader_levels = [480 - y*8 for y in range(0, 25)]
        self.clicked_key = None

        knob_rects = [pygame.Rect((125 + x*60, self.fader_levels[12], 30, 35)) for x in range(8)]
        self.fader_knobs = {key: knob_rects[i] for i, key in enumerate(PAD_KEYS)}

        # -- Fader Modes
        self.mixer_modes = itertools.cycle(['volume', 'pitch'])
        self.toggle_mixer()

        # --- Render all static elments
        factory.build_base(self, lcd, knoby=control_y+150)

    # -------------------------------------------------------------------------
    def make_pad_banks(self):
        self.banks = {}
        for bank in ["A", "B", "C", "D"]:
            self.banks[bank] = {key: Pad(bank, key) for key in PAD_KEYS}
        self.bank_names = itertools.cycle(['A', 'B', 'C', 'D'])
        self.toggle_bank()
        return

    def toggle_bank(self):
        self.bank_name = next(self.bank_names)
        self.pads = self.banks.get(self.bank_name)
        return

    def load_pad_config(self, disk, snd_engine):
        pad_configs = disk.config['pads']

        for pad_config in pad_configs: # Get pad from banks based on config
            bank = pad_config.get('bank')
            ekey = pad_config.get('ekey')
            pad = self.banks[bank][ekey]

            pad.from_dict(pad_config) # use pad method to load config
            missing_snd = snd_engine.set_pitches(pad_config.get('sound_file'))
            if missing_snd:
                pad.sound_file = "None"
        return

    def toggle_mixer(self):
        # toogel between mixer modes (volume and pitch/tune)
        self.mixer_mode = next(self.mixer_modes)
        return

    def spread_levels(self):
        for i, v in enumerate([7, 9, 11, 12, 14, 16, 18, 19]):
            key = PAD_KEYS[i]
            setattr(self.pads[key], self.mixer_mode, v)
            self.fader_knobs[key].centery = self.fader_levels[v]
        return

    def handle_click(self, mode):
        '''Mouse click handler'''
        mx, my = pygame.mouse.get_pos()
        mouse_rect = pygame.Rect((mx,my),(1,1))

        key = mouse_rect.collidedict(self.fader_knobs, 1)
        if key:
            self.fader_clicked = True
            self.clicked_key = key[0]

        if mouse_rect.colliderect(self.vol_knob.rect):
            self.vol_knob.handle_click()

        collide = mouse_rect.collidedict(self.buttons, 1)
        if collide:
            action = collide[0]
            command = mode.commands.get(action, Default())
            command.execute(mode)

        collide = mouse_rect.collidedict(self.pad_buttons, 1)
        if collide:
            action = collide[0]
            command = mode.commands.get(action, Default())
            command.execute(mode)
        return

    def fader_motion(self):
        mx, my = pygame.mouse.get_pos()
        key = self.clicked_key
        new_loc = max(0, min(24, (480-my)//8)) # clamp fader to y range 

        setattr(self.pads[key], self.mixer_mode, new_loc)
        self.fader_knobs[key].centery = self.fader_levels[new_loc]

        return

    def render(self, screen, sequencer):
        '''Render dynamic elements - Called in main game loop'''
        state = sequencer.state
        screen.blit(self.SURFACE, (0, 0))

        # -- Transport
        pcolor = self.RED if state.playing else self.WHITE
        pygame.draw.circle(screen, pcolor,  self.led_rects[0].center, 5)
        pygame.draw.circle(screen, (0, 0, 0), self.led_rects[0].center, 5, 1)

        rcolor = self.RED if state.rec else self.WHITE
        pygame.draw.circle(screen, rcolor, self.led_rects[1].center, 5)
        pygame.draw.circle(screen, (0, 0, 0), self.led_rects[1].center, 5, 1)

        # -- FADERS
        screen.blit(self.mixer_surface, (120, 280))

        for key, rect in self.fader_knobs.items():
            level = getattr(self.pads[key], self.mixer_mode, 12)
            self.fader_knobs[key].centery = self.fader_levels[level]
            screen.blit(self.fader, self.fader_knobs[key])

        if state.met:
                pygame.draw.rect(screen, self.RED, self.buttons["MET_plus"].inflate(-2,-2))
                pygame.draw.rect(screen, (0,0,0), self.buttons["MET_plus"], 2)
        elif not state.met:
                pygame.draw.rect(screen, self.RED, self.buttons["MET_minus"].inflate(-2,-2))
                pygame.draw.rect(screen, (0,0,0), self.buttons["MET_minus"], 2)

        # -- Mixer Mode LED
        for i in [0,1]:
            color = self.WHITE
            if (self.mixer_mode == 'volume' and i == 0) or (self.mixer_mode == 'pitch' and i == 1):
                color = self.RED
            pygame.draw.circle(screen, color, (70, 372 + i*20), 5)
            pygame.draw.circle(screen, (0, 0, 0), (70, 372 + i*20), 5, 1)

        # -- Pad Bank LED
        for i, t in enumerate(["A", "B", "C", "D"]):
            color = self.WHITE
            if t == self.bank_name:
                color = self.RED
            pygame.draw.circle(screen, color, (70, 495 + i*20), 5)
            pygame.draw.circle(screen, (0,0,0), (70, 495 + i*20), 5, 1)

        return
# EOF
