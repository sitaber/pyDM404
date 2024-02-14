from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command, cursor_cmds

# ------ Commands ------ #
cmds = {
    'main': {
        'softkey_1': Command(None, 'make_menu', 'assign'),
        'softkey_6': Command('dm', 'change_mode', 'main'),
        "bank_toggle": Command('panel', 'toggle_bank'),
        K_a: Command(None, 'pad_preview', K_a),
        K_s: Command(None, 'pad_preview', K_s),
        K_d: Command(None, 'pad_preview', K_d),
        K_f: Command(None, 'pad_preview', K_f),
        K_g: Command(None, 'pad_preview', K_g),
        K_h: Command(None, 'pad_preview', K_h),
        K_j: Command(None, 'pad_preview', K_j),
        K_k: Command(None, 'pad_preview', K_k)
    },
    'assign': {
        'softkey_1': Command(None, 'preview'),
        'softkey_2': Command(None, 'set_pad'),
        'softkey_3': Command(None, 'spread_pad'),
        'softkey_6':  Command(None, 'make_menu', 'main'),
        K_a: Command(None, 'pad_select', K_a),
        K_s: Command(None, 'pad_select', K_s),
        K_d: Command(None, 'pad_select', K_d),
        K_f: Command(None, 'pad_select', K_f),
        K_g: Command(None, 'pad_select', K_g),
        K_h: Command(None, 'pad_select', K_h),
        K_j: Command(None, 'pad_select', K_j),
        K_k: Command(None, 'pad_select', K_k)
    }
}

# ------ LCD ------ #
headers = {
    'main' : {0: {0: "BANK:", 1:"PAD:", 2:"CH:"}, 1: {1: "SND:"}},
    'assign' : {0: {0: "BANK:", 1:"PAD:", 2:"CH:"}, 1: {1: "SND:"}}
}

footers = {
    'main': ["<SELECT>", "", "", "", "", "<EXIT>"],
    'assign': ["<PLAY>", "<ASSIGN>", "<SPAN BANK>", "", "", "<BACK>"]
}
# ==============================================================================
PAD_NAMES = {97: "A", 115: "S", 100: "D", 102: "F", 103: "G", 104: "H", 106: "J", 107: "K"}

class Assign(Mode):
    def __init__(self, dm):
        super().__init__(dm)
        self.name = 'assign'
        self.header_dict = headers
        self.footer_dict = footers

        self.pad_idx = None
        self.pad_bank = None
        self.make_menu('main')

    # --------------------------------------------------------------------------
    def make_menu(self, menu='main'):
        body = {'text': ''}

        if menu == 'assign' and self.pad_idx is not None:
            if self.snd_engine.sounds:
                text = ["None"]
                text.extend(list(self.snd_engine.sounds.keys()))
                pad = self.panel.banks[self.pad_bank][self.pad_idx]
                snd = pad.sound_file
                self.lcd.cursor_idx = text.index(snd)
            else:
                text = ['no sounds in memory']
            body = {'text': text}
        else:
            menu = 'main'

        self.menu = menu
        self.lcd.make_header(self.header_dict[menu])
        self.lcd.make_body(body)
        self.lcd.make_footer(self.footer_dict[menu])
        self.commands = cmds[menu]
        self.commands.update(cursor_cmds)

        if menu == 'assign':
            self.spread_text = self.lcd.menu[2]
        return

    # --------------------------------------------------------------------------
    def events(self, event):
        if event.type == KEYDOWN:
            if event.key in self.pad_keys:
                if self.menu == 'main':
                    self.pad_preview(event.key)
                else:
                    self.pad_select(event.key)

            elif event.key in self.chan_keys:
                self.set_chan(event.key)

            elif event.key in self.key_map:
                self.handle_input(event)

        elif event.type == MOUSEBUTTONDOWN and event.button == 1:
            self.panel.handle_click(self)

        return

    # --------------------------------------------------------------------------
    def update(self):
        lcd = self.lcd
        lcd.update_page()

        if self.pad_idx is None:
            text = "Select Bank (Press Pad keyboard key to select)"
            dialog = lcd.make_text(lcd.typer_lines[0], text, (0,0,0), menu=True)
            vals = ["None", "None", "None", "None"]
        else:
            dialog = None
            pad = self.panel.banks[self.pad_bank][self.pad_idx]
            snd = pad.sound_file
            ch = pad.channel
            vals = [f'{self.pad_bank}', f"{PAD_NAMES[self.pad_idx]}", f"{ch}", f"{snd}"]

        content = [lcd.make_text(loc, text, (0,0,0)) for loc, text in zip(lcd.v_coords, vals)]

        if self.menu == 'assign': # check if dialog is none....
            to_blit = [lcd.keys, content, lcd.to_display, [lcd.hilites[lcd.cursor_idx]], lcd.menu]
        else:
            to_blit = [lcd.keys, content, lcd.to_display, lcd.menu]

        if dialog is not None:
            to_blit.append([dialog])

        if self.pad_idx != 97 and self.menu == 'assign':
           self.lcd.menu[2] = self.lcd.menu[3]

        elif self.pad_idx == 97 and self.menu == 'assign':
           self.lcd.menu[2] = self.spread_text

        lcd.DISPLAY.fill(lcd.g2)
        for item in to_blit:
            lcd.DISPLAY.blits(item)

        lcd.draw_header_line()
        lcd.draw_menu_line()
        return

    # --------------------------------------------------------------------------
    '''METHODS'''
    def set_chan(self, ekey):
        pad = self.panel.banks[self.pad_bank][self.pad_idx]
        idx = self.chan_keys.index(ekey)
        if idx > 7:
            idx = idx-8

        pad.channel = idx+1
        return

    def pad_select(self, ekey):
        self.pad_idx = ekey  #self.pad_keys.index(ekey)
        self.pad_bank = self.panel.bank_name

        pad = self.panel.banks[self.pad_bank][ekey]
        snd = pad.sound_file
        return snd

    def pad_preview(self, ekey):
        snd = self.pad_select(ekey)
        if snd != 'None':
            self.snd_engine.preview(snd)
        return

    def preview(self, snd=None):
        if snd is None:
            self.snd_engine.preview(self.lcd.body_text[self.lcd.cursor_idx])
        else:
            self.snd_engine.preview(snd)
        return

    def set_pad(self):
        self.msg_popup("Processing...")
        sound_file = self.lcd.body_text[self.lcd.cursor_idx]
        pad = self.panel.banks[self.pad_bank][self.pad_idx]
        pad.sound_file = sound_file

        if sound_file != "None":
            if self.snd_engine.sounds[sound_file]['pitches'] is None:
                self.snd_engine.set_pitches(sound_file)
        else:
            current_sound = pad.sound_file
            self.snd_engine.unset_pitches(current_sound) # check for pitches again...
        return

    def spread_pad(self):
        if self.pad_idx != 97:
            return
        self.msg_popup("Processing...")
        sound_file = self.lcd.body_text[self.lcd.cursor_idx]
        selected_pad = self.panel.banks[self.pad_bank][self.pad_idx]
        chan = selected_pad.channel

        banks = self.panel.banks[self.pad_bank]
        for key in banks:
            pad = banks[key]

            if sound_file != "None":
                pad.sound_file = sound_file
                pad.channel = chan

                if self.snd_engine.sounds[sound_file]['pitches'] is None:
                    self.snd_engine.set_pitches(sound_file)
            else:
                pad.sound_file = "None"
        return





# EOF
