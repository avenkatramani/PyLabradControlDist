#
# Server for Analog Outout NI6733
#
#Based off NI6535_Digital Server
#Modified by Sergio and Aditya 07/2016

# NOTE - I'm making analog card A the master card for defining the sample clock (routed to other NI cards through RTSI)
# and the start trigger, routed through RTSI and PFI (for PulseBlaster). Ideally would use the Digital card to do this to 
# restore symmety with the Analog cards. The NI MAX shows no connections between the sampleclock and RTSI, but it seems to work ?
# Also, we would need to wire up the PFI pins for the digital card (is readily avaiable for the all analog cards) 

"""
### BEGIN NODE INFO
[info]
name = ni6733_ao
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

from labrad.server import LabradServer, setting
import numpy as np
import time
import datetime
from ctypes import *

########### nidaq.h types and constants
# set up c type names
int32 = c_long
uInt32 = c_ulong
uInt64 = c_ulonglong
float64 = c_double


#############

# define some stuff which would have been done in a header file

# types
TaskHandle = uInt32

# constants

DAQmx_Val_StartTrigger = 12491
DAQmx_Val_SampleClock = 12487

DAQmx_Val_Volts = 10348

DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171

DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_HWTimedSinglePoint = 12522

DAQmx_Val_GroupByChannel = 0
DAQmx_Val_GroupByScanNumber = 1

DAQmx_Val_Cfg_Default = -1

DAQmx_Val_CountUp = 10128
DAQmx_Val_CountDown = 10124

DAQmx_Val_AllowRegen = 10097
DAQmx_Val_DoNotAllowRegen = 10158

DAQmx_Val_Hz = 10373

DAQmx_Val_High = 10192
DAQmx_Val_Low = 10214
#############


DAQmx_Exported_SampClk_OutputTerm = 0x1663
DAQmx_Exported_SampClk_DelayOffset = 0x21C4
DAQmx_Exported_SampClk_Pulse_Polarity = 0x1664

DAQmx_Val_DMA = 10054
DAQmx_Val_ProgrammedIO = 10264
DAQmx_Val_Interrupts = 10204

DAQmx_Val_Task_Commit = 3

DAQmx_Val_High=10192 # High
DAQmx_Val_Low=10214 # Low


DAQmx_Val_ActiveHigh = 10095
DAQmx_Val_ActiveLow = 10096

DAQmx_Val_Pulse = 10265
DAQmx_Val_Lvl = 10210

############# settings
numChannels = 8

channel_string_A = 'AO_A/ao0:7'  
clock_source_A = None #'/AO_A/PFI5'
trigger_source_A = None #'/Dev2/RTSI5'

channel_string_B = 'AO_B/ao0:7'  
clock_source_B = '/AO_B/RTSI1'
trigger_source_B = '/AO_B/RTSI6'

channel_string_C = 'AO_C/ao0:7' 
clock_source_C = '/AO_C/RTSI1'
trigger_source_C = '/AO_C/RTSI6'
#############

class NI6733_AO(LabradServer):
    """ANALOG output server"""

    name="ni6733_ao"
    nidaq = windll.nicaiu

    password=""

    
    def initServer(self):
        self.clock_freq = 10*10**4 # clock of the trigger card
        self.sampleRate = 10*10**4 # clock of the trigger card
        self.V_max = 10 # +- V
        self.slew_rate = 15*10**-6 # max change V/sec
        self.bit_res = 16 # 16 bit resolution
        self.min_delta_V  = 305*10**-6 # (VoltageRange/2**bit_res)
        self.sampsPerChanWritten = int32(0)
        self.taskHandleA = None
        self.taskHandleB = None
        self.taskHandleC = None
	
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
		processed_data = []
        
		channels = data.keys()
		channel_list = [float(i) for i in range(8)]
        
		
		self.numSamples = len(data[channels[0]]['Value'])
		
        
		for channel in channel_list:
			if channel in channels:
				processed_data.append(data[channel]['Value'])   #Note - we want to make a 2D array - so replace extend by append
			else:
				processed_data.append(np.zeros(self.numSamples).tolist())
                
		return np.array(processed_data)
        
    def insert_ramps(self, data_dict): #input is dictionary of {Channel: {Time:[], Ramp:[], Value:[]}} 
        channels = data_dict.keys()
        for channel in channels: #remove the last element
            timesch = data_dict[channel]['Time'] 
            rampsch = data_dict[channel]['Ramp']
            valuesch = data_dict[channel]['Value'] 
            timesch =  np.round(np.array(timesch).astype('float')*self.clock_freq).tolist()  #Having some issues with rounding later.. Divide by clock frequency in the end
                        
            values = []
            times = []
        
            for ix2 in range(len(timesch)):
                if ix2 < len(timesch)-1:
                    x =  np.arange(timesch[ix2], timesch[ix2+1],1.0)
    
                    if rampsch[ix2]:
                            slope = (valuesch[ix2+1]-valuesch[ix2])/(timesch[ix2+1]-timesch[ix2])
                            #if slope*self.clock_freq > self.slew_rate:
                            #    print "slope greater than slew rate at time %f." %(timesch[ix2])
                            y_values = (slope*(x-timesch[ix2]) + valuesch[ix2])
                            #if (valuesch[ix2+1]-valuesch[ix2])> self.min_delta_V:
                            #    print "card lacks resolution for voltage step at time %f." %(timesch[ix2])
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


            data_dict[channel]['Time']  = times
            data_dict[channel]['Value']  = values
        
        return data_dict
            
    
    @setting(20,"start", card = 's')
    def start(self, c, card): #Start with software
        if card == 'A':
            if getattr(self, 'taskHandleA', None) is not None:
                self._check( self.nidaq.DAQmxStartTask(self.taskHandleA) )
               
                
        elif card == 'B':
            if getattr(self, 'taskHandleB', None) is not None:
                self._check( self.nidaq.DAQmxStartTask(self.taskHandleB) )
                                
        elif card == 'C':
            if getattr(self, 'taskHandleC', None) is not None:
                self._check( self.nidaq.DAQmxStartTask(self.taskHandleC) )
                
    @setting(21,"done")
    def done(self, c): #Check if task is done
        #WAIT FOR SOME TIME BEFORE IT IS PROGRAMMED
        #time.sleep(0.75)#wait 500 ms. Temporary. Check if programming is done in future.... 
        if getattr(self, 'taskHandleA', None) is not None:
            self._check( self.nidaq.DAQmxWaitUntilTaskDone(self.taskHandleA, float64(-1)) )       
        
            
    @setting(22,"program", card = 's', data_dict = 's')
    def program(self, c, card, data_dict):        
               
        data = self.process_data(eval(data_dict))
        # first, cleanup any old tasks
        self.cleanupTask(c, card) 
        if card == 'A':
               self.taskHandleA = TaskHandle(0)
               self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandleA)) )
               self._check(
                    self.nidaq.DAQmxCreateAOVoltageChan(
                    self.taskHandleA,
                    channel_string_A,     # physicalChannel
                    "",                 # nameToAssignChannel
                    float64(-1.0),     # min output V  
                    float64(1.0),      # max output V
                    DAQmx_Val_Volts,    # units
                    None)               # customScaleName               
                )

               self._check(
                    self.nidaq.DAQmxSetAODataXferMech(
                        self.taskHandleA,
                        "",        #channel
                        int32(DAQmx_Val_Interrupts),        #Mode
                    )
                )
            
#               self._check(
#                        self.nidaq.DAQmxSetAOUseOnlyOnBrdMem(
#                            self.taskHandleA,
#                            "",        #channel
#                            True,        #Mode
#                        )
#                    ) 
               self._check(
                   self.nidaq.DAQmxCfgSampClkTiming(
                   self.taskHandleA,
                   clock_source_A, #source
                   float64(self.sampleRate), # rate
                   DAQmx_Val_Rising, #activeEdge
                   DAQmx_Val_FiniteSamps, #sampleMode # Finite sampling
                   uInt64(self.numSamples) #numSamples
                   )
                  )
            
			
		# Send Clock of this board to other NI cards    
               self._check( self.nidaq.DAQmxExportSignal(
                   self.taskHandleA,
                   DAQmx_Val_SampleClock, #Signal ID
                   '/AO_A/RTSI1'            
                   ))
				
			
               self._check( self.nidaq.DAQmxExportSignal(
                   self.taskHandleA,
                   DAQmx_Val_StartTrigger, #Signal ID
                   '/AO_A/RTSI6,/AO_A/PFI6' #PFI6 has a direct connection            
                   ))

               self._check(
                   self.nidaq.DAQmxWriteAnalogF64(
                   self.taskHandleA,
                   int32(self.numSamples), #numSampsPerChan
                   0, #autoStart
                   float64(30.0), #timeout
                   DAQmx_Val_GroupByChannel, #dataLayout
                   data.ctypes.data,  #writeArray[]
                   byref(self.sampsPerChanWritten), #sampsPerChanWritten
                   None) #reserved
                 )
            
			
			
        if card == 'B':
            self.taskHandleB = TaskHandle(0)
            self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandleB)) )
        
            self._check(
                self.nidaq.DAQmxCreateAOVoltageChan(
                    self.taskHandleB,
                    channel_string_B,     # physicalChannel
                    "",                 # nameToAssignChannel
                    float64(-5.0),     # min output V  
                    float64(5.0),      # max output V
                    DAQmx_Val_Volts,    # units
                    None)               # customScaleName               
                )
                
            self._check(
                    self.nidaq.DAQmxSetAODataXferMech(
                        self.taskHandleB,
                        "",        #channel
                        int32(DAQmx_Val_Interrupts),        #Mode
                    )
                )    
            self._check(
                self.nidaq.DAQmxCfgDigEdgeStartTrig(
                    self.taskHandleB,
                    trigger_source_B,         # source
                    DAQmx_Val_Rising)       # active edge
                )
        
            self._check(
                self.nidaq.DAQmxCfgSampClkTiming(
                self.taskHandleB,
                clock_source_B, #source
                float64(self.sampleRate), # rate
                DAQmx_Val_Rising, #activeEdge
                DAQmx_Val_FiniteSamps, #sampleMode # continuous sampling
                uInt64(self.numSamples) #numSamples
                )
            )
            
                       
                   
            self._check(
                self.nidaq.DAQmxWriteAnalogF64(
                    self.taskHandleB,
                    int32(self.numSamples), #numSampsPerChan
                    0, #autoStart
                    float64(30.0), #timeout
                    DAQmx_Val_GroupByChannel, #dataLayout
                    data.ctypes.data,  #writeArray[]
                    byref(self.sampsPerChanWritten), #sampsPerChanWritten
                    None) #reserved
                )
            #print(self.sampsPerChanWritten)
            
        
        if card == 'C':
            self.taskHandleC = TaskHandle(0)
            self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandleC)) )
    
            self._check(
                self.nidaq.DAQmxCreateAOVoltageChan(
                    self.taskHandleC,
                    channel_string_C,     # physicalChannel
                    "",                 # nameToAssignChannel
                    float64(-10.0),     # min output V  
                    float64(10.0),      # max output V
                    DAQmx_Val_Volts,    # units
                    None)               # customScaleName               
                )

            self._check(
                    self.nidaq.DAQmxSetAODataXferMech(
                        self.taskHandleC,
                        "",        #channel
                        int32(DAQmx_Val_Interrupts),        #Mode
                    )
                )
                    
            self._check(
                self.nidaq.DAQmxCfgDigEdgeStartTrig(
                    self.taskHandleC,
                    trigger_source_C,         # source
                    DAQmx_Val_Rising)       # active edge
                )
    
            self._check(
                self.nidaq.DAQmxCfgSampClkTiming(
                self.taskHandleC,
                clock_source_C, #source
                float64(self.sampleRate), # rate
                DAQmx_Val_Rising, #activeEdge
                DAQmx_Val_FiniteSamps, #sampleMode # continuous sampling
                uInt64(self.numSamples) #numSamples
                )
            )
             
            self._check(
                self.nidaq.DAQmxWriteAnalogF64(
                    self.taskHandleC,
                    int32(self.numSamples), #numSampsPerChan
                    0, #autoStart
                    float64(30.0), #timeout
                    DAQmx_Val_GroupByChannel, #dataLayout
                    data.ctypes.data,  #writeArray[]
                    byref(self.sampsPerChanWritten), #sampsPerChanWritten
                    None) #reserved
                )
     
    @setting(8,"stopTask",returns="")
    def stopTask(self, c, card):
        """ clean up aprropriate old tasks, ready to restart """
        
        if card == 'A':
            if getattr(self, 'taskHandleA', None) is not None:
                self._check( 
                            self.nidaq.DAQmxStopTask(self.taskHandleA) 
                            )
        
        
        elif card == 'B': 
            if getattr(self, 'taskHandleB', None) is not None:
                self._check( 
                            self.nidaq.DAQmxStopTask(self.taskHandleB) 
                            )
                
        
        elif card == 'C':
            if getattr(self, 'taskHandleC', None) is not None:
                self._check( 
                            self.nidaq.DAQmxStopTask(self.taskHandleC) 
                            )
                
        
    @setting(9,"cleanupTask",returns="")
    def cleanupTask(self, c, card):
        """ clean up aprropriate old tasks, ready to restart """
        
        if card == 'A':
            if getattr(self, 'taskHandleA', None) is not None:
                self._check( 
                            self.nidaq.DAQmxStopTask(self.taskHandleA) 
                            )
                self._check( 
                            self.nidaq.DAQmxClearTask(self.taskHandleA) 
                            )

            self.taskHandleA = None
        
        
        elif card == 'B': 
            if getattr(self, 'taskHandleB', None) is not None:
                self._check( 
                            self.nidaq.DAQmxStopTask(self.taskHandleB) 
                            )
                self._check( 
                            self.nidaq.DAQmxClearTask(self.taskHandleB) 
                            )
    
            self.taskHandleB = None
        
        
        elif card == 'C':
            if getattr(self, 'taskHandleC', None) is not None:
                self._check( 
                            self.nidaq.DAQmxStopTask(self.taskHandleC) 
                            )
                self._check( 
                            self.nidaq.DAQmxClearTask(self.taskHandleC) 
                            )
    
            self.taskHandleC = None


    def _check(self,err):
        """Checks NI-DAQ error messages, prints results"""
        if err < 0:
            buf_size = 128
            buf = create_string_buffer('\000' * buf_size)
            self.nidaq.DAQmxGetErrorString(err,byref(buf),buf_size)
            raise RuntimeError('NI-DAQ call failed with error %d: %s'%(err,repr(buf.value)))

    
if __name__ == "__main__":
    from labrad import util
    util.runServer(NI6733_AO())
