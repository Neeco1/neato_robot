#!/usr/bin/python

from websocket import create_connection
import threading

import signal
import time

class neato_ws:

    def rx_thread(self):
        while not self.kill_now:
            # Exception will be thrown in case recv times out
            try:
                # Lock WS lock and receive
                with self.lockWs:
                    result = self.ws.recv()

                # Lock lines lock and save
                with self.lockLines:
                    self.lines.extend(result.splitlines())
                    #Remove all \x1A from list
                    #list(filter(lambda a: a != '\x1A', x))
                    #print("Size: " + len(self.lines))

                # Notify anyone waiting for data
                with self.cvLines:
                    self.cvLines.notify()

            except:
                time.sleep(0.1)

#        with self.cvLines:
#            self.cvLines.notify()

    def exit_gracefully(self, signum, frame):
        self.kill_now = True
        with self.cvLines:
            self.cvLines.notify()

    def __init__(self, port):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # Flag if thread should be stopped
        self.kill_now = False

        # Create members

        # Will hold received lines
        self.lines = []
        # Lock for accesing the lines list
        self.lockLines = threading.Lock()
        # Condition variable for waiting until stuff is in the list
        self.cvLines = threading.Condition()


        self.ws = create_connection(port, 1)
        # Lock for accessing the websocket object
        self.lockWs = threading.Lock()

        # Spawn RX thread
        self.rxThread = threading.Thread(name='rx_thread',
                                         target=self.rx_thread)
        self.rxThread.setDaemon(True)
        self.rxThread.start()

        # Wait for message "connected to Neato"
        while not self.readline() == "connected to Neato":
            time.sleep(0.1)

        print("Neato WS initialized.")

    def write(self, cmd):
        # Lock WS lock and send
        with self.lockWs:
            result = self.ws.send(cmd)
        time.sleep(0.1)

    def flushInput(self):
        with self.lockLines:
            self.lines = []

    def readline(self):
        self.lockLines.acquire() # Lock the data list
        # Wait until rxthread fills the list: Check length
        while len(self.lines) == 0 and not self.kill_now:
            self.lockLines.release() # Release lock for data list
            with self.cvLines: # Grab lock of condvar
                self.cvLines.wait(0.1) # wait again
                if self.kill_now:
                    return ""
                self.lockLines.acquire() # Reacquire lock after wake

        if self.kill_now:
            self.lockLines.release() # Release lock
            return ""

        try:
            line = self.lines.pop(0)
        except:
            line = ""

        self.lockLines.release() # Release lock
        return line;
