from pathlib import Path

import numpy as np

import pygame
from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command
from pydm.gui.lcd import Typer
from pydm.gui.editors import Truncator, write_wave
from pydm.core.snd_engine import moog_filter

# ------ Commands ------ #
close_menu = Command(None, 'make_menu', 'main')

cmds = {
    'main': {
        'softkey_1': Command(None, 'make_menu', 'to_mem'),
        'softkey_2': Command(None, 'undo'),
        'softkey_3': Command(None, 'reverse_snd'),
        'softkey_4': Command(None, 'filter_snd'),
        'softkey_5': Command(None, 'truncate'),
        'softkey_6': Command('dm', 'change_mode', 'main'),
        "idx-": Command(None, 'chop_tune', K_LEFT),
        "idx+": Command(None, 'chop_tune', K_RIGHT)
    },
    'to_mem': {
        'softkey_1': close_menu,
        'softkey_2': Command(None, 'write_chops'),
    }
}
# ------ LCD ------ #
headers = {
    'main':  {0: {0:"START: ", 1:"END: ", 3: "UNDOS: "}},
    'to_mem': {0: {0: ''}}
}

confirm = ["<NO>", "<YES>"]
typing = ["Typing..."]
use_name = ["<EXIT>", "<CONFIRM>"]

footers = {
    'main': ["<SAVE>", "<UNDO>", "<REVERSE>", "<FILTER>", "<TRUNCATE>", "<EXIT>"],
    'to_mem': use_name,
    'typing': typing
}

# ==============================================================================
class Edit(Mode):
    def __init__(self, dm, sound_name):
        super().__init__(dm)
        self.name = 'edit'
        self.header_dict = headers
        self.footer_dict = footers

        snd_path = self.snd_engine.sounds[sound_name]['path']
        snd_array = pygame.sndarray.array(self.snd_engine.mixer.Sound(snd_path))

        self.editor = Truncator(self.lcd, snd_array)

        self.shade_surface = self.editor.wav_surface.copy()
        self.shade_surface.fill((80, 80, 0))
        self.shade_surface.set_alpha(45)
        self.shade_rect = self.shade_surface.get_rect()

        self.sound_name = sound_name
        self.edit_stack = []
        self.drag = False
        self.drag_rect = None
        self.slice_idx = None
        self.make_menu('main')

    # --------------------------------------------------------------------------
    def make_menu(self, menu=None):
        body = {'text':''}

        if menu == 'main':
            self.typer = None
        elif menu in ['to_mem']: # these need typing submode
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
            lcd_rect = self.lcd.DISPLAY.get_rect(topleft = self.lcd.blitloc)
            # check if inside LCD here
            if lcd_rect.colliderect(mouse_actual):
                mx -= self.lcd.offset #100 #offset
                my = 0
                mouse_rect = pygame.Rect((mx,my),(1,1))
                collide = mouse_rect.collidelistall(self.editor.rects)
                if collide:
                    self.drag = True
                    self.slice_idx = collide[0]
                    self.drag_rect = self.editor.rects[self.slice_idx]

        elif event.type == pygame.MOUSEMOTION and self.drag: # add bound/clamp
            self.chop_motion()

        elif event.type == MOUSEBUTTONUP and event.button == 1 and self.drag:
            self.drag = False
            self.editor.update_endpoints()

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
            if (event.key == K_LEFT or event.key == K_RIGHT) and self.drag_rect: #selected_rect
                self.chop_tune(event.key)
            elif event.key in self.pad_keys:
                self.editor.play_slice(event, self.snd_engine)
            else:
                self.handle_input(event)

        return

    # --------------------------------------------------------------------------
    def update(self):
        lcd = self.lcd
        self.lcd.DISPLAY.fill(self.lcd.g2)

        if self.menu != 'main':
            to_blit, header_line = self.typer_update(
                name_type="File",
                check=list(self.snd_engine.sounds.keys()),
                check_text = ".wav"
            )
        else:
            header_line = True
            self.editor.draw_editor(self.slice_idx)

            vals = [f"{self.editor.start}", f"{self.editor.end}", f"{len(self.edit_stack)}"] #
            content = [lcd.make_text(loc, text, (0,0,0))for loc, text in zip(lcd.v_coords, vals)]

            to_blit = [lcd.keys, lcd.menu, content]

            area_rect = self.shade_rect.copy()
            area_rect.width = self.editor.edit_lines[0][0][0]
            self.editor.wav_surface.blit(self.shade_surface, self.shade_rect, area_rect)

            # offset | 600
            area_rect.width = self.lcd.WIDTH-self.editor.edit_lines[1][0][0] #self.editor.rects[1].left
            area_rect.x = self.editor.edit_lines[1][0][0]
            self.editor.wav_surface.blit(self.shade_surface, area_rect, area_rect)
            self.lcd.DISPLAY.blit(self.editor.wav_surface, (0,self.lcd.font.height*2))

        for item in to_blit:
            lcd.DISPLAY.blits(item)

        if header_line:
            lcd.draw_header_line()
        lcd.draw_menu_line()

        return

    # --------------------------------------------------------------------------
    '''METHODS'''
    # Need to bound moving the endpoints
    def chop_tune(self, ekey):
        if ekey == K_LEFT:
            self.drag_rect.x -=1
        elif ekey == K_RIGHT:
            self.drag_rect.x +=1

        self.check_endpoints()
        self.editor.update_endpoints()
        return

    def chop_motion(self):
        mx, my = pygame.mouse.get_pos()
        mx -= self.lcd.offset #100 #offset
        my = 0
        self.drag_rect.centerx = mx
        self.check_endpoints()
        return

    def check_endpoints(self):
        x = self.drag_rect.centerx
        # Clamp to LCD Width
        if x < 0:
            x = 0
        if x > self.lcd.WIDTH:
            x = self.lcd.WIDTH-1

        if self.slice_idx == 0:
            if self.editor.rects[0].right > self.editor.rects[1].left:
                self.editor.rects[0].right = self.editor.rects[1].left
                x = self.editor.rects[0].centerx
        elif self.slice_idx == 1:
            if self.editor.rects[1].left < self.editor.rects[0].right:
                self.editor.rects[1].left = self.editor.rects[0].right
                x = self.editor.rects[1].centerx

        self.drag_rect.centerx = x
        self.editor.edit_lines[self.slice_idx] = [(x, self.lcd.HEIGHT), (x, 0)]
        return

    def reverse_snd(self):
        self.msg_popup("Processing...")
        self.edit_stack.append(self.editor.snd_array.copy())
        self.editor.snd_array = np.ascontiguousarray(self.editor.snd_array[::-1, :])
        self.editor.remake_waveform()
        self.editor.init_endpoints()
        return

    def write_chops(self):
        name = self.typer.text_to_render#[:-1]
        if len(name) == 0:
            return

        name += ".wav"
        if name in list(self.snd_engine.sounds.keys()):
            return

        start = self.editor.start
        end = self.editor.end
        temp_dir = self.dm.disk.sound_dir
        path = temp_dir / name
        write_wave(path, self.editor.snd_array[start:end, :])

        self.snd_engine.load_sound(path) # add sound to engine, with path used during write
        self.dm.change_mode("main") #exit chop mode...

        return

    def undo(self):
        self.msg_popup("Processing...")
        if len(self.edit_stack) != 0:
            snd_arry = self.edit_stack.pop()
            self.editor.snd_array = snd_arry.copy()
            self.editor.remake_waveform()
            self.editor.init_endpoints()
        return

    def truncate(self):
        self.msg_popup("Processing...")
        start = self.editor.start
        end = self.editor.end

        self.edit_stack.append(self.editor.snd_array.copy())
        self.editor.snd_array = self.editor.snd_array[start:end, :].copy()
        self.editor.remake_waveform()
        self.editor.init_endpoints()
        return

    def filter_snd(self):
        self.edit_stack.append(self.editor.snd_array.copy())
        data = self.editor.snd_array.copy()

        # Seperate left and right channels for processing
        self.msg_popup("Processing...")
        channels = []
        if data.shape[1] == 2:
            yL = data[:, 0].copy() / 2 ** 15
            yR = data[:, 1].copy() / 2 ** 15
            channels.append(yL)
            channels.append(yR)
        else:
            yL = data[:, 0].copy() / 2 ** 15
            channels.append(yL)

        output = []
        for channel in channels:
            filt_data = moog_filter(channel)
            output.append(filt_data)

        if len(output) == 2:
            results = np.vstack([output[0], output[1]]).T
        else:
            results = output[0]

        self.editor.snd_array = np.ascontiguousarray(results)
        return


#
