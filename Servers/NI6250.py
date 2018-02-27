# origin: JDT 7/10
# Aditya 2/17
"""
### BEGIN NODE INFO
[info]
name = ni6250
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
import numpy
import threading, time, struct
import os
from ctypes import *


########### nidaq.h types and constants
# set up c type names
int16 = c_short
uInt16 = c_ushort
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

#############

############# AOServer settings
sampleRate = 1e6
# could use 8, but 4 will be faster for now
#numChannels = 4
#channel_string = "Dev1/ao0:3"
numChannels = 8
channel_string = "Dev3/ao0:7"
trigger_source = "/Dev3/PFI0"
monitor_channel_string = "Dev3/ai1"
dev_str = "Dev3"
monitor_num_channels = 1
monitor_rate = 1e3
scale=10.0/(2**15)
#############

class NI6250_Server(LabradServer):
    """Analog output server"""

    name="ni6250"
    nidaq = windll.nicaiu

    password=""

    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data
		
	    # this is just a test
    @setting(10,"ProcessID_str", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return os.getpid()

    def initServer(self):
        #self.nWritten = c_long(0)
        #self.thresh = [ [-11,11] for x in range(8) ]
        pass

    def stopServer(self):
        # be sure to stop whatever task is active
        self.cleanupTask(c)

    # exported to the main server
    # v value, w integer, s string, etc...
    
    @setting(2,"setStaticVoltage",ch="w",v="v",returns="")
    def setStaticVoltage(self,c,ch,v):
        """ set static voltage v on the channel ch """
        # initialize NI-DAQ

        self.dataSingle = numpy.zeros(1, dtype=float64)
        self.dataSingle[0] = v['V']
        
        self.nWrittenSingle = c_long(0)

        # first, cleanup any old tasks
        self.cleanupTask(c)

        # now setup the new task
        self.taskHandle = TaskHandle(0)

        # int32 __CFUNC     DAQmxCreateTask                (const char taskName[], TaskHandle *taskHandle);
        self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle)) )

        # int32 __CFUNC     DAQmxCreateAOVoltageChan       (TaskHandle taskHandle, const char physicalChannel[], const char nameToAssignToChannel[], float64 minVal, float64 maxVal, int32 units, const char customScaleName[]);
        self._check(
            self.nidaq.DAQmxCreateAOVoltageChan(
                self.taskHandle,
                dev_str+"/ao"+repr(int(ch)),     # physicalChannel
                "",                 # nameToAssignChannel
                float64(-10.0),     # min output V
                float64(10.0),      # max output V
                DAQmx_Val_Volts,    # units
                None)               # customScaleName               
            )

        self._check(
            self.nidaq.DAQmxStartTask(self.taskHandle)
            )

        # int32 __CFUNC     DAQmxWriteAnalogF64            (TaskHandle taskHandle, int32 numSampsPerChan, bool32 autoStart, float64 timeout, bool32 dataLayout, const float64 writeArray[], int32 *sampsPerChanWritten, bool32 *reserved);
        self._check(
            self.nidaq.DAQmxWriteAnalogF64(
                self.taskHandle,
                int32(1),                       # numSampsPerChan
                1,                              # autoStart
                float64(10.0),                  # timeout
                DAQmx_Val_GroupByChannel,       # dataLayout
                self.dataSingle.ctypes.data,    # writeArray[]
                byref(self.nWrittenSingle),     # *sampsPerChanWritten
                None)                           # *reserved
            )

    @setting(3,"getStaticVoltage",ch="w",returns="v")
    def getStaticVoltage(self,c,ch):
        """ get static voltage from the channel ch """
        # initialize NI-DAQ

        self.dataSingle = numpy.zeros(1, dtype=float64)
       # self.dataSingle[0] = v['V']
        
        self.nReadSingle = c_long(0)

        # first, cleanup any old tasks
        self.cleanupTask(c)

        # now setup the new task
        self.taskHandle = TaskHandle(0)

        # int32 __CFUNC     DAQmxCreateTask                (const char taskName[], TaskHandle *taskHandle);
        self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle)) )

        # int32 __CFUNC     DAQmxCreateAIVoltageChan       (TaskHandle taskHandle, const char physicalChannel[], const char nameToAssignToChannel[],
        #                                                   int32 terminalConfig, float64 minVal, float64 maxVal, int32 units, const char customScaleName[]);

        self._check(
            self.nidaq.DAQmxCreateAIVoltageChan(
                self.taskHandle,
                dev_str+"/ai"+repr(int(ch)),     # physicalChannel
                "",                 # nameToAssignChannel
                DAQmx_Val_Cfg_Default,    # terminal configuration
                float64(-10.0),     # min output V
                float64(10.0),      # max output V
                DAQmx_Val_Volts,    # units
                None)               # customScaleName               
            )

        self._check(
            self.nidaq.DAQmxStartTask(self.taskHandle)
            )

        # int32 __CFUNC     DAQmxReadAnalogF64             (TaskHandle taskHandle, int32 numSampsPerChan, float64 timeout, bool32 fillMode, float64 readArray[],
        #                                                   uInt32 arraySizeInSamps, int32 *sampsPerChanRead, bool32 *reserved);
        self._check(
            self.nidaq.DAQmxReadAnalogF64(
                self.taskHandle,
                int32(1),                       # numSampsPerChan
                float64(10.0),                  # timeout
                DAQmx_Val_GroupByChannel,       # dataLayout
                self.dataSingle.ctypes.data,    # readArray[]
                1,                      # arraySizeInSamps
                byref(self.nReadSingle),        # *sampsPerChanWritten
                None)                           # *reserved
            )
        return self.dataSingle[0]
    
    @setting(4,"setStaticVoltageArray",v="*v",returns="")
    def setStaticVoltageArray(self,c,v):
        """ set static voltages v[] on all 8 channels """
        # initialize NI-DAQ
        if len(v) is not 2:
            print "Error: array is the wrong length! Quitting..."
            return -1

        self.dataSingle = numpy.zeros(2, dtype=float64)
        for i in range(0,2):
            self.dataSingle[i] = v[i]['V']
        
        self.nWrittenSingle = c_long(0)

        # first, cleanup any old tasks
        self.cleanupTask(c)

        # now setup the new task
        self.taskHandle = TaskHandle(0)

        # int32 __CFUNC     DAQmxCreateTask                (const char taskName[], TaskHandle *taskHandle);
        self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle)) )

        # int32 __CFUNC     DAQmxCreateAOVoltageChan       (TaskHandle taskHandle, const char physicalChannel[], const char nameToAssignToChannel[], float64 minVal, float64 maxVal, int32 units, const char customScaleName[]);
        self._check(
            self.nidaq.DAQmxCreateAOVoltageChan(
                self.taskHandle,
                dev_str+"/ao0:1",       # physicalChannel
                "",                 # nameToAssignChannel
                float64(-10.0),     # min output V
                float64(10.0),      # max output V
                DAQmx_Val_Volts,    # units
                None)               # customScaleName               
            )

        self._check(
            self.nidaq.DAQmxStartTask(self.taskHandle)
            )

        # int32 __CFUNC     DAQmxWriteAnalogF64            (TaskHandle taskHandle, int32 numSampsPerChan, bool32 autoStart, float64 timeout, bool32 dataLayout, const float64 writeArray[], int32 *sampsPerChanWritten, bool32 *reserved);
        self._check(
            self.nidaq.DAQmxWriteAnalogF64(
                self.taskHandle,
                int32(1),                       # numSampsPerChan
                1,                              # autoStart
                float64(10.0),                  # timeout
                DAQmx_Val_GroupByChannel,       # dataLayout
                self.dataSingle.ctypes.data,    # writeArray[]
                byref(self.nWrittenSingle),     # *sampsPerChanWritten
                None)                           # *reserved
            )
        
    @setting(5,"getStaticVoltageArray",returns="*v")
    def getStaticVoltageArray(self,c):
        """ get static voltage from the channel ch """
        # initialize NI-DAQ

        self.dataSingle = numpy.zeros(16, dtype=float64)
       # self.dataSingle[0] = v['V']
        
        self.nReadSingle = c_long(0)

        # first, cleanup any old tasks
        self.cleanupTask(c)

        # now setup the new task
        self.taskHandle = TaskHandle(0)

        # int32 __CFUNC     DAQmxCreateTask                (const char taskName[], TaskHandle *taskHandle);
        self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle)) )

        # int32 __CFUNC     DAQmxCreateAIVoltageChan       (TaskHandle taskHandle, const char physicalChannel[], const char nameToAssignToChannel[],
        #                                                   int32 terminalConfig, float64 minVal, float64 maxVal, int32 units, const char customScaleName[]);

        self._check(
            self.nidaq.DAQmxCreateAIVoltageChan(
                self.taskHandle,
                dev_str+"/ai0:15",      # physicalChannel
                "",                 # nameToAssignChannel
                DAQmx_Val_Cfg_Default,    # terminal configuration
                float64(-10.0),     # min output V
                float64(10.0),      # max output V
                DAQmx_Val_Volts,    # units
                None)               # customScaleName               
            )

        self._check(
            self.nidaq.DAQmxStartTask(self.taskHandle)
            )

        # int32 __CFUNC     DAQmxReadAnalogF64             (TaskHandle taskHandle, int32 numSampsPerChan, float64 timeout, bool32 fillMode, float64 readArray[],
        #                                                   uInt32 arraySizeInSamps, int32 *sampsPerChanRead, bool32 *reserved);
        self._check(
            self.nidaq.DAQmxReadAnalogF64(
                self.taskHandle,
                int32(1),                       # numSampsPerChan
                float64(10.0),                  # timeout
                DAQmx_Val_GroupByChannel,       # dataLayout
                self.dataSingle.ctypes.data,    # readArray[]
                16,                             # arraySizeInSamps
                byref(self.nReadSingle),        # *sampsPerChanWritten
                None)                           # *reserved
            )
        return self.dataSingle

 


    @setting(9,"cleanupTask",returns="")
    def cleanupTask(self,c):
        self._cleanupTask()

    def _cleanupTask(self):
        """ clean up old task, ready to restart """
        
        if getattr(self, 'taskHandle', None) is not None:
            self._check( self.nidaq.DAQmxStopTask(self.taskHandle) )
            self._check( self.nidaq.DAQmxClearTask(self.taskHandle) )

        if getattr(self, 'taskHandleIn', None) is not None:
            self._check( self.nidaq.DAQmxStopTask(self.taskHandleIn) )
            self._check( self.nidaq.DAQmxClearTask(self.taskHandleIn) )


        self.taskHandle = None
        self.taskHandleIn = None


    def _check_no_ufl(self,err):
        """Checks NI-DAQ error messages, prints results. Ignores if it is underflow error -200284 """
        if err < 0 and err != -200284:
            buf_size = 128
            buf = create_string_buffer('\000' * buf_size)
            # this calls the DAQmx error function; byref(buf) passes a pointer to the string
            self.nidaq.DAQmxGetErrorString(err,byref(buf),buf_size)
            raise RuntimeError('NI-DAQ call failed with error %d: %s'%(err,repr(buf.value)))
        
    def _check(self,err):
        """Checks NI-DAQ error messages, prints results"""
        if err < 0:
            buf_size = 128
            buf = create_string_buffer('\000' * buf_size)
            # this calls the DAQmx error function; byref(buf) passes a pointer to the string
            self.nidaq.DAQmxGetErrorString(err,byref(buf),buf_size)
            raise RuntimeError('NI-DAQ call failed with error %d: %s'%(err,repr(buf.value)))

    
if __name__ == "__main__":
    from labrad import util
    util.runServer(NI6250_Server())
