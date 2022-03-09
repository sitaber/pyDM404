# -----------------------------------------------------------------------------
# pyDM404 - A cross platform Drum Sequencer
# Author: Scott Taber
# File: app.py - Nuts and bolts of application
#
# Contains all functions and classes for drawing to screen, getting user input
# loading and saving files, starting and stoping clock process, etc.
# -----------------------------------------------------------------------------

import os
import sys
import json

import numpy as np
import pygame
from pygame.locals import *

import clock as mc

# RECT func ------------------------------------------------------------ #
# Functions for creating the pygame Rect objects used for the buttons and other screen elements

def make_func_rects(start=95):
    button_1 = pygame.Rect(start+15, 170, 50, 10)
    button_2 = pygame.Rect(start+125,170, 50, 10)
    button_3 = pygame.Rect(start+245, 170, 50, 10)
    button_4 = pygame.Rect(start+360,170, 50, 10)
    return [button_1, button_2, button_3, button_4]

def make_text_rect(text, font, color, x, y):
    textobj = font.render(text, 1, color)
    textrect = textobj.get_rect()
    textrect.topleft = (x, y)
    return [textobj, textrect]
    
def make_playrec_rects(start, font, screen):
    text_rects = []
    
    button_play = pygame.Rect(start+490,100,20,20)
    led_play = pygame.draw.circle(screen, (255,255,255), (start+480+20,140-10), 5) 

    rects = make_text_rect("PLAY", font, (255, 255, 255), start+485,140)
    text_rects.append(rects)

    button_record = pygame.Rect(start+530,100,20,20)
    led_record = pygame.draw.circle(screen, (255, 255, 255), (start+530+10,140-10), 5)
    
    rects = make_text_rect("REC", font, (255,255,255), start+530,140)
    text_rects.append(rects)
    
    return [button_play, led_play, button_record, led_record], text_rects
    
def make_control_rects(start, font):
    buttons_down = []
    buttons_up = []
    text_rects = []
    buttons_text1 = []
    buttons_text2 = []
    for i, t in enumerate(["SEQ","BPM","AC","MET"]):
        button_down = pygame.Rect(start+520,12+14*i, 10, 10)
        button_up   = pygame.Rect(start+550,12+14*i, 10, 10)
        buttons_down.append(button_down)
        buttons_up.append(button_up)
        
        rects = make_text_rect(t, font, (255, 255, 255), start+480, 10+14*i)
        text_rects.append(rects)
        if t == "MET":
            rects = make_text_rect("OFF", font, (255, 255, 255), start+515,10+18*i)
            buttons_text1.append(rects)
            
            rects = make_text_rect("ON", font, (255, 255, 255), start+548, 10+18*i)
            buttons_text2.append(rects)
        else:
            rects = make_text_rect("-", font, (0, 0, 0), start+522, 10+14*i)
            buttons_text1.append(rects)
            
            rects = make_text_rect("+", font, (0, 0, 0), start+551, 10+14*i)
            buttons_text2.append(rects) 
    
    return  buttons_down, buttons_up, text_rects, buttons_text1, buttons_text2       


        
# Sequencer Class -------------------------------------------------------  #
class Sequencer():
    auto_cor = ["4","8","16", "16t", "HI-REZ"]
    note_ppq = [np.array([0,24]), 
                np.array([0,12,24]), 
                np.array([0,6,12,18,24]),
                np.array([0,4,8,12,16,20,24]), 
                np.array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
                          21,22,23,24]) ]
    __transport__ = ['pulse', 'beat', 'bar', 'playing']
    
    recording = False
    delete_flag = False
    bpm = 90
    seq_num = 0
    tc = 0
    met_on = True
    
    def __init__(self, send_conn):
        self.send_conn = send_conn
        self.clock = None
        #self.midi_ports = pygame.midi.get_default_output_id()
        #self.midi_output = pygame.midi.Output(pygame.midi.get_default_output_id())
        self.state = 0
        for val in self.__transport__:
            setattr(self, val, 0)
        self.sequences = [self.make_seq() for i in range(8)]
        self.current_seq = self.sequences[self.seq_num]
        # Need two sequences, one for recording and one for play back
        self.seq_record = self.current_seq[0]
        self.seq_play = self.current_seq[1]
    
    def toggle(self):
        if self.state == 0:
            self.play()
        elif self.state == 1:
            self.stop() 
    
    def set_bpm(self):
        if self.clock:
            self.clock.shared_bpm.value = self.bpm
                    
    def play(self):
        self.state = 1
        self.clock = mc.ClockGen()
        self.clock.shared_bpm.value = self.bpm
        self.clock.launch_process(self.send_conn) # Explain how this works. 

    def stop(self):
        for val in self.__transport__:
            setattr(self, val, 0)
        self.state = 0
        self.clock.end_process() 
        self.copy()
    
    def step_end(self): 
        # Call At end of main function ------------------------------------- #
        self.pulse += 1
        if self.pulse == self.seq_play.shape[1]:
            self.pulse = 0
        if self.pulse % 24 == 0:
            self.beat += 1
        if self.beat == 4:
            self.beat = 0
            self.bar += 1
        if self.bar == self.seq_play.shape[1]//96:
            self.bar = 0 
            self.copy()

    def change_seq(self, up):
        if up == True:
            self.seq_num += 1
            if self.seq_num == 8:
                self.seq_num = 7
        if up == False:
            self.seq_num -= 1 
            if self.seq_num < 0:
                self.seq_num = 0
        if up is None:
            self.seq_num = 0
        self.current_seq = self.sequences[self.seq_num]
        self.seq_record = self.current_seq[0]
        self.seq_play = self.current_seq[1]
                        
    def make_seq(self, length = 2 ):
        seq_record = np.zeros((8, 24*4*length), dtype='i,i') # makes 8xN array of tuples [(0,0),(0,0),...
        seq_play   = np.zeros((8, 24*4*length), dtype='i,i')
        return [seq_record, seq_play]
     
    def ekey_to_idx(self, ekey):
        pad_keys = [K_a,K_s,K_d,K_f,K_g,K_h,K_j,K_k]
        pad_idx = pad_keys.index(ekey)  
        return pad_idx
        
    def record(self, ekey, pads):
        pad = self.ekey_to_idx(ekey)
        tick = self.auto_correct()
        self.seq_record[pad, tick][0] = 1
        # Here is the pitch setting, just need to add something for velocity
        self.seq_record[pad, tick][1] = pads[pad].pitch 
  
    def delete(self, ekey, whole = False):
        pad = self.ekey_to_idx(ekey)
        self.seq_record[pad, self.pulse] = 0
        if whole:
            self.seq_record[pad, :] = 0
    
    def copy(self):
        self.seq_play = self.seq_record.copy()     
    
    def to_play(self, ekey):
        pad = self.ekey_to_idx(ekey)
        val   = self.seq_play[pad, self.pulse][0] 
        pitch = self.seq_play[pad, self.pulse][1] 
        return val, pitch
    
    # AUTOCORRECT FUNCTION  -------------------------------------   ###########
    def auto_correct(self):
        scaled_ac = self.note_ppq[self.tc] + 24*self.beat+96*self.bar
        correct_to_idx = np.argmin( np.abs(self.pulse-scaled_ac) ) 
        correct_to = scaled_ac[correct_to_idx]
        if correct_to == self.seq_play.shape[1]:
            correct_to = 0
        return correct_to

    # STEP SEQ ---------------------------------------------------------     #
    def step_edit(self, chan, pulse, record, pads):
        if record:
            self.seq_record[chan, pulse][0] = 1
            self.seq_record[chan, pulse][1] = pads[chan].pitch
        if not record:
            self.seq_record[chan, pulse][0] = 0
        self.copy()
        
        return
# Setup -------------------------------------------------- #        
def build_chan():
    BASE = pygame.Surface((40,210)) 
    notch_y = [200-(y*8) for y in range(0,25)]
    for y in notch_y:
        pygame.draw.line(BASE, (80,80,80), (0, y), (5,y), 2)
    pygame.draw.line(BASE, (255,255,255), (19,0), (19,210), 1)
    return BASE

# LOAD functions ------------------------------------------------------- #
def load_disk(path, pads, snd_files):
    sounds = [load_snd(x, path) for x in snd_files]
    pads = load_config(path, pads, snd_files, sounds)
    seqs = load_seq(path)
    return pads, sounds, seqs
      
def load_config(path, pads, snd_files, sounds):
    attrs = ["sound_file","pitch","channel_out","volume"]
    
    with open(path[:-8]+'config.json', 'r') as f:
        params = json.load(f) 
    
    for i,pad in enumerate(pads):
        for attr in attrs:
            setattr(pad, attr, params[i][attr])
        snd_file = getattr(pad,"sound_file")
        if snd_file is not None:
            idx = snd_files.index(snd_file)
            pad.sound = sounds[idx]
        else: pad.sound = None
    return pads         
          
def load_snd(to_load, path):
    snd = pygame.mixer.Sound(path+to_load)
    snd_array = pygame.sndarray.array(snd)
    return pitch_it(snd_array)

def pitch_it(data):
    pitch_snd = []
    for n in np.arange(1,13): 
        idx = np.arange(0, data.shape[0] * 2**(n/12) ) * 2**(-n/12)
        idx_floor = np.floor(idx).astype("int")
        new_data = data[ idx_floor[idx_floor < data.shape[0]] ]
        pitch_snd.append( pygame.sndarray.make_sound(new_data) )
    
    pitch_snd.reverse()
    pitch_snd.append(pygame.sndarray.make_sound(data))
    for n in np.arange(1,13): 
        idx = np.arange(0, data.shape[0]) * 2**(n/12)
        idx_floor = np.floor(idx).astype("int")
        new_data = data[ idx_floor[ idx_floor < data.shape[0] ] ]
        pitch_snd.append( pygame.sndarray.make_sound(new_data) )  
    
    return pitch_snd  

def load_seq(path):
    #path = DISKS/{disk}/
    seqs = []
    for i in range(8):
        temp = np.load(path[:-8]+f"seq0{i}.npy")
        seqs.append([temp.copy(), temp.copy()])   
    return seqs 

# SAVE functions ------------------------------------------------------ #
def save_disk(path, pads, seqs):
    config = make_config(pads)
    save_config(path, config)
    save_seq(path, seqs)
    
def make_config(pads):
    params = {"sound_file": None, "pitch": 12, "channel_out": 1, "volume": 1.0}
    attrs = ["sound_file", "pitch", "channel_out", "volume"]
    configs = []
    for pad in pads:
        for attr in attrs:
            params[attr] = getattr(pad,attr)
        configs.append(params.copy())
    return configs
        
def save_config(path, config):
    with open(path+'config.json', 'w') as f:
        json.dump(config, f)

def save_seq(path, seqs):
    #path = DISKS/{disk}/
    #print(len(seqs))
    for i in range(8):
        to_save = seqs[i][0]
        np.save(path+f"seq0{i}.npy", to_save)    

# PAD class ----------------------------------------------------------- #           
class Pad():
    def __init__(self, mixer):
        self.sound_file = None
        self.sound = None
        self.pitch = 12
        self.channel_out = 1
        self.volume = 24
        self.mixer = mixer

# Main Class ----------------------------------------------------------  #
class DrumMachine():
    FLAGS = 0
    WIDTH = 800
    HEIGHT = 600
    FPS = 30
    WHITE = (255,255,255)
    GREY = (80,80,80)
    RED = (255,0,0)
    GREEN = (0,255,0)
    
    def __init__(self,receive_conn, send_conn):
        # Pygame inits ------- #
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        #pygame.midi.init()
        pygame.font.init()
        #self.midi_in = pygame.midi.Input(1) 
        self.receive_conn = receive_conn
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), self.FLAGS)
        self.mainClock = pygame.time.Clock()
        pygame.display.set_caption("pyDM404")
        self.font = pygame.font.Font('assets/Kenney Future Narrow.ttf', 12)#pygame.font.SysFont(None, 20)#
        
        # Class vars ---------- #
        self.sequencer = Sequencer(send_conn)
        self.mixer_chan = build_chan()
        self.DISPLAY = pygame.Surface((460,165)) 
        self.knob_notch_locs = [200-(y*8) for y in range(0,25)]
        self.pads = [Pad(self.mixer_chan) for i in range(8)]
        self.knobs = [] 
        self.snd_files = []
        self.sounds = []
        self.met = pygame.mixer.Sound('assets/metronome.wav')
        self.met.set_volume(0.4) 
        self.fill_rect =[]
        self.step_rect = []
        self.step_rect2 = []
        self.fill_rect2 = []
        
    def play(self,ekey, pitch = None):
        pad_keys = [K_a,K_s,K_d,K_f,K_g,K_h,K_j,K_k]
        pad_idx = pad_keys.index(ekey)
        if self.pads[pad_idx].sound is not None:
            if pitch is not None:
                pitch = pitch
            else:
                pitch = self.pads[pad_idx].pitch
            to_play = self.pads[pad_idx].sound[pitch]
            chan = self.pads[pad_idx].channel_out
            to_play.set_volume(0.04*self.pads[pad_idx].volume)
            pygame.mixer.Channel(chan).play(to_play)
        
    def draw_mixer(self,volume):
        start = 95 #0
        sub_mixer = pygame.Surface((40,210)) 
        MIXER = pygame.Surface((460,210)) 
        self.knobs = [] 
        for x in range(8):
            if volume:
                level = self.pads[x].volume
            else: 
                level = self.pads[x].pitch
            knob = pygame.Rect( (start+x*60, self.knob_notch_locs[level]-3+260, 40, 8) )
            self.knobs.append(knob)
            self.screen.blit(self.pads[x].mixer, (start+x*60,260))
            pygame.draw.rect(self.screen, (255,255,255), knob, 0) 
            
    def draw_text(self,text, font, color, surface, x, y):
        textobj = font.render(text, 1, color)
        textrect = textobj.get_rect()
        textrect.topleft = (x, y)
        surface.blit(textobj, textrect)

    def _draw_main(self, display_step):
        self.DISPLAY.fill((0,255,0)) 
        seq = self.sequencer.seq_num
        bpm = self.sequencer.bpm
        c = [self.sequencer.bar+1,self.sequencer.beat+1,self.sequencer.pulse]
        c[2] = self.sequencer.pulse - 24 * self.sequencer.beat - 96 * self.sequencer.bar
        ac = self.sequencer.auto_cor[self.sequencer.tc]
        DISPLAY_TEXT = [f"SEQ: 0{seq}",f"BPM: {bpm}", f"COUNT: 0{c[0]}.0{c[1]}.{c[2]}", f"AC: {ac}"]
        
        for i in [0,2]:
            t = self.font.render(DISPLAY_TEXT[i], True, (0, 0, 0))
            self.DISPLAY.blit(t, (5,10+i*10)) 
            t = self.font.render(DISPLAY_TEXT[i+1], True, (0, 0, 0))
            self.DISPLAY.blit(t, (320,10+i*10)) 
        
        if display_step:
            lower_menu = ["<EXIT>", "<BAR->", "<BAR+>", "<>"]
        else:
            lower_menu = ["<LOAD>", "<ASSN SND>", "<STEPEDIT>", "<SAVE>"]
        for x, b in enumerate(lower_menu):
            func_text = self.font.render(b, True, (0,0,0))
            self.DISPLAY.blit(func_text, (15+115*x,150)) 
        
        self.screen.blit(self.DISPLAY, (95,0))
        return
    
    # DRAW STEP -------------------------------------------------- #
    def draw_step(self, step_bar_val):
        #STEPDISPLAY = pygame.Surface((460,165)) 
        y1 = 75
        y2 = 145
        
        if self.sequencer.pulse < 96 and step_bar_val == 0:
            x1 = 30+self.sequencer.pulse*4
            pygame.draw.lines(self.DISPLAY, self.RED, False, [(x1,y1),(x1,y2)])
        elif self.sequencer.pulse > 96 and step_bar_val == 1:
            x1 = 30+(self.sequencer.pulse-96)*4
            pygame.draw.lines(self.DISPLAY, self.RED, False, [(x1,y1),(x1,y2)])
            
        for rect in self.fill_rect:
            pygame.draw.rect(self.DISPLAY, self.RED, rect)
            pygame.draw.rect(self.DISPLAY, self.GREEN, rect, width=1)
        for rect in self.step_rect:
            pygame.draw.rect(self.DISPLAY, self.WHITE, rect, width=1)
            
        func_text = self.font.render("0"+str(step_bar_val+1)+".", True, (0,0,0))
        self.DISPLAY.blit(func_text, (0,53)) 
        for i, pad_alpha in enumerate(['A','S','D','F','G','H','J','K']):
            self.draw_text(pad_alpha, self.font, (0, 0, 0), self.DISPLAY, 20, 63+10*i)
                
        for x, b in enumerate(["1", "2", "3", "4"]):
            func_text = self.font.render(b, True, (0,0,0))
            self.DISPLAY.blit(func_text, (26+(384/4)*x,53)) 
        
        for x, b in enumerate(["|", "|", "|", "|"]):
            func_text = self.font.render(b, True, (0,0,0))
            self.DISPLAY.blit(func_text, (76+(384/4)*x,53)) 
            
        self.screen.blit(self.DISPLAY, (95,0))
        return
    
    def make_step_rects(self, step_bar_val):
        bar = step_bar_val
        self.step_rect = []
        self.fill_rect = []
        self.step_rect2 = []
        self.fill_rect2 = []
        steps = [4,8,16,24,32]
        length = steps[self.sequencer.tc]
        for i in range(8):
            for j in range(length):
                self.step_rect.append(pygame.Rect(30+(384/length)*j,65+10*i, 384/length, 10))
                self.step_rect2.append(pygame.Rect(95+30+(384/length)*j,65+10*i, 384/length, 10))
        for i in range(8):
            for j in range(96*bar,96*(bar+1)): #range(self.sequencer.seq_play.shape[1]-1): # 
                val = self.sequencer.seq_record[i, j][0] 
                if val:
                    if bar == 0:
                        self.fill_rect.append(pygame.Rect(30+4*j, 65+10*i, 384/32, 10))
                        self.fill_rect2.append(pygame.Rect(95+30+4*j, 65+10*i, 384/32, 10))
                    elif bar == 1:
                        self.fill_rect.append(pygame.Rect(30+4*(j-96), 65+10*i, 384/32, 10))
                        self.fill_rect2.append(pygame.Rect(95+30+4*(j-96), 65+10*i, 384/32, 10))
        # save fill_rect to self ==> mouse_pos_collide => if true remove fill and record
        
    # MAIN LOOP ----------------------------------------------------------- # 
    def main_loop(self):
        click = False
        drag = False
        pad_keys = [K_a,K_s,K_d,K_f,K_g,K_h,K_j,K_k]
        step = False
        display_step = False
        step_bar_val = 0
        volume = True
        start = 95
        func_rects = make_func_rects(start = 95)
        playrec_rects, playrec_text = make_playrec_rects(95, self.font, self.screen)
        buttons_down, buttons_up, text_rects, buttons_text1, buttons_text2 = make_control_rects(95, self.font)
        mix_tune_rect = pygame.Rect((8,348,20,20))
        while True:
            self.screen.fill((0,0,0))
            
            mx, my = pygame.mouse.get_pos()
            mouse_rect = pygame.Rect((mx,my),(1,1))          
            # STEP SEQ boxes ----------------------------------------------- #
            select_idx2 = mouse_rect.collidelistall(self.step_rect2) 
            if select_idx2 and click and self.sequencer.recording:
                idx = select_idx2[0]
                rect_clicked = self.step_rect[idx]
                rx,ry = rect_clicked.topleft
                r_chan = int((ry - 65)/ 10)
                r_pulse = int( ((rx - 30)/4)+96*step_bar_val)
                self.sequencer.step_edit(r_chan, r_pulse, True, self.pads)  
            
            select_idx = mouse_rect.collidelistall(self.fill_rect2)
            if select_idx and click:
                idx = select_idx[0]
                rect_clicked = self.fill_rect[idx]
                rx,ry = rect_clicked.topleft
                r_chan = int((ry - 65)/ 10)
                r_pulse = int( ((rx - 30)/4)+96*step_bar_val)
                self.fill_rect.pop(idx)
                self.sequencer.step_edit(r_chan, r_pulse, False, self.pads)   
            # ----------------- left, top, width, height ----------------- #
            button_1 = pygame.Rect(start+15, 170, 50, 10)
            button_2 = pygame.Rect(start+125,170, 50, 10)
            button_3 = pygame.Rect(start+245, 170, 50, 10)
            button_4 = pygame.Rect(start+360,170, 50, 10)
            
            if button_1.collidepoint((mx, my)):
                if click and not display_step:
                    self.load_menu()
                elif click and display_step:
                    display_step = not display_step
            
            if button_2.collidepoint((mx, my)):
                if click and not display_step:
                    self.assn_menu()
                elif click and display_step:
                    step_bar_val = 0
            
            if button_3.collidepoint((mx, my)):
                if click and not display_step:
                    display_step = True
                elif click and display_step: 
                    step_bar_val = 1
            
            if button_4.collidepoint((mx, my)):
                if click and not display_step:
                    self.load_menu(load=False)
                              
            for i,knob in enumerate(self.knobs):
                if knob.collidepoint((mx,my)):
                    if click:
                        drag = True
                        knob_drag = knob
                        knob_idx = i
                        break
            
            for r in func_rects:
                pygame.draw.rect(self.screen, self.WHITE, r)            

            if mix_tune_rect.collidepoint((mx, my)):
                if click:
                    volume = not volume 
            
            select_down_idx = mouse_rect.collidelistall(buttons_down)
            if select_down_idx and click:
                idx = select_down_idx[0]
                if idx == 0:
                    self.sequencer.change_seq(False)   
                if idx == 1:
                    self.sequencer.bpm -= 0.5
                    self.sequencer.set_bpm()
                if idx == 2:
                    self.sequencer.tc -= 1
                    if self.sequencer.tc < 0:    
                        self.sequencer.tc = 0 
                if idx == 3:
                    self.sequencer.met_on = False
            
            select_up_idx = mouse_rect.collidelistall(buttons_up) 
            if select_up_idx and click:
                idx = select_up_idx[0]
                if idx == 0:
                    self.sequencer.change_seq(True)   
                if idx == 1:
                    self.sequencer.bpm += 0.5
                    self.sequencer.set_bpm()
                if idx == 2:
                    self.sequencer.tc += 1 
                    if self.sequencer.tc == 5:    
                        self.sequencer.tc = 4
                if idx == 3:
                    self.sequencer.met_on = True
                        
            select_playrec_idx = mouse_rect.collidelistall(playrec_rects) 
            if select_playrec_idx and click:
                idx = select_playrec_idx[0]
                if idx == 0:
                    self.sequencer.toggle()
                    step = False
                if idx == 2:
                    self.sequencer.recording = not self.sequencer.recording           
           
            # 1) Check midi for pulse =>Step Start => Play met----------- #
            if self.receive_conn.poll():
                _ignore = self.receive_conn.recv() 
                step = True
                if self.sequencer.pulse % 24 == 0 and self.sequencer.met_on and self.sequencer.state:
                    pygame.mixer.Channel(0).play(self.met)   
            # 2) Get sounds to play and play them --------------- #
                for pad in pad_keys:
                    val, pitch = self.sequencer.to_play(pad)
                    if val:
                        self.play(pad, pitch)
            # 3a) Check user inputs
            click = False
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == KEYUP: 
                    if event.key == K_l:
                        self.sequencer.delete_flag = False # Keyboard key L for delete
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == K_o:   
                        self.sequencer.recording = not self.sequencer.recording
                    if event.key == K_m:   
                        self.sequencer.met_on = not self.sequencer.met_on
                    if event.key == K_p:
                        self.sequencer.toggle()
                        step = False
                    if event.key == K_l:
                        self.sequencer.delete_flag = True
                    # PAD PLAY ---------------------------------------------- #
                    if event.key in pad_keys:
                        self.play(event.key)
                        # 3b) Record if applicable -------------------------  #
                        if self.sequencer.recording and self.sequencer.state and not self.sequencer.delete_flag:
                            self.sequencer.record(event.key, self.pads)
                    if event.key == K_EQUALS:
                        self.sequencer.bpm += 0.5
                        self.sequencer.set_bpm()
                    if event.key == K_MINUS:
                        self.sequencer.bpm -= 0.5
                        self.sequencer.set_bpm()
                    if event.key == K_0:
                        self.sequencer.tc += 1 
                        if self.sequencer.tc == 5:    
                            self.sequencer.tc = 4
                    if event.key == K_9:
                        self.sequencer.tc -= 1
                        if self.sequencer.tc < 0:    
                            self.sequencer.tc = 0                    
                    if event.key == K_LEFTBRACKET:
                        self.sequencer.change_seq(False)                        
                    if event.key == K_RIGHTBRACKET:
                        self.sequencer.change_seq(True)   
                    if event.key == K_i:      
                        volume = not volume              
                if event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        click = True
                if event.type == MOUSEBUTTONUP:
                    if event.button == 1 and drag:
                        drag = False
                if event.type == pygame.MOUSEMOTION:
                # Mixer knob drag --- make function -------------------------  #
                    if drag:
                        mouse_x, mouse_y = event.pos
                        knob_drag.y = mouse_y 
                        if (460-knob_drag.y)//8 <= 0:
                            new_loc = 0
                        elif (460-knob_drag.y)//8 >= 24:
                            new_loc = 24
                        else: new_loc = (460-knob_drag.y)//8
                        if volume:
                            self.pads[knob_idx].volume = new_loc
                        else:
                            self.pads[knob_idx].pitch = new_loc
                    
            # DELETE ---------------------------------------------  #
            if self.sequencer.delete_flag and self.sequencer.state: # Delete note as realtime plays over it
                pressed = pygame.key.get_pressed()
                for press in [97,115,100,102,103,104,106,107]:
                    if pressed[press]:
                        self.sequencer.delete(press)
            elif self.sequencer.delete_flag and not self.sequencer.state: # Deletes all notes if not running
                pressed = pygame.key.get_pressed()
                for press in [97,115,100,102,103,104,106,107]:
                    if pressed[press]:
                        self.sequencer.delete(press, whole=True)
                        self.sequencer.copy() 
            
            # 4) Step End - increment pulse,beat,bar, etc (after event loop) 
            if step:
                self.sequencer.step_end()  
                step = False  
            # DRAW STUFF ----------------------------------------------------- #        
            self._draw_main(display_step)
            self.draw_mixer(volume)
            if display_step:
                self.make_step_rects(step_bar_val)
                self.draw_step(step_bar_val)
            # DRAW CONTROLS ------------------------------------------------ #   
            pygame.draw.rect(self.screen, self.WHITE, playrec_rects[0])
            if self.sequencer.state:
                pygame.draw.rect(self.screen, self.RED, playrec_rects[1])
            else: pygame.draw.rect(self.screen, self.WHITE, playrec_rects[1])

            pygame.draw.rect(self.screen, self.RED, playrec_rects[2])
            if self.sequencer.recording:
                pygame.draw.rect(self.screen, self.RED, playrec_rects[3])
            else: pygame.draw.rect(self.screen, self.WHITE, playrec_rects[3])
            
            for r in playrec_text:
                self.screen.blit(r[0], r[1])  
            
            for r in buttons_down:
                pygame.draw.rect(self.screen, self.WHITE, r)
            if not self.sequencer.met_on:
                pygame.draw.rect(self.screen, self.RED, buttons_down[3])
            
            for r in buttons_up:
                pygame.draw.rect(self.screen, self.WHITE, r)
            if self.sequencer.met_on:
                pygame.draw.rect(self.screen, self.RED, buttons_up[3])    
            
            for r in text_rects:
                self.screen.blit(r[0], r[1])

            for r in buttons_text1:
                self.screen.blit(r[0], r[1])
                
            for r in buttons_text2:
                self.screen.blit(r[0], r[1])

            # MIX/TUNE ------------------------------------------------------ #
            pygame.draw.rect(self.screen, self.WHITE, mix_tune_rect,0)
            for i, t in enumerate(["MIX","TUNE"]):
                text_b = self.font.render(t, True, (255, 255, 255))
                self.screen.blit(text_b, (50,344+i*20))
                if i != volume:
                    color = self.RED
                else: color = self.WHITE
                pygame.draw.circle(self.screen, color, (41,349+i*20), 5)
            
            pygame.display.update()
            self.mainClock.tick(160)

    # LOAD/SAVE LOOP -------------------------------------------------------- # 
    def load_menu(self, load=True):
        running = True
        click = False
        DIR_CONTENTS = os.listdir("DISKS")
        #print(os.getcwd())
        DIR_CONTENTS.sort()
        #DIR_CONTENTS.remove("BLANK")
        selected = np.zeros((len(DIR_CONTENTS)), dtype=int)
        button_select = None
       
        while running:
            self.screen.fill((0,0,0))
            self.draw_text('DISKS', self.font, (255, 255, 255), self.screen, 20, 20)

            # Make Select Boxes and text ---------------------------------    #
            buttons = []
            for i,text in enumerate(DIR_CONTENTS):
                self.draw_text(text, self.font, (255, 255, 255), self.screen, 20, 60+20*i)
                button = pygame.Rect(5, 62+20*i, 10, 10)
                pygame.draw.rect(self.screen, (255, 0, 0), button)
                buttons.append(button)

            # Mouse pos and collision check ------------------------------    #
            mx, my = pygame.mouse.get_pos()    
            mouse_rect = pygame.Rect((mx,my),(1,1))          
            select_idx = mouse_rect.collidelistall(buttons)

            if select_idx and click:
                if selected[select_idx] == 0:
                    selected[select_idx] = 1
                    button_select = buttons[select_idx[0]] 
                else: 
                    selected[select_idx] = 0
                    button_select = None
            
            # Color Select Box WHITE if selected ----------------------- #      
            if button_select:
                pygame.draw.rect(self.screen, self.WHITE, button_select)            
            
            click = False      
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        running = False
                    if event.key == K_F1 and button_select:
                        #print(selected)
                        #print(np.nonzero(selected)[0][0])
                        DISK = DIR_CONTENTS[np.nonzero(selected)[0][0]]
                        if load:
                            snd_path = "DISKS/"+DISK+"/samples/"
                            snd_files = os.listdir(snd_path)
                            snd_files.sort()
                            self.snd_files = snd_files
                            self.pads, self.sounds,seqs = load_disk(snd_path, self.pads, snd_files)
                            self.sequencer.sequences = seqs
                            self.sequencer.change_seq(None)
                        if not load:
                            disk_path = "DISKS/"+DISK+"/"
                            #print(disk_path)
                            #print(self.sequencer.sequences)
                            save_disk(disk_path, self.pads, self.sequencer.sequences)
                        running = False     
                if event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        click = True
            pygame.display.update()
            self.mainClock.tick(60)       
             
    # ASSN LOOP ----------------------------------------------------------- # 
    def assn_menu(self):
        running = True
        click = False
        assn = False
        checked_rect = None
        snd_file_text = [None] + self.snd_files
        chan = 1
        num_keys = [K_1,K_2,K_3,K_4,K_5,K_6,K_7,K_8]
        
        while running:
            self.screen.fill((0,0,0))
            self.draw_text('PADS', self.font, (255, 255, 255), self.screen, 20, 20)
            self.draw_text('SOUNDS', self.font, (255, 255, 255), self.screen, 350, 20)

            # Sounds ------------------------------------------------------  #
            buttons = []
            for i,text in enumerate(snd_file_text):
                self.draw_text(text, self.font, (255, 255, 255), self.screen, 350, 60+20*i)
                button = pygame.Rect(335, 62+20*i, 10, 10)
                pygame.draw.rect(self.screen, (255, 0, 0), button)
                buttons.append(button)
           
            # Pads ---------------------------------------------------------- #
            buttons2 = []       
            for i, pad_alpha in enumerate(['A','S','D','F','G','H','J','K']):
                self.draw_text(pad_alpha, self.font, (255, 255, 255), self.screen, 20, 60+20*i)
                file_text = self.pads[i].sound_file
                if file_text is not None:
                    file_text = file_text[0:40]
                self.draw_text(file_text, self.font, (255, 255, 255), self.screen, 40, 60+20*i)
                button = pygame.Rect(5, 62+20*i, 10, 10)
                pygame.draw.rect(self.screen, (255, 0, 0), button)
                buttons2.append(button)
                self.draw_text(str(self.pads[i].channel_out), self.font, (255, 255, 255), 
                                                           self.screen, 30, 60+20*i)   
            # Mouse pos and collision check ------------------------------    #       
            mx, my = pygame.mouse.get_pos()    
            mouse_rect = pygame.Rect((mx,my),(1,1))  
            select_idx = mouse_rect.collidelistall(buttons2)
            
            if select_idx and click:
                assn = not assn
                pad_idx = select_idx[0]
                checked_rect = buttons2[select_idx[0]]
                chan = self.pads[pad_idx].channel_out
            
            if checked_rect and assn:
                pygame.draw.rect(self.screen, self.WHITE, checked_rect)
                self.pads[pad_idx].channel_out = chan # Set pad channel ------ #
            
            # Select Sound for pad ---------------------------------------    # 
            select_idx = mouse_rect.collidelistall(buttons)         
            if assn and select_idx and click:
                self.pads[pad_idx].sound_file = snd_file_text[select_idx[0]]
                if snd_file_text[select_idx[0]] is not None:
                    self.pads[pad_idx].sound = self.sounds[select_idx[0]-1]  
                else: self.pads[pad_idx].sound = None
                         
            click = False      
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        running = False
                    if event.key in num_keys:
                        chan = num_keys.index(event.key)+1
                if event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        click = True
            
            pygame.display.update()
            self.mainClock.tick(60)     
# MAIN ----------------------------------------------------------------------- #

