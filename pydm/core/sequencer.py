from multiprocessing import Pipe
from copy import deepcopy

import numpy as np


class States:
    '''Simple container for sequencer states'''
    playing = False
    rec = False
    met = True
    delete = False

# -- Sequencer Class
class Sequencer:
    '''Controls playback, sets sequence notes, implments auto-correct
    Checks clock state (also starts the clock process)
    Controls/Sets the current sequnce and a lot more (This is real nuts and bolts of the app)
    '''

    auto_cor = ["4","8","8t","16","16t","32", "32t", "HI-REZ"]
    # Parts per quarter note PPQN (Determines 'resolution' of a sequence via number of pulses)
    # 24 is PPQN, 96 is toal nuber of pulses in a bar at 4/4
    note_ppq = [
        np.array([0,24]),  # Quarter Notes
        np.array([0,12,24]), # Eight Notes
        np.array([0,8,16,24]), # Eight Notes triplets
        np.array([0,6,12,18,24]), # 16th notes
        np.array([0,4,8,12,16,20,24]), # 16th triplets
        np.array([0,3,6,9,12,15,18,21,24]), # 32nd
        np.array([0,2,4,6,8,10,12,14,16,18,20,22,24]), # 32nd triplets
        np.array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24]) # Hi-rez 64 triplets
    ]

    # Variables for sequence playback and displaying location in sequence
    now_count = ['pulse','beat','bar']
    pulse = 0 #
    beat = 0 #
    bar = 0 #
    step = False

    # Default setting BPM = 90, SEQnum = 0, timing/auto correct set to Quarter Notes
    bpm = 90
    tc = 0
    seq_num = 0
    #swing = {0: "50%", 1: "54%", 2: "58%", 3: "63%", 4: "66%", 5:"71%"}
    swing_values = [[6,7,8,9], [18,19,20,21]]

    def __init__(self, ClockGen):
        self.receive_conn, self.send_conn = Pipe(True)
        self.clock = None
        self.ClockGen = ClockGen
        self.state = States()

        for val in self.now_count:
            setattr(self, val, 0)

        self.queued_seq = None
        self.is_song = False
        self.seq_configs = None
        self.error = False
        self.perform_seq = None

    # ===========================
    def load_config(self, config):
        '''Set sequencer parameters using config file from Disk'''
        self.seq_configs = config['seqs']
        self.bpm = config['global']['bpm']
        self.state.met = config['global']['met']
        self.tc = config['global']['quantize']
        return

    # ===========================
    def set_seq(self):
        '''Only used by load_disk in Disk mode'''
        self.seq_num = 0
        self.queued_seq = None

        self.current_seq = self.sequences[self.seq_num]
        self.seq_record = self.current_seq
        self.copy_rec_to_play()

        return

    def copy_rec_to_play(self):
        '''Copy recorded sequence into playing sequence'''
        self.seq_play = self.seq_record.copy()
        
        if self.seq_configs[self.seq_num]['swing'] != 0:
            self.copy_swing()

        return

    def copy_swing(self):
        '''Copy notes to swing values if applicable'''
        swing = self.seq_configs[self.seq_num]['swing']
        for swing_notes in self.swing_values:
            start = swing_notes[swing]
            note = swing_notes[0]
            self.seq_play[:, start::24] = self.seq_record[:, note::24].copy()
            self.seq_play[:, note::24] = (0,0)

        return

    # --------------------------------------------------------------------------
    '''Sequence functions: Build/Init, copy/delete and change'''
    def make_seq(self, length = 2):
        seq = np.zeros((32, 24*4*length), dtype='i,i') # add 'i,i,i' for volume
        return seq

    def copy_seq(self, source_index, dest_index):
        if self.sequences[dest_index].size == 1: # uninit seq
            seq_copy = self.sequences[source_index].copy()
            self.sequences[dest_index] = seq_copy
        else: # need to concat
            source_seq = self.sequences[source_index].copy()
            dest_seq = self.sequences[dest_index].copy()
            self.sequences[dest_index] = np.hstack((dest_seq, source_seq))

        self.change_seq(0)
        return

    def init_seq(self, seq_num, length):
        self.sequences[seq_num] = self.make_seq(length)
        self.change_seq(0)
        return

    def delete_seq(self, seq_idx):
        self.sequences[seq_idx] = np.zeros((), dtype='i,i')
        self.change_seq(0)
        return

    def change_seq(self, val):
        '''Changes sequnce, or queues the next seq'''
        # if the seq we change to is not init, stop play
        if self.state.playing:
            if self.queued_seq is not None:
                self.queued_seq = max(0, min(len(self.sequences)-1, self.queued_seq + val))
            else:
                self.queued_seq = max(0, min(len(self.sequences)-1, self.seq_num + val))

        elif (self.state.rec == False or self.state.playing == False):
            self.seq_num = max(0, min(len(self.sequences)-1, self.seq_num + val))
            self.current_seq = self.sequences[self.seq_num]
            self.seq_record = self.current_seq
            self.copy_rec_to_play()

    # --------------------------------------------------------------------------
    '''Properties for sharing with LCD etc.'''
    @property
    def count(self):
        # This would be Sequencer.get_count() or Sequencer.count [a property]
        c = [self.bar + 1, self.beat + 1, self.pulse]
        c[2] = self.pulse - 24 * self.beat - 96 * self.bar
        return f"0{c[0]}.0{c[1]}.{c[2]}"

    @property
    def ac(self):
        return self.auto_cor[self.tc]

    @property
    def seq(self):
        '''Used by perform mode to display seq number or queued'''
        seq = str(self.seq_num)
        if self.queued_seq is not None:
            seq = str(self.queued_seq) + '*'

        return seq

    # --------------------------------------------------------------------------
    '''Clock/Sequnecer start/stop functions''' 
    def toggle_play(self, song=False, seq_list=None): # ,is_song=False
        if self.state.playing:
            self.stop()
            self.step = False
            return

        if song:
            self.perform_seq = self.seq_num
            self.song_seqs = deepcopy(seq_list)
            self.is_song = True
            self.check_seq_valid()
            if self.is_song:
                self.start()
        else:
            if self.current_seq.size == 1:
                self.error = True
                return
            self.start()

        self.step = False
        return

    def start(self):
        self.state.playing = True
        self.clock = self.ClockGen()
        self.clock.shared_bpm.value = self.bpm
        self.clock.launch_process(self.send_conn)
        return

    def stop(self):
        if self.perform_seq is not None:
            self.seq_num = self.perform_seq
            self.perform_seq = None

        if self.clock is not None and self.clock._run_code.value == 1:
            self.clock.end_process()
            self.current_seq = self.sequences[self.seq_num]
            self.seq_record = self.current_seq
            self.copy_rec_to_play()
            self.state.playing = False
            self.queued_seq = None
            for val in self.now_count:
                setattr(self, val, 0)
        return

    def check_clock(self):
        '''Check if clock is running, if so, stop the process'''
        if self.clock._run_code.value == 1:
            self.clock.end_process()

    # --------------------------------------------------------------------------
    '''Check for sounds and/or metronome to play'''
    def update(self):
        # if first entry is true, we are on valid pulse, so check for sound(s) to play
        # if second entry is true, we need to play the metronome
        seq_met = [False, False] # Document this better 
        
        if self.step == True:
            self.step_end()
            self.step = False

        if self.receive_conn.poll(): # Check if we have a clock pulse
            _ignore = self.receive_conn.recv() # need to remove the item from the Pip conncetion
            if self.state.playing:
                self.step = True
                seq_met[0] = True #self.to_play(snd_engine, pads)
                if (self.pulse % 24 == 0 and self.state.met):
                    seq_met[1] = True #snd_engine.play_met()
        return seq_met

    def step_end(self):
        '''Called during Sequencer update | when we each the end of a bar/beat etc, set the next one'''
        self.pulse += 1
        if self.pulse == self.seq_play.shape[1]:
            self.pulse = 0

        if self.pulse % 24 == 0:
            self.beat += 1

        if self.beat == 4:
            self.beat = 0
            self.bar += 1

        if self.bar == int(self.seq_play.shape[1]/96): # We need to get seq length here
            self.bar = 0
            self.copy_rec_to_play()

            if self.is_song:
                self.check_seq_valid()
                if self.is_song == False:
                    return

            elif self.queued_seq is not None:
                if self.sequences[self.queued_seq].size == 1:
                    self.stop()
                else:
                    self.current_seq = self.sequences[self.queued_seq]
                    self.seq_num = self.queued_seq
                    self.queued_seq = None
                    self.seq_record = self.current_seq
                    self.copy_rec_to_play()
        return

    # --------------------------------------------------------------------------
    def check_seq_valid(self):
        '''Used to check if we have reached to end of a song playback list'''
        check = True
        while check:
            if len(self.song_seqs) > 0:
                seq_num = self.song_seqs.pop(0)
                if self.sequences[seq_num].size != 1:
                    check = False
            else:
                self.is_song=False
                self.stop()
                return

        self.seq_num = seq_num
        self.current_seq = self.sequences[seq_num]
        self.seq_record = self.current_seq
        self.copy_rec_to_play()
        return

    # --------------------------------------------------------------------------
    # -- Set and toggle fucntions
    def toggle_rec(self):
        self.state.rec = not self.state.rec

    def toggle_met(self):
        self.state.met = not self.state.met

    def toggle_delete(self):
        self.state.delete = not self.state.delete

    def set_bpm(self, val, knob=False):
        self.bpm = max(50, min(240, self.bpm+val))

        if self.clock:
            self.clock.shared_bpm.value = self.bpm

    def set_tc(self, val):
        self.tc = max(0, min(len(self.note_ppq)-1, self.tc+val))

    # --------------------------------------------------------------------------
    # -- Record, Delete, Play Note Logic
    def record(self, idx, pitch):
        tick = self.auto_correct()
        self.seq_record[idx, tick] = (1, pitch)
    
    def delete(self, idx, whole = False):
        tick = self.auto_correct()
        self.seq_record[idx, tick] = 0 # Scale idx to bank
       
        if whole: 
            self.seq_record[idx, :] = 0 # 'Delete whole track
        
        self.copy_rec_to_play()
        return
        
    # -- Grid record function
    def grid_edit(self, chan, pulse, record, pitch):
        if record:
            self.seq_record[chan, pulse][0] = 1
            self.seq_record[chan, pulse][1] = pitch #pads[chan].pitch
        if not record:
            self.seq_record[chan, pulse][0] = 0
        self.copy_rec_to_play()

        return
        
    # -- AUTOCORRECT FUNCTION
    def auto_correct(self):
        '''Corrects input to nearest value based on auto correct settings'''
        scaled_ac = self.note_ppq[self.tc] + 24*self.beat + 96*self.bar
        correct_to_idx = np.argmin(np.abs(self.pulse - scaled_ac))
        correct_to = scaled_ac[correct_to_idx]
        if correct_to == self.seq_play.shape[1]:
            correct_to = 0
        return correct_to

    
    
# EOF
