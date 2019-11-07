# this is a prototype server for programming the PulseBlaster.
# It is loosely modeled on data_vault_v2.2.py
#
# JDT 2/2010

"""
### BEGIN NODE INFO
[info]
name = pulseblaster
version = 1.0
description =
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

# these includes might not all be necessary; just copied from something else
from __future__ import with_statement

from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting

from spincore import SpinAPI


class PBServer(LabradServer):
    """Interface to PulseBlaster Digital I/O Card"""
    name = "pulseblaster"
    started = 0

    def initServer(self):
        self.board = SpinAPI()
        self.board.connect()
        self.started = 1


    def stopServer(self):
        if self.started == 1:
            self.board.disconnect()
            self.started=0


    # here come the functions that other scripts can call
    @setting(2,"Start",data="",returns="b")
    def start(self,c,data):
        """Start the PulseBlaster card"""
        self.board.start()
        return True

    @setting(3,"Stop",data="",returns="b")
    def stop(self,c,data):
        """Stop the PulseBlaster card"""
        self.board.stop()
        return True

     
    @setting(6,"Reset")
    def reset(self,c):
        """Reset the task list. This is only important for loops: will erase memory
of previously programmed loops. Good hygiene to use it every time."""

        self.board.reset()

    @setting(7,"wait",time="v",loop="w")
    def wait(self,c,time,loop):
        """Instruct the board to wait at a certain time for a hardware trigger. Optionally
        can specify whether the board should loop back to the waiting point at the end"""

        if loop==1:
            loopBool=True
        else:
            loopBool=False
            
        self.board.setupWait( time['ns'], loopBool)

       
    @setting(101,"program", loops = "*v",states ="*v",delays="*v", returns="b")
    def program(self,c, loops, states, delays):
        # states="*w", delays= "*v", 
        """set one output on the PulseBlaster card.
            Input is a list of values and a list of words (unsigned integers).
            The values are times, and the words are the new states to be set at those times"""
       
        self.board.reset()
        states = [int(x) for x in states]
        states = [s & (2**24 - 1) for s in states]
        loops =  [int(x) for x in loops]
        
        self.board.program(loops, states, delays)
        self.board.start()
        
        return True
        
    @setting(102,"delay_max",  returns="w")
    def delay_max(self,c):
        answer = (2.0**8/self.board.clock())*10**-6
        return answer 
        
    @setting(103,"delay_per_command",  returns="w")
    def delay_cmd(self,c):
        answer = (3.0/self.board.clock())*10**-6
        return answer 

    @setting(104,"initial_delay",  returns="w")
    def delay_init(self,c):
        answer = (5.0/self.board.clock())*10**-6


if __name__ == "__main__":
    from labrad import util
    util.runServer(PBServer())
