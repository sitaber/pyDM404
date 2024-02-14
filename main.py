# -----------------------------------------------------------------------------
# pyDM404 - A cross platform Drum Sequencer
# File: main.py - entry point for the application
#
# LINKS: refer to the links for more information about structure of this file
# (1) https://docs.python.org/3/library/multiprocessing.html#the-spawn-and-forkserver-start-methods
# (2) https://docs.python.org/3/library/multiprocessing.html#multiprocessing.freeze_support
# (3) https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
# -----------------------------------------------------------------------------

import sys
from multiprocessing import freeze_support, set_start_method

from time import perf_counter, sleep, time
from multiprocessing import Process, Value

# -----------------------------------------------------------------------------
'''We put the multiprocess clock here so that when using set_start_method('spawn'), we
do not import the whole pydm package/modules again'''


class ClockGen:
    '''ClockGen: class for controlling the timer process
    modified from https://github.com/ElliotGarbus/MidiClockGenerator

    MIT License

    Copyright (c) 2019 Elliot Garbus

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    '''
    # TODO: Needs more comments/documentation
    def __init__(self):
        self.shared_bpm = Value('f', 60)
        self._run_code = Value('i', 1)  # used to stop Clock from main process
        self.clock_process = None

    @staticmethod
    def _clock_generator(out_port, bpm, run):

        while run.value:
            pulse_rate = 60.0 / (bpm.value * 24) # NUmber of pulses in 60 seconds
            out_port.send(1)
            t1 = perf_counter()
            
            t2 = perf_counter()
            while (t2 - t1) < pulse_rate:
                t2 = perf_counter()

    def launch_process(self, out_port):
        if self.clock_process:  # if the process exists, close prior to creating a new one
            self.end_process()

        self._run_code.value = 1
        self.clock_process = Process(
            target = self._clock_generator,
            args = (out_port, self.shared_bpm, self._run_code),
            name='pydm-clock-background'
        )
        self.clock_process.start()

    def end_process(self):
        self._run_code.value = 0
        self.clock_process.join()
        self.clock_process.close()

#  “entry point” protection, see (1) "Safe importing of main module"
if __name__ == "__main__":
    freeze_support() # Required on Windows to package executable, see (2)
    set_start_method('spawn') # Make behavior of start method the same for all platforms, see (3)

    from pydm import app
    app.run(ClockGen)
    sys.exit()

#
