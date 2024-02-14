from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command, cursor_cmds
from pydm.gui.lcd import Typer

# ------ Commands ------ #
cmds = {
    'cursor': cursor_cmds,
    'main': {
        'softkey_1': Command(None, 'make_menu'),
        'softkey_2': Command(None, 'make_menu', 'name_song'),
        'softkey_3': Command(None, 'make_menu', 'del_song'),
        'softkey_6': Command(None, 'exit_mode'),
    },
    'song': {
        'softkey_1': Command(None, 'set_idx0', -1),
        'softkey_2': Command(None, 'set_idx0', 1),
        'softkey_3': Command(None, 'add_seq'),
        'softkey_4': Command(None, 'del_seq'),
        'softkey_6': Command(None, 'make_menu', 'main'),
        "BPM_minus": Command('sequencer', 'set_bpm', -0.5),
        "BPM_plus": Command('sequencer', 'set_bpm', 0.5),
        "BPM_--": Command('sequencer', 'set_bpm', -10),
        "BPM_++": Command('sequencer', 'set_bpm', 10),
        "play": Command(None, 'play_song'),
        "mixer_toggle": Command('panel', 'toggle_mixer'),
        "bank_toggle": Command('panel', 'toggle_bank'),
    },
    'name_song': {
        'softkey_1': Command(None, 'make_menu', 'main'),
        'softkey_2': Command(None, 'name_song'),
    },
    'del_song': {
        'softkey_1': Command(None, 'make_menu', 'main'),
        'softkey_2': Command(None, 'delete_song'),
    }
}

# ------ LCD ------ #
no_text = {0: {0: ""}}
headers = {
    'main': {0: {0: "Select Song and/or Function"}},
    'del_song': {0: {0: ""}},
    'name_song': {0: {0: ""}},
    'song': {
        0: {0:"SONG: ", 2:"BPM: ", 3:"Length: "},
        1: {0:"SEQ TO ADD: "}
    },
}

# --- FOOTERS --- #
song_main = ["<SELECT>", "<RENAME>", "<DEL>", "", "", "<EXIT>"]
song_edit = ["<SEQ->", "<SEQ+>","<INSERT>", "<DEL>", "", "<EXIT>"]

confirm = ["<NO>", "<YES>"]
typing = ["Typing..."]
use_name = ["<EXIT>", "<CONFIRM>"]

footers = {
    'main': song_main,
    'song': song_edit,
    'del_song': confirm,
    'name_song': use_name,
    'typing': typing,
}

# ==========================================================================
class Song(Mode):
    def __init__(self, dm):
        super().__init__(dm)
        self.name = 'song'
        self.header_dict = headers
        self.footer_dict = footers

        self.songs = self.dm.disk.config['songs']
        self.seqs = self.dm.disk.config['seqs']

        self.current_song = None
        self.make_menu('main')

    # --------------------------------------------------------------------------
    def make_menu(self, menu=None):
        body = {'text':''}
   
        if menu is None:
            selected_song = self.lcd.body_text[self.lcd.cursor_idx]
            self.song_num = int(selected_song.split()[0]) # gives index of song list
            self.set_song()

            if self.song_init:
                menu = 'song'
                self.step = 1
            else:
                menu = 'name_song'
                self.typer = Typer(mode='text')
        
        elif menu == 'name_song':
            selected_song = self.lcd.body_text[self.lcd.cursor_idx]
            self.song_num = int(selected_song.split()[0]) # gives index of song list
            self.set_song()
            self.typer = Typer(mode='text')
            
        elif menu == 'del_song':     
            selected_song = self.lcd.body_text[self.lcd.cursor_idx]
            self.song_num = int(selected_song.split()[0]) # gives index of song list
            self.set_song()
            if self.song_init is False:
                menu = 'main'

        if menu == 'main':
            text = [f"{idx} {song['name']}" for idx, song in enumerate(self.songs)]
            body = {'text': text}
            self.typer = None
            if self.sequencer.state.playing:
                self.play_song()
                
        self.menu = menu
        self.idx0 = 0
        self.lcd.cursor_idx = 0
        self.lcd.make_header(self.header_dict[menu])
        self.lcd.make_body(body)
        self.lcd.make_footer(self.footer_dict[menu])
        self.commands = cmds[menu]
        self.commands.update(cmds['cursor'])
        return

    # --------------------------------------------------------------------------
    def events(self, event):
        '''Assign Mode Event Handler'''
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            self.panel.handle_click(self)

        elif (self.panel.vol_knob.clicked or self.panel.fader_clicked):
            if event.type == MOUSEMOTION:
                if self.panel.vol_knob.clicked:
                    self.panel.vol_knob.update()
                    self.snd_engine.volume = self.panel.vol_knob.index/10

                elif self.panel.fader_clicked:
                    self.panel.fader_motion()

            elif event.type == MOUSEBUTTONUP and event.button == 1:
                if self.panel.vol_knob.clicked:
                    self.panel.vol_knob.handle_click()
                elif self.panel.fader_clicked:
                    self.panel.fader_clicked = False

        elif self.typer != None:
            self.typer.typer_event(event)
            if self.typer.active:
                self.lcd.make_footer(self.footer_dict['typing'])
            else:
                self.lcd.make_footer(self.footer_dict[self.menu])
                self.commands = cmds[self.menu]
                if event.type == KEYDOWN:
                    self.handle_input(event)

        elif event.type == KEYDOWN:
            self.handle_input(event)

        return

    # --------------------------------------------------------------------------
    def update(self):
        lcd = self.lcd
        if self.sequencer.state.playing:
            self.song_update()

        if self.menu in ['del_song', 'name_song']:
            if self.menu == 'del_song':
                to_blit, header_line = self.typer_update(
                    texta = f"Confirm Delete Song?: {self.current_song['name']}",
                    prompt=True
                )
            else:
                to_blit, header_line = self.typer_update(name_type="Song")
        else:
            header_line = True
            lcd.update_page()

            if self.menu == 'song':
                text = [
                    f"STEP {step} - SEQ {seq} {self.seqs[seq]['name']}"
                    for step, seq in enumerate(self.current_song['seqs'])
                ]
                text.append("END")
                body = {'text': text}
                self.lcd.make_body(body)
                lcd.update_page()

                bars = 0
                self.current_song['bpm'] = self.sequencer.bpm

                if len(self.current_song['seqs']) != 0:
                    for seq_num in self.current_song['seqs']:
                        if self.sequencer.sequences[seq_num].size != 1:
                            bars += self.sequencer.sequences[seq_num].shape[1]//96

                vals = [
                    f"{self.current_song['name']}", f"{self.current_song['bpm']}", f'{bars}',
                    f"{self.idx0} - {self.seqs[self.idx0]['name']}"
                ]

                content = [lcd.make_text(loc, text, (0,0,0)) for loc, text in zip(lcd.v_coords, vals)]
                to_blit = [lcd.keys, content, lcd.to_display, [lcd.hilites[lcd.cursor_idx]], lcd.menu]

            else:
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
    def set_song(self):
        self.current_song = self.songs[self.song_num]

        if self.current_song['name'] == "(unused)":
            self.song_init = False
        else:
            self.song_init = True
            self.sequencer.bpm = self.current_song['bpm']

        self.songs[self.song_num] = self.current_song
        return

    def name_song(self):
        song_name = self.typer.text_to_render
        if len(song_name) == 0 or song_name == "(unused)":
            return
        self.current_song['name'] = song_name # we init song here, set bpm to global
        self.current_song['bpm'] = self.sequencer.bpm
        self.make_menu('main')
        return

    def delete_song(self):
        self.songs[self.song_num] = {"name": "(unused)", "seqs": [], "bpm": 120}
        self.make_menu('main')
        return

    def play_song(self):
        self.sequencer.toggle_play(song=True, seq_list=self.current_song['seqs'])
        return

    def song_update(self):
        check_seq, _ = self.sequencer.update()
        if check_seq:
            self.snd_engine.sequncer_play(self.sequencer, self.panel.banks)
        return

    # ----- Individual song
    def set_idx0(self, val):
        self.idx0 = max(0, min(39, self.idx0+val))
        return

    # --- STEP METHODS | Disable when playing
    def add_seq(self):
        if self.sequencer.state.playing:
            return

        selected_step = self.lcd.body_text[self.lcd.cursor_idx]
        if selected_step == 'END':
            self.current_song['seqs'].append(self.idx0)
        else:
            self.current_song['seqs'].insert(self.lcd.cursor_idx, self.idx0)

        self.lcd.cursor_idx += 1
        return

    def del_seq(self):
        if self.sequencer.state.playing:
            return

        selected_step = self.lcd.body_text[self.lcd.cursor_idx]
        if selected_step == 'END':
            return
        else:
            self.current_song['seqs'].pop(self.lcd.cursor_idx)

        return

    # ----- Exit mode and clean up
    def exit_mode(self):
        # pass/set the song config on disk and change mode to perfrom/main
        if self.sequencer.state.playing:
            self.play_song()
        self.dm.disk.config['songs'] = self.songs
        self.dm.change_mode('main')
        return

# EOF
