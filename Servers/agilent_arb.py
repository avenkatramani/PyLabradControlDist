"""
### BEGIN NODE INFO
[info]
name = agilent_arb
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


#from common import *


#GPIB address
addr = 11

class Agilent_Arb(LabradServer):
    """Server to program Agilent 33250A arbitrary waveform generator (over GPIB) """
    name="agilent_arb"
    
    def initServer(self):
        rm = visa.ResourceManager()
        visa_addr = "GPIB0::%d::INSTR" % addr
        print "Opening connection to VISA address %s" % visa_addr
        self.inst = rm.open_resource(visa_addr)

            
    @setting(2,'DC',V='v')
    def DC(self,c,V):
        """ set output to DC mode at voltage V """
        
        self.inst.write("APPL:DC DEF,DEF, %.4f" % V)
        self.inst.write("OUTP ON")
        
    @setting(5,'gated_sine',Vamp='v',Voff='v',freq='v')
    def gated_sine(self,c,Vamp,Voff, freq):
        command_strings = []
        command_strings.append(r':FUNC SIN')
        command_strings.append(r':VOLT %.4f V' % Vamp) #Vpp
        command_strings.append(r':FREQ %.4f' % freq) #Hz
        command_strings.append(r' :VOLT:OFFS %.4f V' % Voff)
        command_strings.append(r':TRIG:SOUR EXT')
        command_strings.append(r':TRIG:DEL MIN')
        command_strings.append(r':TRIG:SLOP POS')
        command_strings.append(r':OUTP:LOAD INF')
        command_strings.append(r':BURS:STAT ON')
        command_strings.append(r':BURS:MODE GAT')
        command_strings.append(r':BURS:GATE:POL NORM')
        command_strings.append(r':OUTP ON')
        
        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
            
        print command_total
            
        self.inst.write(command_total)
        
        
    @setting(3,'square_pulse',Vhigh='v',period='v',width='v',edge='v')
    def square_pulse(self,c,Vhigh,period,width,edge):
        
        command_strings = []
        
        command_strings.append(r':FUNC PULS')
        
        command_strings.append(r':TRIG:SOUR EXT')
        command_strings.append(r':TRIG:SLOP POS')
        command_strings.append(r':TRIG:DEL MIN')
        command_strings.append(r':BURS:STAT ON')
        command_strings.append(r':BURS:NCYC 1')
        command_strings.append(r':BURS:MODE TRIG')
        command_strings.append(r':OUTP:LOAD INF')
        
        command_strings.append(r':VOLT:RANG:AUTO ON')
        
        command_strings.append(r':VOLT:HIGH %.4f V' % Vhigh)
        command_strings.append(r':VOLT:LOW %.4f V' % 0.0)
        
        command_strings.append(r':PULS:PER %.9f s' % period)
        command_strings.append(r':PULS:TRAN %.9f s' % edge)
        command_strings.append(r':PULS:WIDT %.9f s' % width)
        
        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
            
        print command_total
            
        self.inst.write(command_total)
        
    @setting(4,'arb',total_time='v', voltages='*v')
    def arb(self,c,total_time, voltages):
        #The voltage values should go from -2047 to +2047.
        # the Vmin/Vmax commands specify how these map to actual output voltages.    
        voltage_max = max(voltages)
        voltage_min = min(voltages)
        data_scaled = [ int(round(2*2047*(x - voltage_min)/(voltage_max - voltage_min) - 2047)) for x in voltages]
        
        self._sendWf(data_scaled,voltage_min,voltage_max,total_time)
        
        return 1
        
    
    def _sendWf(self,wf_data,Vbot,Vtop,ttot,ncycles=1,load=50):
        # function for internal use, takes array of data wf_data,
        # min,max voltages (in Volts)
        # total time of sequence (in seconds)
        # number of cycles
        # and impedance of output (to interpret voltages)
        
        # wf_data should range from -2047 to 2047
        
        #print wf_data

        #nBytesStr = str(2*array_len)
        #byteStrLen = len(nBytesStr)

        command_string = ":OUTP OFF;:DATA:DAC VOLATILE"
        for pt in wf_data:
            command_string += ", %d" % int(pt)
            
        self.inst.write(command_string)

      
        
        command_strings = []
        command_strings.append(r':FUNC:USER VOLATILE')
        command_strings.append(r':FUNC:SHAP USER')
        command_strings.append(r':TRIG:SOUR EXT')
        command_strings.append(r':TRIG:SLOP POS')
        command_strings.append(r':TRIG:DEL MIN')
        command_strings.append(r':BURS:STAT ON')
        command_strings.append(r':BURS:NCYC '+str(ncycles))
        command_strings.append(r':BURS:MODE TRIG')

        # important to set this before specifying voltages
        if load>50:
            command_strings.append(r':OUTP:LOAD INF')
        else:
            command_strings.append(r':OUTP:LOAD INF')
        command_strings.append(r':OUTP:POL NORM')

    
        command_strings.append(r':VOLT:RANG:AUTO ON')

        freq = 1.0/ttot
        command_strings.append(':FREQ %f' % freq)

        command_strings.append(r':VOLT:HIGH %f' % Vtop)
        command_strings.append(r':VOLT:LOW %f' % Vbot)

        command_strings.append(r':OUTP ON')

        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
            
        self.inst.write(command_total)

        print "Sent: %s" % command_total

        
if __name__ == "__main__":
    from labrad import util
    util.runServer(Agilent_Arb())

    
