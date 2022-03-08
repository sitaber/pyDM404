# -----------------------------------------------------------------------------
# pyDM404 - A cross platform Drum Sequencer
# Author: Scott Taber
# File: clock.py - Contains the Clock class for controlling the timer process
#
# modified from https://github.com/ElliotGarbus/MidiClockGenerator
# -----------------------------------------------------------------------------

from time import perf_counter, sleep, time
from multiprocessing import Process, Value

class ClockGen:
    def __init__(self):
        self.shared_bpm = Value('f', 60)
        self._run_code = Value('i', 1)  # used to stop midiClock from main process
        self.clock_process = None

    @staticmethod
    def _clock_generator(out_port, bpm, run):

        while run.value:
            pulse_rate = 60.0 / (bpm.value * 24)
            out_port.send(1)
            t1 = perf_counter()
            if bpm.value <= 3000:
                sleep(pulse_rate * 0.8)
            t2 = perf_counter()
            while (t2 - t1) < pulse_rate:
                t2 = perf_counter()

    def launch_process(self, out_port):
        if self.clock_process:  # if the process exists, close prior to creating a new one
            self.end_process()
        
        self._run_code.value = 1
        self.clock_process = Process(target=self._clock_generator,
                                    args=(out_port, self.shared_bpm, self._run_code),
                                    name='midi-background')
        self.clock_process.start()

    def end_process(self):
        self._run_code.value = 0
        self.clock_process.join()
        self.clock_process.close()

