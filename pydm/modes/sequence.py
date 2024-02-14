from pygame.locals import *

from pydm.modes.mode import Mode, Default, Command, cursor_cmds
from pydm.gui.lcd import Typer

# ------ Commands ------ #
cmds = {
    'cursor': cursor_cmds,
    'main': {
        'softkey_1': Command(None, 'make_menu'),
        'softkey_2': Command(None, 'make_menu', 'name_seq'),
        'softkey_3': Command(None, 'make_menu', 'copy_seq'),
        'softkey_4': Command(None, 'make_menu', 'del_seq'),
        'softkey_6': Command('dm', 'change_mode', 'main')
    },
    'new_seq': {
        'softkey_1': Command(None, 'change_func_val', -1),
        'softkey_2': Command(None, 'change_func_val', 1),
        'softkey_3': Command(None, 'init_sequence'),
        'softkey_6': Command(None, 'make_menu', 'main'),
    },
    'name_seq': {
        'softkey_1': Command(None, 'make_menu', 'main'),
        'softkey_2': Command(None, 'name_seq'),
    },
    'copy_seq': {
        'softkey_1': Command(None, 'change_func_val', -1),
        'softkey_2': Command(None, 'change_func_val', 1),
        'softkey_3': Command(None, 'copy_sequence'),
        'softkey_6': Command(None, 'make_menu', 'main'),
    },
    'del_seq': {
        'softkey_1': Command(None, 'make_menu', 'main'),
        'softkey_2': Command(None, 'del_sequence')
    }
}

# ------ LCD ------ #
headers = {
    'main': {0: {0:"Select Sequence and/or Function",}},
    'name_seq': {0: {0: ""}},
    'copy_seq': {
        0: {0: "Select Destination Sequence"},
        1: {0: "Copy To: "}
    },
    'new_seq': {
        0: {0:"Enter Sequence Length (Max is 8 Bars)"},
        1: {0: "BARS: "}
    },
    'del_seq': {1: {0:""}},
}

main = ["<SELECT>", "<NAME>", "<COPY>", "<DEL>", "", "<EXIT>"]
new_seq = ["<BAR->", "<BAR+>", "<DO IT>", "", "", "<EXIT>"]
copy_seq = ["<SEQ->", "<SEQ+>", "<DO IT>", "", "", "<EXIT>"]

confirm_footer = ["<NO>", "<YES>"]
use_name_footer = ["<EXIT>", "<CONFIRM>"]
typing_footer = ["Typing..."]

footers = {
    'main': main,
    'new_seq': new_seq,
    'name_seq': use_name_footer,
    'copy_seq': copy_seq,
    'del_seq': confirm_footer,
    'typing': typing_footer
}

# ==========================================================================
class Seq(Mode):
    def __init__(self, dm):
        super().__init__(dm)
        self.name = 'seq'
        self.header_dict = headers
        self.footer_dict = footers

        self.seqs = self.dm.disk.config['seqs']
        self.func_val = 0
        self.seq_init = False
        self.make_menu('main')

    # --------------------------------------------------------------------------
    def make_menu(self, menu=None):
        body = {'text':''}

        if menu != 'main':
            self.check_seq()

        if menu is None:
            if self.seq_init is False:
                menu = 'new_seq'
                self.func_val = 1
            elif self.seq_init is True:
                # exit mode to selected seq
                self.exit_mode()
                return

        elif menu in ['name_seq', 'copy_seq']:
            if self.seq_init is False: # cant name unused seq
                menu = 'main'
            elif menu == 'name_seq':
                self.typer = Typer(mode='text')
            elif menu == 'copy_seq':
                self.func_val = 0

        if menu == 'main':
            text = [f"{idx} {seq['name']}" for idx, seq in enumerate(self.seqs)]
            body = {'text': text}
            self.typer = None

        self.menu = menu
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
        if self.menu in ['del_seq', 'name_seq']:
            if self.menu == 'del_seq':
                to_blit, header_line = self.typer_update("Confirm Delete?", prompt=True)
            else:
                to_blit, header_line = self.typer_update(name_type="SEQ")
        else:
            header_line = True

            lcd.update_page()

            if self.menu in ["main"]:
                to_blit = [lcd.keys, lcd.to_display, [lcd.hilites[lcd.cursor_idx]], lcd.menu]

            elif self.menu in ['new_seq', 'copy_seq']:
                vals = ["", f"{self.func_val}"]
                content = [lcd.make_text(loc, text, (0,0,0)) for loc, text in zip(lcd.v_coords, vals)]
                to_blit = [lcd.keys, content, lcd.to_display, lcd.menu]

        lcd.DISPLAY.fill(lcd.g2)
        for item in to_blit:
            lcd.DISPLAY.blits(item)

        if header_line:
            lcd.draw_header_line()
        lcd.draw_menu_line()

        return

    # --------------------------------------------------------------------------
    '''METHODS'''
    def check_seq(self):
        selected_seq = self.lcd.body_text[self.lcd.cursor_idx]
        self.seq_num = int(selected_seq.split()[0]) # gives index of song list

        self.seq_name = self.seqs[self.seq_num]['name']

        if self.seq_name == "(unused)":
            self.seq_init = False
        else:
            self.seq_init = True
        return

    def name_seq(self):
        seq_name = self.typer.text_to_render #[:-1]
        if len(seq_name) == 0 or seq_name == "(unused)":
            return
        self.seqs[self.seq_num]['name'] = seq_name
        self.make_menu('main')
        return

    def change_func_val(self, val):
        seqs = list(range(len(self.sequencer.sequences)))
        if self.menu == 'copy_seq':
            self.func_val = max(0, min(len(seqs)-1, self.func_val+val))
        else:
            self.func_val = max(1, min(8, self.func_val+val)) # Max bars a seq can be
        return

    def init_sequence(self):
        self.sequencer.init_seq(self.seq_num, self.func_val)
        self.seqs[self.seq_num]['name'] = ''
        self.make_menu('main') # exit mode and set glbal seq num? | or seperate select func
        return

    def copy_sequence(self):
        self.sequencer.copy_seq(source_index=self.seq_num, dest_index=self.func_val)
        self.seqs[self.func_val]['name'] = str(self.seq_num) + "-copy"
        self.make_menu('main')
        return

    def del_sequence(self):
        self.sequencer.delete_seq(self.seq_num)
        self.seqs[self.seq_num]['name'] = "(unused)"
        self.seqs[self.seq_num]['swing'] = 0
        self.make_menu('main')
        return

    def exit_mode(self):
        self.dm.disk.config['seqs'] = self.seqs
        self.sequencer.seq_num = self.seq_num
        self.sequencer.change_seq(0)
        self.dm.change_mode("main")
        return

# EOF
