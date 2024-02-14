import shutil
from pathlib import Path
import os # We might want to change to pathlib.Path (its easier to use)
import json

import pygame
from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command, cursor_cmds
from pydm.core import FloppyDisk
from pydm.gui.lcd import Typer

# ------ Commands
close_menu = Command(None, 'make_menu', 'main')

cmds = {
    'cursor': cursor_cmds,
    'main': {
        'softkey_1': Command(None, 'make_menu', None),
        'softkey_6': Command('dm', 'change_mode', 'main')
    },
    'load': {
        'softkey_1': Command(None, 'make_menu', 'load_it'),
        'softkey_6': close_menu
    },
    'load_it': {
        'softkey_1': close_menu,
        'softkey_2': Command(None, 'load_disk'),
    },
    'save': {
        'softkey_1': close_menu,
        'softkey_2': Command(None, 'save_disk'),
    },
    'save_as': {
        'softkey_1': close_menu,
        'softkey_2': Command(None, 'save_as'),
    },
    'new_disk': {
        'softkey_1': close_menu,
        'softkey_2': Command(None, 'new_disk'),
    }
}

# ------ LCD ------ #
no_text = {0: {0:""}}
headers = {
    'main': {0: {0: "Current Disk: "}, 1: {0:"Select Function"}},
    'load': {0: {0:"Select Disk To Load"}},
    'load_it': no_text,
    'save': no_text,
    'save_as': no_text,
    'new_disk': no_text
}

select = ["<SELECT>", "", "", "", "", "<EXIT>"]
confirm = ["<NO>", "<YES>"]
typing = ["Typing..."]
use_name = ["<EXIT>", "<CONFIRM>"]
clear_dialog = ["<BACK>"]

footers = {
    'main': select,
    'load': select,
    'load_it': confirm,
    'save': confirm,
    'save_as': use_name,
    'new_disk': use_name,
    'typing': typing
}

options = {
    'Load Disk': 'load',
    'Save Disk': 'save',
    'Save Disk As': 'save_as',
    'New Disk': 'new_disk'
}

# ==============================================================================
class Disk(Mode):
    def __init__(self, dm):
        super().__init__(dm)
        self.name = 'disk'
        self.header_dict = headers
        self.footer_dict = footers

        self.make_menu('main')

    # --------------------------------------------------------------------------
    def make_menu(self, menu=None):
        body = {'text':''}

        if menu == 'main':
            text = list(options.keys())
            body = {'text': text}
            self.typer = None
            self.lcd.cursor_idx = 0

        elif menu is None:
            option = self.lcd.body_text[self.lcd.cursor_idx]
            menu = options[option]

        if menu in ['save_as', 'new_disk']:
            self.typer = Typer(mode='text')

        elif menu in ['load', 'load_it']:
            text = sorted(os.listdir(self.dm.ROOT_DIR / Path(f"DISKS")))#key=len
            body = {'text': text}

        self.menu = menu

        self.lcd.make_header(self.header_dict[menu])
        self.lcd.make_body(body)
        self.lcd.make_footer(self.footer_dict[menu])
        self.commands = cmds[menu]
        self.commands.update(cmds['cursor'])

        return

    # --------------------------------------------------------------------------
    def events(self, event):
        """DISK Mode Event Handler"""
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
        if self.menu not in ['main', 'load']:
            if self.menu == 'load_it':
                to_blit, header_line = self.typer_update(
                    texta = f"Load Disk: {lcd.body_text[lcd.cursor_idx]}?",
                    textb = "Load Disk will overwrite memory.",
                    prompt=True
                )
            elif self.menu == 'save':
                if self.dm.disk.name != "None":
                    to_blit, header_line = self.typer_update(
                        texta = f"Save to Current Disk: {self.dm.disk.name}?",
                        prompt=True
                    )
                else:
                    self.msg_popup(msg="No disk loaded! Use Save As...", error=True)
                    self.make_menu("main")
                    return
            else:
                to_blit, header_line = self.typer_update(
                    name_type="Disk",
                    check=sorted(os.listdir(self.dm.ROOT_DIR / Path(f"DISKS")))
                )
        else:
            header_line = True
            lcd = self.lcd
            lcd.update_page()
            to_blit = [lcd.keys, lcd.to_display, [lcd.hilites[lcd.cursor_idx]], lcd.menu]

            if self.menu == 'main':
                vals = ["None"]
                if self.dm.disk.name != "None":
                    vals = [f"{self.dm.disk.name}"]

                content = [lcd.make_text(loc, text, (0,0,0)) for loc, text in zip(lcd.v_coords, vals)]
                to_blit = [lcd.keys, content, lcd.to_display, [lcd.hilites[lcd.cursor_idx]], lcd.menu]

        lcd.DISPLAY.fill(lcd.g2)
        for item in to_blit:
            lcd.DISPLAY.blits(item)

        if header_line:
            lcd.draw_header_line()
        lcd.draw_menu_line()
        return

    # --------------------------------------------------------------------------
    '''METHODS'''
    def load_disk(self, disk_name=None):
        if disk_name is None:
            disk_name = self.lcd.body_text[self.lcd.cursor_idx]

        self.msg_popup(msg="Loading Disk...")

        self.dm.disk = FloppyDisk(self.dm.ROOT_DIR, disk_name)
        self.snd_engine.load_sounds(self.dm.disk.sound_dir)

        self.panel.make_pad_banks()
        self.panel.load_pad_config(self.dm.disk, self.snd_engine)

        self.sequencer.sequences = self.dm.disk.load_seqs()
        self.sequencer.load_config(self.dm.disk.config)
        self.sequencer.set_seq()

        self.dm.change_mode("main")
        return

    def save_disk(self, config=None):
        if self.dm.disk.name != "None": # cannot save default | change to None ?
            # Make list of pad dictionaries
            banks = self.panel.banks
            pad_configs = [
                pad.to_dict for bank in banks.values()
                for pad in bank.values() if pad.sound_file != "None"
            ]

            # Get sequence array from sequencer & save
            seqs = self.sequencer.sequences
            self.dm.disk.save_seq(seqs)

            # Set config & save
            self.dm.disk.config['pads'] = pad_configs
            self.dm.disk.config['seqs'] = self.sequencer.seq_configs
            self.dm.disk.config['global']['bpm'] = self.sequencer.bpm
            self.dm.disk.config['global']['met'] = self.sequencer.state.met
            self.dm.disk.config['global']['quantize'] = self.sequencer.tc
            self.dm.disk.save_config()

            self.snd_engine.reload_sounds(self.dm.disk.sound_dir)
            self.dm.change_mode("main")
        return

    def save_as(self):
        disk_name = self.typer.text_to_render
        names = sorted(os.listdir(self.dm.ROOT_DIR / Path(f"DISKS")))
        if len(disk_name) == 0 or disk_name in names:
            return

        # Copy source (current disk) to destination path
        source = self.dm.disk.path
        dest = self.dm.ROOT_DIR / Path(f"DISKS/{disk_name}")
        shutil.copytree(source, dest)

        self.dm.disk.path = dest
        self.dm.disk.sound_dir = dest / "samples" #update path
        self.dm.disk.name = disk_name
        self.save_disk()
        return

    def new_disk(self):
        '''Use BlankDisk DIR to create a new blank disk'''
        disk_name = self.typer.text_to_render
        names = sorted(os.listdir(self.dm.ROOT_DIR / Path(f"DISKS")))
        if len(disk_name) == 0 or disk_name in names:
            return

        source = self.dm.ROOT_DIR / Path("assets/BlankDisk") # need to copy the blank disk
        dest = self.dm.ROOT_DIR / Path(f"DISKS/{disk_name}")
        shutil.copytree(source, dest)

        self.load_disk(disk_name) # Load new disk (overwrites all data in memory)
        return


# EOF
