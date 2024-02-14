from pathlib import Path

import pygame
from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command
from pydm.gui.lcd import Typer
from pydm.gui.editors import Chopper, write_wave

from pydm.modes import Perform

# ------ Commands ------ #
close_menu = Command(None, 'make_menu', 'main')

cmds = {
    'main': {
        'softkey_1': Command(None, 'remove_slice'),
        'softkey_3': Command(None, 'make_menu', 'to_pads'), #Default(),
        'softkey_4': Command(None, 'make_menu', 'to_mem'),
        'softkey_6': Command('dm', 'change_mode', 'main')
    },
    'to_pads': {
        'softkey_1': Command(None, 'set_bank', 'A'),
        'softkey_2': Command(None, 'set_bank', 'B'),
        'softkey_3': Command(None, 'set_bank', 'C'),
        'softkey_4': Command(None, 'set_bank', 'D'),
        'softkey_6': close_menu
    },
    'to_mem': {
        'softkey_1': close_menu,
        'softkey_2': Command(None, 'write_chops'),
    }
}
# ------ LCD ------ #
headers = {
    'main': {0: {0: "SLICE:", 1: "START-LOC:"}},
    'to_pads': {0: {0: ''}},
    'to_mem': {0: {0: ''}}
}

confirm = ["<NO>", "<YES>"]
typing = ["Typing..."]
use_name = ["<EXIT>", "<CONFIRM>"]

footers = {
    'main': ["<DEL>", "", "<TO-PADS>", "<TO-MEM>", "", "<EXIT>"],
    'to_pads': ['<A>', '<B>', '<C>', '<D>', '<>', '<CANCEL>'],
    'to_mem': use_name,
    'typing': typing
}

# ==============================================================================
class Chop(Mode):
    def __init__(self, dm, sound_name, from_memory=True):
        super().__init__(dm)
        self.name = 'chopit'
        self.header_dict = headers
        self.footer_dict = footers

        if from_memory:
            snd_path = self.snd_engine.sounds[sound_name]['path']
            snd_array = pygame.sndarray.array(self.snd_engine.mixer.Sound(snd_path))
        else:
            snd_array = pygame.sndarray.array(self.snd_engine.mixer.Sound(sound_name))

        self.chopper = Chopper(self.lcd, snd_array) # Check snd here, if len == 0 msg and exit

        self.selected_bank = None
        self.sound_name = sound_name
        self.drag = False
        self.drag_rect = None
        self.slice_idx = None
        self.make_menu('main')

    # --------------------------------------------------------------------------
    def make_menu(self, menu=None):
        body = {'text':''}

        if menu == 'main':
            self.typer = None
            self.selected_bank = None
        elif menu in ['to_mem']:
            self.typer = Typer(mode='text')

        self.menu = menu
        self.lcd.make_header(self.header_dict[menu])
        self.lcd.make_body(body)
        self.lcd.make_footer(self.footer_dict[menu])
        self.commands = cmds[menu]

        return
        
    # --------------------------------------------------------------------------
    def events(self, event):
        '''Mode Event Handler'''
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.panel.handle_click(self)

            mx, my = pygame.mouse.get_pos()
            mouse_actual = pygame.Rect((mx,my),(1,1))

            lcd_rect = self.lcd.DISPLAY.get_rect(topleft=self.lcd.blitloc) #(0,0)) #self.lcd.blitloc)

            # Translate actual to y=0, x adjusted by lcd offset
            if lcd_rect.colliderect(mouse_actual):
                mx -= self.lcd.offset #100 #offset
                mouse_rect = pygame.Rect((mx, 0),(1,1))
                collide = mouse_rect.collidelistall(self.chopper.rects)

                if collide:
                    self.drag = True
                    self.slice_idx = collide[0]
                    self.drag_rect = self.chopper.rects[self.slice_idx]
                else:
                    self.chopper.make_slice()
                    collide = mouse_rect.collidelistall(self.chopper.rects)

                    if collide:
                        self.drag = True
                        self.slice_idx = collide[0]
                        self.drag_rect = self.chopper.rects[self.slice_idx]

        elif event.type == pygame.MOUSEMOTION and self.drag:
            self.chop_motion()

        elif event.type == MOUSEBUTTONUP and event.button == 1 and self.drag:
            self.drag = False
            self.chopper.update_slices()
            self.slice_idx = self.chopper.rects.index(self.drag_rect) # works

        elif self.typer != None:
            self.typer.typer_event(event)
            if self.typer.active:
                self.lcd.make_footer(self.footer_dict['typing'])

            else:
                self.lcd.make_footer(self.footer_dict[self.menu])
                self.commands.update(cmds[self.menu])

                if event.type == KEYDOWN:
                    self.handle_input(event)

        elif event.type == pygame.KEYDOWN:
            if (event.key == K_LEFT or event.key == K_RIGHT) and self.drag_rect:
                self.chop_tune(event.key)
                self.slice_idx = self.chopper.rects.index(self.drag_rect)

            elif event.key in self.pad_keys:
                self.chopper.play_slice(event, self.snd_engine)
            else:
                self.handle_input(event)

        return

    # --------------------------------------------------------------------------
    def update(self):
        lcd = self.lcd
        lcd.DISPLAY.fill(lcd.g2)

        if self.menu != 'main':
            if self.menu == 'to_pads':
                to_blit, header_line = self.typer_update("Select Bank", prompt=True)
            else:
                to_blit, header_line = self.typer_update(name_type="File")
        else:
            header_line = True
            lcd = self.lcd
            self.chopper.draw_editor(self.slice_idx)

            if self.slice_idx != None:
                start, end = self.chopper.endpoints[self.slice_idx]
                slice = self.slice_idx+1
            else:
                start = 0
                end = None
                slice = self.slice_idx

            vals = [f"{slice}", f"{end}"] #
            content = [lcd.make_text(loc, text, (0,0,0))for loc, text in zip(lcd.v_coords, vals)]
            to_blit = [lcd.keys, lcd.menu, content]
            lcd.DISPLAY.blit(self.chopper.wav_surface, (0, lcd.font.height*2))

        for item in to_blit:
            self.lcd.DISPLAY.blits(item)

        self.lcd.draw_menu_line()
        if header_line:
            self.lcd.draw_header_line()
        return

    # --------------------------------------------------------------------------
    '''METHODS'''
    def remove_slice(self):
        # pop line and rect
        if self.slice_idx != None:
            self.chopper.rects.pop(self.slice_idx)
            self.chopper.edit_lines.pop(self.slice_idx)
            self.slice_idx = None
            self.drag = False
            self.drag_rect = None
            self.chopper.update_slices()
        return

    def chop_tune(self, ekey):
        if ekey == K_LEFT:
            self.drag_rect.x -=1
        elif ekey == K_RIGHT:
            self.drag_rect.x +=1

        x = self.drag_rect.centerx # DRY
        if x < 0:
            x = 1
        elif x > self.lcd.WIDTH:
            x = self.lcd.WIDTH-1

        self.drag_rect.centerx = x # fixes flag off screen, but if sample len == 0, div by zero
        self.chopper.edit_lines[self.slice_idx] = [(x, self.lcd.HEIGHT), (x, 0)]
        self.chopper.update_slices()
        return

    def chop_motion(self):
        mx, my = pygame.mouse.get_pos()
        mx -= self.lcd.offset #100

        # Clamp to LCD Width [DRY - used elsewhere...]
        if mx < 0:
            x = 1
        elif mx > self.lcd.WIDTH:
            x = self.lcd.WIDTH-1
        else:
            x = mx
        self.drag_rect.centerx = x
        self.chopper.edit_lines[self.slice_idx] = [(x, self.lcd.HEIGHT), (x, 0)]

        return

    def set_bank(self, bank):
        self.selected_bank = bank
        self.make_menu('to_mem')

    def write_chops(self):
        name = self.typer.text_to_render
        if len(name) == 0:
            return

        chops_objs = self.chopper.chop_play # these are pygame Sound objects
        # sound arrays / numpy arrys
        chops = {key: pygame.sndarray.array(chop) for key, chop in chops_objs.items()}

        i = 0
        for key, chop in chops.items():
            new_name = f"{name}-{str(i)}.wav"

            if new_name in list(self.snd_engine.sounds.keys()):
                new_name = "pydm_" + new_name
            temp_dir = self.dm.disk.sound_dir
            path = temp_dir / new_name
            write_wave(path, chop)

            # add sound to engine, with path used during write
            self.snd_engine.load_sound(path)

            if self.selected_bank is not None:
                pad = self.panel.banks[self.selected_bank][key]
                pad.sound_file = new_name
                self.snd_engine.set_pitches(new_name)
            i += 1

        self.dm.change_mode("main")
        return


#
