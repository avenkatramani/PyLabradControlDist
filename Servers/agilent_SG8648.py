# -*- coding: utf-8 -*-
"""
Created on Sun Nov 26 13:00:29 2017

@author: Sergio Cantu

### BEGIN NODE INFO
[info]
name = agilent_sg8648
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

from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
from Queue import Queue
import socket
import time, sys, shutil
import threading
from twisted.internet.defer import returnValue,inlineCallbacks
import visa

#GPIB address
addr = 12


class Agilent_SG8648(LabradServer):
    """Server to program Agilent 33250A arbitrary waveform generator (over GPIB) """
    name="agilent_sg8648"
    
    def initServer(self):
        rm = visa.ResourceManager()
        visa_addr = "GPIB0::%d::INSTR" % addr
        print "Opening connection to VISA address %s" % visa_addr
        self.inst = rm.open_resource(visa_addr)
        
    @setting(1,'RFonoff',b0='b')
    def RFonoff(self,c,b0):
        """ turn RF on/off """
        if b0:
            self.inst.write("OUTP:STAT ON")
        else:
            self.inst.write("OUTP:STAT OFF")
    
    @setting(2,'setPower',P='v')
    def setPower(self,c,P):
        """ Sets the amplitude of the RF output to the
            desired <value> and <units>. <value> may
            be up to 4 digits plus a sign if applicable """
        pow_dBm = P['dBm']
        self.inst.write("POW:AMPL %.4f dBm" % pow_dBm)

    @setting(3,'setFreq',F='v')
    def setFreq(self,c,F):
        """ Sets the amplitude of the RF output to the
            desired <value> and <units>. <value> may
            be up to 4 digits plus a sign if applicable """
        freq_MHz = F['MHz']
        self.inst.write("FREQ:CW %0.4f MHz" % freq_MHz)
        
if __name__ == "__main__":
    from labrad import util
    util.runServer(Agilent_SG8648())