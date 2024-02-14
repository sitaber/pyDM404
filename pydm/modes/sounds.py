from pathlib import Path
import time
import shutil

import tkinter
import tkinter.filedialog

import pygame
from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command, cursor_cmds
from pydm.gui.lcd import Typer
from pydm.modes.chopit import Chop
from pydm.modes.edit import Edit

# ------ Commands ------ #
cmds = {
    'cursor': cursor_cmds,
    'main': {
        'softkey_1': Command(None, 'make_menu', 'option'),
        'softkey_6': Command('dm', 'change_mode', 'main'),
    },
    'select_sound' : {
        'softkey_1': Command(None, 'preview'),
        'softkey_2': Command(None, 'chop_mode'),
        'softkey_6': Command(None, 'make_menu', "main")
    },
    'edit_select' : {
        'softkey_1': Command(None, 'preview'),
        'softkey_2': Command(None, 'edit_mode'),
        'softkey_6': Command(None, 'make_menu', "main")
    },
    'rename_select' : {
        'softkey_1': Command(None, 'preview'),
        'softkey_2': Command(None, 'make_menu', "rename_snd"),
        'softkey_6': Command(None, 'make_menu', "main")
    },
    'delete_select' : {
        'softkey_1': Command(None, 'preview'),
        'softkey_2': Command(None, 'make_menu', "del_snd"), # prompt
        'softkey_6': Command(None, 'make_menu', "main")
    },
    "rename_snd": {
        'softkey_1': Command(None, 'make_menu', "main"),
        'softkey_2': Command(None, 'do_rename'),
    },
    'del_snd': {
        'softkey_1': Command(None, 'make_menu', "main"),
        'softkey_2': Command(None, 'do_del'),
    },
    "disk_error": {
        'softkey_1':Command('dm', 'change_mode', 'main'),
    }
}

# ------ LCD ------ #
# Edit, Load and Chop
headers = {
    'main': {0: {0:"Select Function"}},
    'select_sound': {0: {0: "Select Sound"}},
    'edit_select': {0: {0: "Select Sound"}},
    'rename_select': {0: {0: "Select Sound"}},
    'delete_select': {0: {0: "Select Sound"}},
    'rename_snd': {0: {0: ""}},
    'del_snd': {0: {0: ""}},
}

select_option = ["<SELECT>", "", "", "", "", "<EXIT>"]
select_sound = ["<PREVIEW>", "<SELECT>", "", "", "", "<BACK>"]

confirm = ["<NO>", "<YES>"]
#typing = ["Typing..."]
use_name = ["<EXIT>", "<CONFIRM>"]

footers = {
    'main': select_option,
    'select_sound': select_sound,
    'edit_select': select_sound,
    'rename_select': select_sound,
    'delete_select': select_sound,
    'typing': ["Typing..."],
    'rename_snd': use_name,
    'del_snd': confirm
}

options = {
    'Load Sound': 'load_sound',
    'Chop Sound': 'select_sound',
    'Load and Chop': 'load_chop',
    'Edit Sound': 'edit_select',
    'Rename Sound': 'rename_select',
    'Delete Sound': 'delete_select',
}
# ==============================================================================
class Sounds(Mode):
    def __init__(self, dm):
        super().__init__(dm)
        self.name = 'sounds'
        self.header_dict = headers
        self.footer_dict = footers

        self.to_del = None
        self.make_menu('main')

    # -----------------------------------------------------------------------------
    def make_menu(self, menu=None):
        body = {'text':''}

        if menu == 'option':
            option = self.lcd.body_text[self.lcd.cursor_idx]
            menu = options[option]

        if menu == 'load_sound':
            self.prompt_file()
            menu = 'main'

        elif menu == 'load_chop':
            self.prompt_file(chop=True)
            return

        if menu == 'main':
            text = list(options.keys())
            body = {'text': text}
            self.typer = None

        elif menu in ['select_sound', 'edit_select', 'rename_select', 'delete_select']:
            if self.snd_engine.sounds:
                text = list(self.snd_engine.sounds.keys())
            else:
                text = ['no sounds in memory']
            body = {'text': text}

        if menu == 'rename_snd':
            self.typer = Typer(mode='text')
            self.rename_snd()

        if menu == 'del_snd':
            self.to_del = self.lcd.body_text[self.lcd.cursor_idx]

        self.menu = menu
        self.lcd.cursor_idx = 0
        self.lcd.make_header(self.header_dict[menu])
        self.lcd.make_body(body)
        self.lcd.make_footer(self.footer_dict[menu])
        self.commands = cmds[menu]
        self.commands.update(cmds['cursor'])
        return

    # --------------------------------------------------------------------------
    def events(self, event):
        '''Mode Event Handler'''
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            self.panel.handle_click(self)
        elif self.typer != None:
            self.typer.typer_event(event)
            if self.typer.active:
                self.lcd.make_footer(self.footer_dict['typing'])
            else:
                self.lcd.make_footer(self.footer_dict[self.menu])
                self.commands.update(cmds[self.menu])
                if event.type == KEYDOWN:
                    self.handle_input(event)
        elif event.type == KEYDOWN:
            self.handle_input(event)

        return

    # --------------------------------------------------------------------------
    def update(self):
        lcd = self.lcd
        if self.menu in ['rename_snd', 'del_snd']:
            if self.menu == 'del_snd':
                to_blit, header_line = self.typer_update(
                    texta = f"Delete Sound from Disk: {self.to_del}?",
                    prompt=True
                )
            else:
                to_blit, header_line = self.typer_update(
                    name_type="Sound",
                    check = list(self.snd_engine.sounds.keys()),
                    check_text = "." + self.rename_dict['ext']
                )
        else:
            header_line = True
            lcd.update_page()
            to_blit = [lcd.keys, lcd.to_display, [lcd.hilites[lcd.cursor_idx]], lcd.menu]

        lcd.DISPLAY.fill(lcd.g2)
        for item in to_blit:
            lcd.DISPLAY.blits(item)

        if header_line:
            lcd.draw_header_line()
        lcd.draw_menu_line()
        return

    # --------------------------------------------------------------------------
    '''METHODS'''
    def preview(self):
        self.snd_engine.preview(self.lcd.body_text[self.lcd.cursor_idx])
        return

    def edit_mode(self):
        self.msg_popup("Loading Editor...")
        sound_name = self.lcd.body_text[self.lcd.cursor_idx]
        
        snd_path = self.snd_engine.sounds[sound_name]['path']
        snd_array = pygame.sndarray.array(self.snd_engine.mixer.Sound(snd_path))
        if snd_array.size == 0: # if size == 0 exit with msg
            self.msg_popup("Cannot edit zero length sound...", error=True)
        else:
            self.dm.mode = Edit(self.dm, sound_name)

    def chop_mode(self):
        self.msg_popup("Loading Chopper...")
        sound_name = self.lcd.body_text[self.lcd.cursor_idx]
        
        snd_path = self.snd_engine.sounds[sound_name]['path']
        snd_array = pygame.sndarray.array(self.snd_engine.mixer.Sound(snd_path))
        if snd_array.size == 0: # if size == 0 exit with msg
            self.msg_popup("Cannot edit zero length sound...", error=True)
        else:
            self.dm.mode = Chop(self.dm, sound_name, from_memory=True)

    def prompt_file(self, chop=False):
        """Create a Tk file dialog and cleanup when finished"""
        # Works, need to convert to path obj and load into snd engine
        my_filetypes = [('wav files', '.wav'), ('mp3 files', '.mp3')]
        top = tkinter.Tk()
        top.withdraw()  # hide window
        file_name = tkinter.filedialog.askopenfilename(
            parent=top, 
            filetypes=my_filetypes,
            initialdir=self.dm.ROOT_DIR,
            #title="Dialog box",
        )
        top.destroy()

        if len(file_name) == 0:
            return

        if Path(file_name).name in list(self.snd_engine.sounds.keys()):
            self.msg_popup('File exists in memory, re-select', error=True)
            return

        if chop == True:
            self.msg_popup("Loading Sound into Chopper...")
            self.dm.mode = Chop(self.dm, file_name, from_memory=False)
        else:
            # SND FILES | this has to be updated when loading a new file/sound
            self.msg_popup("Loading Sound...")
            source = Path(file_name)
            dest = self.dm.disk.sound_dir / source.name
            shutil.copy(source, dest)
            self.snd_engine.load_sound(Path(dest))
        return

    def do_del(self):
        # Now loop over pads and set
        self.msg_popup("Processing...")
        for bank in self.panel.banks.values():
            for pad in bank.values():
                if pad.sound_file == self.to_del:
                    pad.sound_file = "None"

        path = self.snd_engine.sounds[self.to_del]['path']
        path.unlink()
        del self.snd_engine.sounds[self.to_del]

        self.save_pad_config()
        self.make_menu("main")
        return

    def rename_snd(self):
        current_name = self.lcd.body_text[self.lcd.cursor_idx]
        snd = self.snd_engine.sounds[current_name]
        self.rename_dict = {
            'name': current_name,
            'ext': current_name.split(".")[1],
            'path': snd['path'],
            'pitches': snd['pitches']
        }
        return

    def do_rename(self):
        name = self.typer.text_to_render
        if len(name) != 0:
            f_ext = self.rename_dict['ext']
            new_path = self.rename_dict['path'].with_name(name + f".{f_ext}")

            if new_path.name in list(self.snd_engine.sounds.keys()):
                return

            self.msg_popup("Processing...")
            self.snd_engine.sounds[new_path.name] = {
                'path': new_path,
                'pitches':self.rename_dict['pitches']
            }

            # Now loop over pads and set
            for bank in self.panel.banks.values():
                for pad in bank.values():
                    if pad.sound_file == self.rename_dict['name']:
                        pad.sound_file = new_path.name

            self.rename_dict['path'].rename(new_path)
            del self.snd_engine.sounds[self.rename_dict['name']]
            self.save_pad_config()
            self.make_menu("main")
        return

    def save_pad_config(self):
        # Make list of pad dictionaries
        banks = self.panel.banks
        pad_configs = [
            pad.to_dict for bank in banks.values()
            for pad in bank.values() if pad.sound_file != "None"
        ]
        # Set config & save
        self.dm.disk.config['pads'] = pad_configs
        self.dm.disk.save_config()
        return

# EOF
