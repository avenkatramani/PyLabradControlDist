# -*- coding: utf-8 -*-
"""
Created on Thu Sep 08 22:12:18 2016

@author: Sergio H. Cantu

"""

"""
### BEGIN NODE INFO
[info]
name = rigol_a
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
import numpy as np

COUPLINGS = ['AC', 'DC']
VERT_DIVISIONS = 5.0
HORZ_DIVISIONS = 10.0
SCALES = []


class Rigol_A(LabradServer):
    """Server for Rigol Tech. DS1000Z oscilloscope """
    name="rigol_a"
    
    def initServer(self):
    # runs when server launches. Should establish connection
        rm = visa.ResourceManager() 
        visaname = "Rigol_A" 
        print "Opening connection to oscilloscope : " + visaname 
        self.inst = rm.get_instrument(visaname)
        print str(self.inst.query('*IDN?'))
    
    # this is just a test
    @setting(1,"echo", returns="?")
    def echo(self,c):
        """Test echo"""
        return "echo"
        
    #reset device
    @setting(11,"reset", returns="?")        
    def reset(self,c):
        dev = self.inst
        yield dev.write('*RST')
        return 
    #Channel settings
    @setting(12, "channel_info", channel = 'i', returns = '(vsvvssss)')
    def channel_info(self, c, channel):
        """channel(int channel)
        Get information on one of the scope channels.
        OUTPUT
        Tuple of (probeAtten, ?, scale, position, coupling, bwLimit, invert, units)
        """
        #NOTES
        #The scope's response to 'CH<x>?' is a string of format
        #'1.0E1;1.0E1;2.5E1;0.0E0;DC;OFF;OFF;"V"'
        #These strings represent respectively,
        #probeAttenuation;?;?;vertPosition;coupling;?;?;vertUnit

        dev = self.inst
        resp = yield dev.query('CH%d?' %channel)
        probeAtten, iDontKnow, scale, position, coupling, bwLimit, invert, unit = resp.split(';')

        #Convert strings to numerical data when appropriate
        probeAtten = T.Value(float(probeAtten),'')
        #iDontKnow = None, I don't know what this is!
        scale = T.Value(float(scale),'')
        position = T.Value(float(position),'')
        coupling = coupling
        bwLimit = bwLimit
        invert = invert
        unit = unit[1:-1] #Get's rid of an extra set of quotation marks

        returnValue((probeAtten,iDontKnow,scale,position,coupling,bwLimit,invert,unit))

    @setting(22, "coupling", channel = 'i', coupling = 's', returns=['s'])
    def coupling(self, c,channel, coupling = None):
        """Get or set the coupling of a specified channel
        Coupling can be "AC" or "DC"
        """
        dev = self.inst
        if coupling is None:
            resp = yield dev.query('CH%d:COUP?' %channel)
        else:
            coupling = coupling.upper()
            if coupling not in COUPLINGS:
                raise Exception('Coupling must be "AC" or "DC"')
            else:
                yield dev.write(('CH%d:COUP '+coupling) %channel)
                resp = yield dev.query('CH%d:COUP?' %channel)
        returnValue(resp)
    
    @setting(23,"pk2pk", channel = 'i', returns = 'v[]')
    def pk2pk(self, c, channel):
        """Get pk2pk measurement of channel i
        """
        dev = self.inst
        dev.write('MEASU:IMM:SOU CH%d' %channel)
        dev.write('MEASU:IMM:TYP PK2pk')
        resp = dev.query('MEASU:IMM:VAL?')
        pk2pk0 = float(eval(resp))
        return(pk2pk0)
    
    @setting(33,"scale", channel = 'i', scale = 'v',returns = ['v'])
    def scale(self, c, channel,scale = None):
        """Get or set the vertical scale of a channel
        """
        dev = self.inst
        if scale is None:
            resp = yield dev.query('CH%d:SCA?' %channel)
        else:
            scale = format(scale,'E')
            yield dev.write(('CH%d:SCA '+scale) %channel)
            resp = yield dev.query('CH%d:SCA?' %channel)
        scale = float(resp)
        returnValue(scale)

    @setting(25,"channelOnOff", channel = 'i', state = '?', returns = '')
    def channelOnOff(self, c, channel, state):
        """Turn on or off a scope channel display
        """
        dev = self.inst
        if isinstance(state, str):
            state = state.upper()
        if state not in [0,1,'ON','OFF']:
            raise Exception('state must be 0, 1, "ON", or "OFF"')
        if isinstance(state, int):
            state = str(state)
        yield dev.write(('SEL:CH%d '+state) %channel)
        
    #Data acquisition settings
    @setting(41,"get_trace", channel = 'i', start = 'i', stop = 'i', returns='*?')
    def get_trace(self, c, channel, start=1, stop=2500):
        """Get a trace from the scope.
        OUTPUT - (array time in seconds,array voltage in volts )
        """
        ##        DATA ENCODINGS
        ##        RIB - signed, MSB first
        ##        RPB - unsigned, MSB first
        ##        SRI - signed, LSB first
        ##        SRP - unsigned, LSB first
        #Hardcoding to set data transer word length to 1 byte
        recordLength = stop-start+1
        wordLength = 1
        dev = self.inst
        resp = dev.query('CH%d?' %channel)
        probeAtten, iDontKnow, scale, position, coupling, bwLimit, invert, unit = resp.split(';')
        
        probeAtten = float(probeAtten)
        #iDontKnow = None, I don't know what this is!
        scale = float(scale)
        position = float(position)
        coupling = coupling
        bwLimit = bwLimit
        invert = invert
        unit = unit[1:-1]
        wordLength = 1 #Hardcoding to set data transfer word length to 1 byte
        recordLength = stop-start+1
        
        #DAT:SOU - set waveform source channel
        dev.write('DAT:SOU CH%d' %channel)
        #DAT:ENC - data format (binary/ascii)
        dev.write('DAT:ENC RIB')
        #osc.values_format.use_binary('d', False, np.array)
        
        #Set number of bytes per point
        dev.write('DAT:WID %d' %wordLength)
        
        #Starting and stopping point
        if not (start<2500 and start>0 and stop<2501 and stop>1):
            raise Exception('start/stop points out of bounds')
        dev.write('DAT:STAR %d' %start)
        dev.write('DAT:STOP %d' %stop)
        #Transfer waveform preamble
        preamble = dev.query('WFMPre?')
        
        #Transfer waveform data
        #binary = osc.query_binary_values('CURVe?')#osc.query('CURV?').decode("utf8")
        trace = dev.query_binary_values('CURVe?', datatype='b', is_big_endian=True, container=np.array)
        
        #Parse waveform preamble
        segPerVertDiv = float(eval(dev.query('WFMPre:YMUlt?'))) #segments per vertical division
        secPerDiv = eval(dev.query('HOR:MAI:SEC?'))
        
        #Parse binary
        #trace = _parseBinaryData(binary,wordLength = wordLength)
        #Convert from binary to volts
        traceVolts = scale*((VERT_DIVISIONS*segPerVertDiv)*trace-position)
        time = np.linspace(0,HORZ_DIVISIONS*secPerDiv*recordLength*(1.0/len(trace)),len(trace))
        return [time,traceVolts]

    @setting(61,"query", inputstr = 's', returns='s')    
    def query(self,c,inputstr):
        dev = self.inst
        resp = dev.query(inputstr)
        return str(resp)
        
    @setting(62,"write", inputstr = 's', returns='s')    
    def write(self,c,inputstr):
        dev = self.inst
        resp = dev.write(inputstr)
        return str(resp)
        
__server__ = Rigol_A()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)