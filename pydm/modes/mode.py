import time

import pygame
from pygame.locals import *


class Default:
    def execute(self, mode):
        pass

class Command:
    '''Command acts like a callback (more or less)
    It is an object to store a function, which is letter executed
    '''
    def __init__(self, target=None, method=None, arg=None):
        self.target = target  # target is a attribute/method
        self.method = method  # Method to invoke from target
        self.arg = arg  # Arg to pass to the Targets Method

    def execute(self, mode):
        if self.target is not None:
            invoker = getattr(mode, self.target)
        else:
            invoker = mode
        self.command = getattr(invoker, self.method)

        if self.arg is not None:
            if type(self.arg) is list:
                self.command(*self.arg)
            else:
                self.command(self.arg)
        else:
            self.command()

# ==============================================================================
# ------ Key Maps
kb_key_map = {
    K_EQUALS: 'BPM_plus', #"plus",
    K_MINUS: 'BPM_minus', #minus",
    K_0: "AC_plus",
    K_9: "AC_minus",
    K_LEFTBRACKET: "SEQ_minus",
    K_RIGHTBRACKET: "SEQ_plus",
    K_o: "record",
    K_m: "MET_minus", # met_toggle
    K_p: "play" ,
    K_SPACE: "play",
    K_BACKQUOTE: 'mixer_toggle',
    K_BACKSPACE: "delete", #K_BACKSPACE / K_L
    K_TAB: "bank_toggle",
    K_q: "softkey_1",
    K_w: "softkey_2",
    K_e: "softkey_3",
    K_r: "softkey_4",
    K_t: "softkey_5",
    K_y: "softkey_6",
    K_LEFT: "page-",
    K_RIGHT: "page+",
    K_UP: "idx-",
    K_DOWN: "idx+",
}

# ------ LCD Cursor commands
cursor_cmds = {
    "page-": Command('lcd', 'change_idx_col', -1),
    "page+": Command('lcd', 'change_idx_col', 1),
    "idx-": Command('lcd', 'change_idx_row', -1),
    "idx+": Command('lcd', 'change_idx_row', 1)
}

# ------ LCD ------ #
confirm_footer = ["<NO>", "<YES>"]
use_name_footer = ["<EXIT>", "<CONFIRM>"]
typing_footer = ["Typing..."]


# ==============================================================================
class Mode:
    '''Base Class all modes inherit fromand override'''
    pad_keys = [K_a, K_s, K_d, K_f, K_g, K_h, K_j, K_k]
    chan_keys = [
        K_1, K_2, K_3, K_4, K_5 , K_6, K_7, K_8,
        K_KP1, K_KP2, K_KP3, K_KP4, K_KP5, K_KP6, K_KP7, K_KP8
    ]
    def __init__(self, dm):
        self.dm = dm
        # Init System Modules
        self.sequencer = dm.sequencer
        self.snd_engine = dm.snd_engine
        self.disk = dm.disk
        self.lcd = dm.lcd
        self.panel = dm.panel

        # key mapping and commands
        self.key_map = kb_key_map
        self.commands = {}
        self.menu = None
        self.typer = None
        self.lcd.cursor_idx = 0

    def msg_popup(self, msg="Loading...", error=False):
        '''Helper to create pop up messages with option to sleep in order for
        user to see the message
        '''
        self.lcd.msg_surf.fill(self.lcd.g2)
        pygame.draw.rect(self.lcd.msg_surf, (0,0,0), (0,0,350,100), 5)

        dialog_text, dialog_rect = self.lcd.make_text((0, 0), msg, (0,0,0), menu=False)
        dialog_rect.center = (350//2, 100/2) # Get rect h/w, so not hard coded

        self.lcd.msg_surf.blits([[dialog_text, dialog_rect]])
        self.lcd.overlay.blit(self.lcd.msg_surf, self.lcd.msg_rect)

        self.lcd.DISPLAY.blit(self.lcd.overlay, (0,0))
        self.dm.screen.blit(self.lcd.DISPLAY, self.lcd.blitloc)
        pygame.display.flip()

        if error:
            time.sleep(2)
        else:
            time.sleep(0.33)

        return

    def typer_update(self, texta="", textb="", name_type="File", check=None, check_text='', prompt=False):
        """Updates displayed text when user is prompted to type sound, song, and other names
        
        Parameters
        ----------
        texta : str
            The first line of text to display if prompt is True.
        textb : str
            The second line of text to display if prompt is True (optional).
        name_type : str
            Arg used in text to display what is being typed. Sound name, Disk name, song name etc.
        check : list
            If supplied, the typed text is checked aginst this list to prevent duplciate names 
        check_text : str
            Concated to check arg (another layer to check for duplicate names)
        prompt : bool
            Indicates if we are simply diplsaying text version typing and checking
        
        Returns
        -------
        to_blit : list
            List of lists holding a surface/rect and corrdinates
        header_line : bool
            Indicates if the horizontal header line should be rendered (always False)
        """
        lcd = self.lcd
        no_confirm = False

        if prompt:
            text1 = texta
            text2 = textb
        else:
            text1 = f"Enter {name_type} Name (Press Return to toggle typing):"
            self.typer.check_blink()
            text2 = self.typer.text_to_render
            no_confirm = True

            if len(text2) > 0 and self.typer.active == False:
                if check is not None:
                    name = text2 + check_text
                    if name in check:
                        text1 = f'{name_type} name exists, re-enter (Press Return to change)'
                        no_confirm = True
                    else:
                        text1 = f"Confirm {name_type} Name? (Press Return to change):"
                        no_confirm = False
                else:
                    text1 = f"Confirm {name_type} Name? (Press Return to change):"
                    no_confirm = False

        dialog1 = lcd.make_text(lcd.typer_lines[0], text1, (0,0,0), menu=True)
        dialog2 = lcd.make_text(lcd.typer_lines[1], text2, (0,0,0), menu=True)

        to_blit = [lcd.menu, [dialog1], [dialog2]]
        if no_confirm:
            to_blit = [[lcd.menu[0]], [dialog1], [dialog2]]

        header_line = False
        return to_blit, header_line

    # --------------------------------------------------------------------------
    def handle_input(self, event):
        """Get Action from event, if action -> execute mapped command"""
        action = self.key_map.get(event.key, False)
        if action:
            command = self.commands.get(action, Default())
            command.execute(self)

    def make_menu(self, menu):
        '''This method need to be overridden in sub-class: Builds LCD menu'''
        pass

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

    def update(self):
        '''This method need to be overridden in sub-class: handle update logic'''
        pass

# EOF
