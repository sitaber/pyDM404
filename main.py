# -----------------------------------------------------------------------------
# pyDM404 - A cross platform Drum Sequencer
# Author: Scott Taber
# File: main.py - entry point for the application
#
# LINKS: refer to the links for more information about structure of this file
# (1) https://docs.python.org/3/library/multiprocessing.html#the-spawn-and-forkserver-start-methods
# (2) https://docs.python.org/3/library/multiprocessing.html#multiprocessing.freeze_support
# (3) https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
# -----------------------------------------------------------------------------

from multiprocessing import freeze_support, set_start_method, Pipe

#  “entry point” protection, see (1) "Safe importing of main module"
if __name__ == '__main__':
    freeze_support() # Required on Windows to package executable, see (2)
    set_start_method('spawn') # Make behavior of start method the same for all platforms, see (3)
    
    # Import app, setup Pipe for communication, and start application -------- #
    import app
    receive_conn, send_conn = Pipe(True)
    engine = app.DrumMachine(receive_conn, send_conn)
    engine.main_loop()
