import wave

import pygame
from pygame.locals import *

def write_wave(path, audio):
    # Convert to (little-endian) 16 bit integers.
    audio = audio.astype("<h")

    with wave.open(str(path), "w") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(audio.tobytes())
    return

class WaveEditor:
    def __init__(self, lcd, snd_array):
        self.edit_lines = [] #chop_lines
        self.start = 0
        self.end = None
        self.rect = pygame.Rect(0,0,14,15)
        self.rects = []

        self.snd_array = snd_array

        # Get LCD parameters and make sub-surface
        self.lcd = lcd
        width = lcd.WIDTH
        height = lcd.HEIGHT - 3*lcd.font.height
        self.height = height
        
        # Base Body subsurface | maybe just specify body_x, body_y
        self.wav_surface = pygame.Surface((width, height))
        self.wav_surface.fill(lcd.g2)

        # the main wave surface (we draw once, save and reblit)
        self.wavform = pygame.Surface((width, height))
        self.wavform.fill(lcd.g2) #wav_surface2

        self.make_waveform()

    def remake_waveform(self):
        self.wavform.fill(self.lcd.g2)
        self.make_waveform()
        return

    def make_waveform(self):
        lcd = self.lcd
        y = self.snd_array[:,0].copy() # one channel only (left/right)
        length = len(y) # how many samples

        # Pixels per Sample | get ratio of screen size to number samples
        # Check/fix length == 0 | else display error
        if length != 0:
            scale_factor = lcd.WIDTH/length

            # Set x postion based on scale factor
            self.x = [int((i+1)*scale_factor) for i in range(length)]

            '''This part is tricky, need to fit the wave form inside the LCD area'''
            ratio = ((2**15)-1000) / max(abs(y)) # Normalize Ratio
            ys = y * ratio # Scale y to full scale
            
            # Add the max (all y values positive), renormalize, then scale
            ys = (ys + (2**15)) / ((2**15) * 2) * self.height
            y2 = ys.astype(int) # convert to int for rendering

            self.coords = list(zip(self.x, y2)) # Make (x,y) coords
            pygame.draw.lines(self.wavform, (0,0,0), False, self.coords, 1) # Draw wavform
        else:
            self.x = [0]
        return

    def draw_editor(self, idx):
        self.wav_surface.fill(self.lcd.g2)
        self.wav_surface.blit(self.wavform, (0,0))

        if len(self.edit_lines) == 0:
            return

        i = 0
        for line, rect in zip(self.edit_lines, self.rects):
            color = (255,0,0)
            if i == idx:
                color = (0,92,230)
            # White, Black, or yellowish orange
            pygame.draw.line(self.wav_surface, (255,255,255), line[0], line[1], width = 1)
            pygame.draw.rect(self.wav_surface, (0,0,0), rect)
            pygame.draw.rect(self.wav_surface, color, rect, width = 2)
            i += 1
        return


class Chopper(WaveEditor):
    def __init__(self, lcd, snd_array):
        super().__init__(lcd, snd_array)
        self.make_snd =  pygame.sndarray.make_sound
        self.chop_play = {K_a: self.make_snd(self.snd_array[0:, :])}

    # --------------------------------------------------------------------------
    def make_slice(self):
        pos = pygame.mouse.get_pos()[0]-self.lcd.offset #100 # Adjust for offset
        percent = pos/self.lcd.WIDTH
        end = int(percent*len(self.x))

        if len(self.edit_lines) < 7:
            self.edit_lines.append([(pos, self.lcd.HEIGHT), (pos, 0)])
            self.edit_lines.sort()

            self.update_slices()

            self.rects = []
            for line in self.edit_lines:
                rect = self.rect.copy()
                rect.centerx = line[0][0]
                self.rects.append(rect)

        self.rects.sort()
        return

    def update_slices(self):
        slice_x = [0]
        for line in self.edit_lines:
            x = line[0][0]
            percent = x/self.lcd.WIDTH
            slice_x.append(int(percent*len(self.x)))

        self.make_chops(slice_x)
        self.rects.sort()
        self.edit_lines.sort()

        return
    
    # --------------------------------------------------------------------------
    def make_chops(self, slices):
        chops = [None for i in range(len(slices))]
        slices.sort()
        if len(slices) > 1:
            for idx, val in enumerate(slices):
                if idx == 0:
                    chops[idx] = [0, slices[idx+1]]
                elif idx == len(slices)-1:
                    chops[idx] = [val, len(self.x)]
                else:
                    chops[idx] = [val, slices[idx+1]]
        else:
            chops[0] = (0, len(self.x))

        for chop in chops: #start cannot equal end
            if chop[0] == chop[1]:
                chop[1] += 10 # Increase? Also fix "flags" can go off screen

        pad_keys = [K_a, K_s, K_d, K_f, K_g, K_h, K_j, K_k] # From import PAD_KEYS
        sounds = [self.make_snd(self.snd_array[start:end, :]) for start, end in chops]

        self.endpoints = {i:(vals[0], vals[1]) for i, vals in enumerate(chops)}
        self.chop_play = {pad_keys[i]: val for i, val in enumerate(sounds)}

    def play_slice(self, event, snd_engine):
        chop = self.chop_play.get(event.key, False)
        if chop:
            snd_engine.mixer.Channel(0).play(chop)

        return

# ==========================================================================
class Truncator(WaveEditor):
    def __init__(self, lcd, snd_array):
        super().__init__(lcd, snd_array)
        self.make_snd =  pygame.sndarray.make_sound
        self.init_endpoints()
    
    def init_endpoints(self):
        self.edit_lines = []
        self.end = self.x[-1]
        self.start = 0
        # Comment all this | end lines not needed?
        self.edit_lines.append([(self.start, self.lcd.HEIGHT), (self.start, 0)])
        self.edit_lines.append([(self.end, self.lcd.HEIGHT), (self.end, 0)])
        self.update_endpoints()

    def update_endpoints(self):
        self.rects = []
        for idx, line in enumerate(self.edit_lines):
            x = line[0][0]
            percent = x/self.lcd.WIDTH

            rect = self.rect.copy()
            rect.centerx = line[0][0]
            self.rects.append(rect)

            loc = int(percent*len(self.x))
            if idx == 0:
                self.start = loc #line[0][0]
            else:
                self.end = loc #line[0][0]

        return

    def play_slice(self, event, snd_engine):
        chop = self.make_snd(self.snd_array[self.start:self.end, :])
        snd_engine.mixer.Channel(0).play(chop)
# EOF
