# -----------------------------------------------------------------------------
# pyDM404 - A cross platform Drum Sequencer
# -----------------------------------------------------------------------------

from pathlib import Path
import sys
import os
import shutil
import time

import pygame
from pygame.locals import *

from pydm.gui import LCD, Panel
from pydm.core import (
    Sequencer,
    SNDEngine,
    FloppyDisk
)
from pydm.modes import (
    Perform,
    Disk,
    Assign,
    Sounds,
    Seq,
    Song
)

# ==============================================================================
class DrumMachine:
    pad_keys = [K_a, K_s, K_d, K_f, K_g, K_h, K_j, K_k]
    chan_keys = [K_1, K_2, K_3, K_4, K_5 , K_6, K_7, K_8]

    def __init__(self, mixer, DIR, ClockGen):
        self.ROOT_DIR = DIR

        # ---- CORE
        self.sequencer = Sequencer(ClockGen)
        self.snd_engine = SNDEngine(mixer, self.ROOT_DIR)

        # ---- GUI
        self.lcd = LCD(DIR)
        self.panel = Panel(self.lcd, DIR)

        # ---- Load default settings
        self.disk = FloppyDisk(self.ROOT_DIR)

        self.snd_engine.load_sounds(self.disk.sound_dir)
        self.panel.make_pad_banks()
        self.panel.load_pad_config(self.disk, self.snd_engine)

        self.sequencer.sequences = self.disk.load_seqs()
        self.sequencer.load_config(self.disk.config)
        self.sequencer.set_seq()

        self.mode = Perform(self) # Set mode to Perform

    def change_mode(self, next_mode):
        playing = self.sequencer.state.playing
        
        if next_mode == 'main':
            self.mode = Perform(self)
        elif playing == False:
            self.sequencer.state.rec = False
            if next_mode == 'sounds':
                self.mode = Sounds(self)
            elif next_mode == 'disk':
                self.mode = Disk(self)
            elif next_mode == 'assign':
                self.mode = Assign(self)
            elif next_mode == 'seq':
                self.mode = Seq(self)
            elif next_mode == 'song':
                self.mode = Song(self)

    def render(self, screen):
        self.panel.render(screen, self.sequencer)
        # LCD outline "pop" effect
        pygame.draw.rect(screen, (22, 20, 21), (self.lcd.blitloc[0]-1, 0, self.lcd.WIDTH+1, 233) , 4)
        screen.blit(self.lcd.DISPLAY, self.lcd.blitloc)

# ==============================================================================
def run(ClockGen):
    # Check if running from bundled binary or source code
    # Set DIR to coorect location i.e. the Top level dir of the program based on location
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print('running in a PyInstaller bundle')
        print(f"Tmp location: {sys._MEIPASS}")
        print(f"exe dirname: {os.path.dirname(sys.executable)}")
        print(f"exe abs path {os.path.abspath(sys.executable)}")
        DIR = Path(sys.executable).parent
        #print(DIR)
    else:
        print('running in a normal Python process')
        print(f'wdir: {os.getcwd()}')
        print(f'file: {__file__}')
        print(f'root dir: {Path(__file__).parent.parent}')
        DIR = Path(__file__).parent.parent

    # GUI size variables
    WIDTH = 800
    HEIGHT = 600
    TEMP_DIR = DIR / "assets/temp"

    '''Pre init the mixer:44100 Hz, signed 16 bit int, 2 channels, 512 buffer'''
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()

    # set the total number of playback channels | chan 0 is for metronome
    pygame.mixer.set_num_channels(9)
    clock = pygame.time.Clock() # Init application clock for FPS control

    '''Init main screen | Resizable & Scaled for mouse position translation in full screen'''
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags=pygame.RESIZABLE | pygame.SCALED)

    '''Check that assests DIR exists and can be loaded'''
    asset_dir = DIR / "assets"
    
    if asset_dir.exists() is False: # Display msg, and exit
        load_font = pygame.font.Font(None, 30)
        font_height = load_font.get_height()
        load_text = load_font.render(
            "ERROR: assets DIR not found, please retrive from repo...",
            1,
            (255,255,255)
        )

        screen.blit(load_text, (10, font_height))
        pygame.display.flip()
        time.sleep(3) # Should sleep so we see error
        sys.exit() 
    else:
        # Load assets 
        icon = pygame.image.load(DIR / "assets/icon.png")
        pygame.display.set_icon(icon)
        pygame.display.set_caption("pyDM404")

        load_image = pygame.image.load(DIR / "assets/loading-splash.png")
        load_image = load_image.convert()
        load_image_rect = load_image.get_rect()
        
        screen.blit(load_image, (0,0))
        pygame.display.flip()

    disk_dir = DIR / 'DISKS'
    if disk_dir.exists() is False:
        disk_dir.mkdir() # make it

    if (TEMP_DIR / 'default').exists():
        print("old temp files found, removing...") # clean up (would exist if app crashed)
        shutil.rmtree(TEMP_DIR / 'default')

    '''Init DrumMachine | pygame.mixer must be passed as arg'''
    dm = DrumMachine(pygame.mixer, DIR, ClockGen)
    dm.screen = screen

    '''Application Loop: handle input -> update -> render'''
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                dm.mode.events(event)

        dm.mode.update()
        dm.render(screen)
        pygame.display.flip()
        clock.tick(160)

    # Shutdown and clean up | Check if clock is running and shut down/kill process if needed
    if dm.sequencer.clock is not None:
        dm.sequencer.check_clock()

    shutil.rmtree(TEMP_DIR / 'default') # remove temp files
    pygame.quit()
    return

# EoF
