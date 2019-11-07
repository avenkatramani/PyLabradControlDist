#
# Server for digital output with NI-6534
#
#Modified by Aditya 07/2016
"""
### BEGIN NODE INFO
[info]
name = ni6535_digital
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
import numpy as np
import datetime

from ctypes import *

import matplotlib.pyplot as plt

########### nidaq.h types and constants
# set up c type names
int32 = c_long
uInt32 = c_ulong
uInt64 = c_ulonglong
float64 = c_double


# define some stuff which would have been done in a header file

# types
TaskHandle = uInt32

# constants
DAQmx_Val_Volts = 10348

DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171

DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_HWTimedSinglePoint = 12522

DAQmx_Val_GroupByChannel = 0
DAQmx_Val_GroupByScanNumber = 1

DAQmx_Val_Bit_TermCfg_RSE = 1
DAQmx_Val_Bit_TermCfg_NRSE = 2     
DAQmx_Val_Bit_TermCfg_Diff = 4     
DAQmx_Val_Bit_TermCfg_PseudoDIFF = 8

DAQmx_Val_Cfg_Default = -1

DAQmx_Val_ChanPerLine = 0   # One Channel For Each Line
DAQmx_Val_ChanForAllLines = 1   # One Channel For All Lines

DAQmx_Val_DMA = 10054
DAQmx_Val_ProgrammedIO = 10264
DAQmx_Val_Interrupts = 10204


#############

############# settings
numChannels = 32
channel_string = "Dev5/line0:31" 
#NOTE - Very wierd error... if the clock is RTSI 4 or 5, the trigger for digital does not seems to work ?

clock_source = '/Dev5/RTSI1'  
trigger_source = '/Dev5/RTSI6'


#############

class NI6535_Digital(LabradServer):
    """Digital output server"""

    name="ni6535_digital"
    nidaq = windll.nicaiu

    password=""

    
    def initServer(self):
        self.clock_freq = 10*10**4
        self.sampsPerChanWritten = int32(0)
        self.reserved = None
	
    @setting(100,"deviceList",returns="s")
    def deviceList(self,c):
        buflen = 1000
        buf = create_string_buffer(buflen)
        self._check(
                    self.nidaq.DAQmxGetSysDevNames(buf,uInt32(buflen))
                    )

        print buf.value

        return buf.value	

    def stopServer(self):
        self.cleanupTask(0)

    def process_data(self, data_dict):
        #input is dictionary of {Channel: {Time:[], Ramp:[], Value:[]}} 
        
        data = self.insert_ramps(data_dict)        
        
        
        channels = data.keys()
        
        self.numSamples = len(data[channels[0]]['Value'])
        processed_data = np.zeros(self.numSamples)
            
        for channel in channels:
            processed_data += data[channel]['Value'] * 2**channel   
        
        return processed_data
         
    def insert_ramps(self, data_dict):
        data_dict = data_dict #input is dictionary of {Channel: {Time:[], Ramp:[], Value:[]}} 
        channels = data_dict.keys()
        for channel in channels:
            timesch = data_dict[channel]['Time']  
            rampsch = data_dict[channel]['Ramp']  
            valuesch = data_dict[channel]['Value']  
            
            timesch = np.round(np.array(timesch).astype('float')*self.clock_freq).tolist()
            
            values = []
            times = []
        
            for ix2 in range(len(timesch)):
                if ix2 < len(timesch)-1:
                    x =  np.arange(timesch[ix2],timesch[ix2+1],1.0)
    
                    if rampsch[ix2]:
                            slope = (valuesch[ix2+1]-valuesch[ix2])/(timesch[ix2+1]-timesch[ix2])
                            y_values = (slope*(x-timesch[ix2]) + valuesch[ix2])
                    else:
                            slope = 0
                            y_values = (slope*(x-timesch[ix2]) + valuesch[ix2])
    
                    values.extend(y_values.tolist())
                    times.extend((x/self.clock_freq).tolist())
    
                else:
                    x = [timesch[ix2]/self.clock_freq]
                    y_values = [valuesch[ix2]]
                    values.extend(y_values)
                    times.extend(x)


            data_dict[channel]['Time']  = np.array(times)  #NOTE - avoid going back and forth with numpy arrays - cleanup this code
            data_dict[channel]['Value']  = np.array(values) 

        return data_dict
            
    @setting(20,"start")
    def start(self, c): #Start with software
        if getattr(self, 'taskHandle', None) is not None:
            self._check( self.nidaq.DAQmxStartTask(self.taskHandle) )
            
    
    @setting(8,"stopTask",returns="")
    def stopTask(self, c):
        """ clean up aprropriate old tasks, ready to restart """
        if getattr(self, 'taskHandle', None) is not None:
            self._check( 
                        self.nidaq.DAQmxStopTask(self.taskHandle) 
                        )
        
                    
    @setting(2,"program", data_dict="s" )
    def program(self, c, data_dict):
        data = np.array(self.process_data(eval(data_dict)), dtype = np.int32)
        # first, cleanup any old tasks
        self.cleanupTask(c) 

        self.taskHandle = TaskHandle(0)
        self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle)) )

        self._check( self.nidaq.DAQmxCreateDOChan(
            self.taskHandle,
            channel_string,
            "",
            DAQmx_Val_ChanForAllLines #mabe have a channel for each line to speed up transfer ?
            ))


        self._check(
                self.nidaq.DAQmxSetDODataXferMech(
                    self.taskHandle,
                    "",        #channel
                    int32(DAQmx_Val_DMA),        #Mode
                )
            )
            
        self._check(
                self.nidaq.DAQmxSetDOUseOnlyOnBrdMem(
                    self.taskHandle,
                    "",        #channel
                    True,        #Mode
                )
            )

        self._check(
            self.nidaq.DAQmxCfgDigEdgeStartTrig(
            self.taskHandle,
            trigger_source,         # source
            DAQmx_Val_Rising)       # active edge
            )	
            
        self._check( self.nidaq.DAQmxCfgSampClkTiming(
            self.taskHandle,
            clock_source, #source  
            float64(self.clock_freq), # rate
            DAQmx_Val_Rising, #activeEdge
            DAQmx_Val_FiniteSamps, #sampleMode 
            uInt64(self.numSamples) #numSamples
            ))
         
		
        
        #NOTE - need to have atleast 2 samples or otherwise need to configure buffer
            
        self._check(
            self.nidaq.DAQmxWriteDigitalU32(
                self.taskHandle,
                int32(self.numSamples),         # numSampsPerChan
                0,                              # autoStart
                float64(30.0),                  # timeout
                DAQmx_Val_GroupByChannel,       # dataLayout
                data.ctypes.data,          # writeArray[]  #Check if this has to be converted to a ctypes type
                byref(self.sampsPerChanWritten),           # *sampsPerChanWritten
                None)                           # *reserved
            )

        #print(self.sampsPerChanWritten)


    @setting(9,"cleanupTask",returns="")
    def cleanupTask(self,c):
        """ clean up old task, ready to restart """
        
        if getattr(self, 'taskHandle', None) is not None:
            self._check( 
                        self.nidaq.DAQmxStopTask(self.taskHandle) 
                        )
            self._check( 
                        self.nidaq.DAQmxClearTask(self.taskHandle) 
                        )

        self.taskHandle = None


    def _check(self,err):
        """Checks NI-DAQ error messages, prints results"""
        if err > 0 :
            print err
        if err < 0:
            buf_size = 128
            buf = create_string_buffer('\000' * buf_size)
            self.nidaq.DAQmxGetErrorString(err,byref(buf),buf_size)
            raise RuntimeError('NI-DAQ call failed with error %d: %s'%(err,repr(buf.value)))

    
if __name__ == "__main__":
    from labrad import util
    util.runServer(NI6535_Digital())
