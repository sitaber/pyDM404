from pathlib import Path
import json

import pygame.sndarray
import numpy as np

# ============================================================================
# -- Mapping dictionaries 
bank_map = {"A": 0, "B": 8, "C": 16, "D": 24}
ekey_map = {97: 0, 115: 1, 100: 2, 102: 3, 103: 4, 104: 5, 106: 6, 107: 7}

# Use mappings to build further mappings 
# "Scales" the ekey value based on current bank for use during playback
IDX_TOPAD = {}
for bank, bank_val in bank_map.items():
    for ek, val in ekey_map.items():
        IDX_TOPAD[bank_val+val] = (bank, ek)


def moog_filter(samples, sample_rate=44100, cutoff=250, resonance=0.1, drive=1.0):
    '''
    Copyright 2012 Stefano D'Angelo <zanga.mail@gmail.com>

    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.

    THIS SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
    '''
    
    VT = 0.312
    MOOG_PI = 3.14159265358979323846264338327950288
    x = (MOOG_PI * cutoff) / sample_rate
    g = 4.0 * MOOG_PI * VT * cutoff * (1.0 - x) / (1.0 + x)

    V = [0,0,0,0]
    dV = [0,0,0,0]
    tV = [0,0,0,0]

    dV0 = 0
    dV1 = 0
    dV2 = 0
    dV3 = 0

    VT2 = (2.0 * VT)
    SR2 = (2.0 * sample_rate)

    filtered_samples = []
    for sample in samples:
        x = (drive*sample + resonance*V[3]) / VT2

        dV0 = -g*(np.tanh(x) + tV[0])
        V[0] += (dV0 + dV[0]) / SR2
        dV[0] = dV0
        tV[0] = np.tanh(V[0] / VT2)

        dV1 = g*(tV[0] - tV[1])
        V[1] += (dV1 + dV[1]) / SR2
        dV[1] = dV1
        tV[1] = np.tanh(V[1] / VT2)

        dV2 = g*(tV[1] - tV[2])
        V[2] += (dV2 + dV[2]) / SR2
        dV[2] = dV2
        tV[2] = np.tanh(V[2] / VT2)

        dV3 = g*(tV[2] - tV[3])
        V[3] += (dV3 + dV[3]) / SR2
        dV[3] = dV3
        tV[3] = np.tanh(V[3] / VT2)

        filtered_samples.append(V[3])

    output = np.array(filtered_samples)
    y_out = np.int16(output * 2 ** 15) #should be 16? (no 16 is for unsigned)

    return y_out
    
class SNDEngine:
    def __init__(self, mixer, root_dir):
        self.mixer = mixer
        self.metup = mixer.Sound(root_dir / 'assets/MetronomeUp.wav')
        self.met = mixer.Sound(root_dir / 'assets/Metronome.wav')
        self.volume = 1
        self.root_dir = root_dir

    def load_sounds(self, sound_dir):
        self.sounds = {
            snd_path.name: {'path': snd_path, 'pitches': None}
            for snd_path in sound_dir.iterdir()
        }
        return

    def reload_sounds(self, sound_dir):
        for snd_path in sound_dir.iterdir():
            self.sounds[snd_path.name]['path'] = snd_path
        return

    def load_sound(self, snd_path):
        self.sounds[snd_path.name] = {'path': snd_path, 'pitches': None}
        return

    def set_pitches(self, sound_file):
        if sound_file != 'None':
            snd = self.sounds.get(sound_file, False)
            if snd:
                snd_path = snd['path']
                snd_array = pygame.sndarray.array(self.mixer.Sound(snd_path))
                self.sounds[sound_file]['pitches'] = self.pitch_it(snd_array)
                missing_snd =  False
            else:
                missing_snd = True

        return missing_snd

    def unset_pitches(self, name):
        # Used to unset/remove pitched sounds
        self.sounds[name]['pitches'] = None
        return

    def play_error(self):
        sound = self.mixer.Sound(self.root_dir / 'assets/error-beep.wav')
        sound.set_volume(0.1*self.volume)
        self.mixer.Channel(0).play(sound)
        return

    def play_met(self, beat):
        if beat == 0:
            self.metup.set_volume(0.4*self.volume)
            self.mixer.Channel(0).play(self.metup)
        else:
            self.met.set_volume(0.4*self.volume)
            self.mixer.Channel(0).play(self.met)
        return

    def sequncer_play(self, sequencer, pad_banks):
        # Loop over pads/'tracks' | 32 possible pads/'tracks'
        for idx in range(32):
            val, pitch = sequencer.seq_play[idx, sequencer.pulse]
            if val:
                bank, ekey = IDX_TOPAD.get(idx)
                pad = pad_banks[bank][ekey]
                self.play_sound(pad, pitch)
        return

    def play_sound(self, pad, pitch=None):
        if pad.sound_file != "None":
            if pitch is None:
                sound = self.sounds[pad.sound_file]['pitches'][pad.pitch]
            else:
                sound = self.sounds[pad.sound_file]['pitches'][pitch]

            chan = pad.channel
            sound.set_volume(0.04*pad.volume*self.volume)
            self.mixer.Channel(chan).play(sound)
        return

    def preview(self, sound_file):
        '''Plays a sound in Assign Mode'''
        sound = self.sounds.get(sound_file, False) 
        if sound:
            sound_path = sound['path']
            sound = self.mixer.Sound(sound_path)
            if sound.get_length() > 0: # need to check length of sound (cant play sound with no data!)
                sound.set_volume(0.04*12*self.volume)
                self.mixer.Channel(0).play(sound)
        return

    @staticmethod
    def pitch_it(data):
        '''Pitch algorithm - based on the SP1200 algorithm'''
        pitch_snd = []

        # Get lower pitch data (-1 thru -12 semitones)
        for n in np.arange(1,13):
            idx = np.arange(0, data.shape[0] * 2**(n/12) ) * 2**(-n/12)
            idx_floor = np.floor(idx).astype("int")
            new_data = data[idx_floor[idx_floor < data.shape[0]]]
            pitch_snd.append(pygame.sndarray.make_sound(new_data))

        pitch_snd.reverse() # Reverse the list sp lowest pitch is at the bottom
        pitch_snd.append(pygame.sndarray.make_sound(data))

        # get higher pitch data (+1 thru +12 semitones)
        for n in np.arange(1,13):
            idx = np.arange(0, data.shape[0]) * 2**(n/12)
            idx_floor = np.floor(idx).astype("int") # can try round
            new_data = data[idx_floor[ idx_floor < data.shape[0]]]
            pitch_snd.append(pygame.sndarray.make_sound(new_data))

        return pitch_snd

# EOF
