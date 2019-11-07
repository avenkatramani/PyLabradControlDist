# origin: JDT 7/10
# Aditya 6/16
"""
### BEGIN NODE INFO
[info]
name = nicounter
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

##############

# Default data transfer mechanism is DMA. Using default for now. Change it to interrupts if there is any problems. In the Labview program, one is DMA and the other three and Interrupts

##############


from labrad import types as T
from labrad.server import LabradServer, setting

from ctypes import *
import numpy
import math

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

DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171

DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_HWTimedSinglePoint = 12522

DAQmx_Val_CountUp = 10128
DAQmx_Val_CountDown = 10124


DAQmx_Val_DMA	= 10054	
DAQmx_Val_Interrupts	= 10204
DAQmx_Val_ProgrammedIO	= 10264
DAQmx_Val_USBbulk	 = 12590	


#############

counter0_channel = "Dev6/Ctr0"
input0_channel = "/Dev6/PFI39"
clock0_channel = "/Dev6/PFI38"

counter1_channel = "Dev6/Ctr1"
input1_channel = "/Dev6/PFI35"
clock1_channel = "/Dev6/PFI38"

counter2_channel = "Dev6/Ctr2"
input2_channel = "/Dev6/PFI31"
clock2_channel = "/Dev6/PFI38"

counter3_channel = "Dev6/Ctr3"
input3_channel = "/Dev6/PFI27"
clock3_channel = "/Dev6/PFI38"


class NI_Counter(LabradServer):
    """NI Counter Server"""

    name="nicounter"
    nidaq = windll.nicaiu

    password=""

   
    def initServer(self):
        
        self.DMACount = 0 # Only 3 DMA per card. So when a fourth channel is initialized, use interrupts
        self.sample_buffer_len = 200
        
        
    def stopServer(self):
        self.cleanupTask(0, 0)
        self.cleanupTask(0, 1)
        self.cleanupTask(0, 2)
        self.cleanupTask(0, 3)
       
    @setting(2,"setupCounter", counter_number="w",returns="")
    def setupCounter(self, c, counter_number = 0):

        if counter_number == 0 :
            self.cleanupTask(0, 0)
            self.taskHandle0 = TaskHandle(0)
            self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle0)) )
            self.createCounterChannel('taskHandle0', counter0_channel)
            self.cfgSampleClkTiming('taskHandle0', clock0_channel)
            self.setXferMech('taskHandle0', counter0_channel)
            self.buf0 = numpy.zeros( self.sample_buffer_len, dtype=uInt32 )
            
        elif counter_number == 1 :
            self.cleanupTask(0, 1)
            self.taskHandle1 = TaskHandle(0)
            self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle1)) )
            self.createCounterChannel('taskHandle1', counter1_channel)
            self.cfgSampleClkTiming('taskHandle1', clock1_channel)
            self.setXferMech('taskHandle1', counter1_channel)
            self.buf1 = numpy.zeros( self.sample_buffer_len, dtype=uInt32 )
            
        elif counter_number == 2 :
            self.cleanupTask(0, 2)
            self.taskHandle2 = TaskHandle(0)
            self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle2)) )
            self.createCounterChannel('taskHandle2', counter2_channel)
            self.cfgSampleClkTiming('taskHandle2', clock2_channel)
            self.setXferMech('taskHandle2', counter2_channel)
            self.buf2 = numpy.zeros( self.sample_buffer_len, dtype=uInt32 )
            
        elif counter_number == 3 :
            self.cleanupTask(0, 3)
            self.taskHandle3 = TaskHandle(0)
            self._check( self.nidaq.DAQmxCreateTask("",byref(self.taskHandle3)) )
            self.createCounterChannel('taskHandle3', counter3_channel)
            self.cfgSampleClkTiming('taskHandle3', clock3_channel)
            self.setXferMech('taskHandle3', counter3_channel)
            self.buf3 = numpy.zeros( self.sample_buffer_len, dtype=uInt32 )
    
        
    @setting(3,"startCounter",returns="")
    def startCounter(self,c, counter_number):
        if counter_number == 0 :
            self._check(self.nidaq.DAQmxStartTask(self.taskHandle0))
            
        elif counter_number == 1 :
            self._check(self.nidaq.DAQmxStartTask(self.taskHandle1))
            
        elif counter_number == 2 :
            self._check(self.nidaq.DAQmxStartTask(self.taskHandle2))
            
        elif counter_number == 3 :
            self._check(self.nidaq.DAQmxStartTask(self.taskHandle3))
            
    @setting(4,"stopCounter",returns="")
    def stopCounter(self,c, counter_number):
        if counter_number == 0 :
            self._check(self.nidaq.DAQmxStopTask(self.taskHandle0))
            
        elif counter_number == 1 :
            self._check(self.nidaq.DAQmxStopTask(self.taskHandle1))
            
        elif counter_number == 2 :
            self._check(self.nidaq.DAQmxStopTask(self.taskHandle2))
            
        elif counter_number == 3 :
            self._check(self.nidaq.DAQmxStopTask(self.taskHandle3)) 
        

    @setting(5,"readCounter", counter_number="w", returns="*w")
    def readCounter(self,c, counter_number):
        self.read = uInt32(0)
        if counter_number == 0 :
            if getattr(self, 'taskHandle0', None) is not None:
                self._check(
                    self.nidaq.DAQmxReadCounterU32(
                        self.taskHandle0,
                        -1,     # numSampsPerChan, read all samples in buffer 
                        float64(1.0),           # timeout
                        self.buf0.ctypes.data,        # readArray[]
                        self.sample_buffer_len,                   # arraySizeInSamps
                        byref(self.read),            # sampsRead
                        None
                    )
                )
                return(self.buf0)
            
        elif counter_number == 1 :
            if getattr(self, 'taskHandle1', None) is not None:
                self._check(
                    self.nidaq.DAQmxReadCounterU32(
                        self.taskHandle1,
                        -1,     # numSampsPerChan, read all samples in buffer 
                        float64(1.0),           # timeout
                        self.buf1.ctypes.data,        # readArray[]
                        self.sample_buffer_len,                   # arraySizeInSamps
                        byref(self.read),            # sampsRead
                        None
                    )
                )
                return(self.buf1)
                
               
        elif counter_number == 2 :
            if getattr(self, 'taskHandle2', None) is not None:
                self._check(
                    self.nidaq.DAQmxReadCounterU32(
                        self.taskHandle2,
                        -1,     # numSampsPerChan, read all samples in buffer 
                        float64(1.0),           # timeout
                        self.buf2.ctypes.data,        # readArray[]
                        self.sample_buffer_len,                   # arraySizeInSamps
                        byref(self.read),            # sampsRead
                        None
                    )
                )
                return(self.buf2)
                
        elif counter_number == 3 :
            if getattr(self, 'taskHandle3', None) is not None:
                self._check(
                    self.nidaq.DAQmxReadCounterU32(
                        self.taskHandle3,
                        -1,     # numSampsPerChan, read all samples in buffer 
                        float64(1.0),           # timeout
                        self.buf3.ctypes.data,        # readArray[]
                        self.sample_buffer_len,                   # arraySizeInSamps
                        byref(self.read),            # sampsRead
                        None
                    )
                )
                return(self.buf3)
                
            
   

    @setting(9,"cleanupTask",counter_number = "w", returns="")
    def cleanupTask(self,c, counter_number):
        """ clean up old task, ready to restart """
    
        if counter_number == 0:
            if getattr(self, 'taskHandle0', None) is not None:
                transferType = self.getXferMech('taskHandle0', counter0_channel)
                if transferType == DAQmx_Val_DMA:
                    self.DMACount -= 1
                self._check( self.nidaq.DAQmxStopTask(self.taskHandle0) )
                self._check( self.nidaq.DAQmxClearTask(self.taskHandle0) )
                self.taskHandle0 = None
                
        elif counter_number == 1:    
            if getattr(self, 'taskHandle1', None) is not None:
                transferType = self.getXferMech('taskHandle1', counter1_channel)
                if transferType == DAQmx_Val_DMA:
                    self.DMACount -= 1
                self._check( self.nidaq.DAQmxStopTask(self.taskHandle1) )
                self._check( self.nidaq.DAQmxClearTask(self.taskHandle1) )
                self.taskHandle1 = None
                
        elif counter_number == 2:    
            if getattr(self, 'taskHandle2', None) is not None:
                transferType = self.getXferMech('taskHandle2', counter2_channel)
                if transferType == DAQmx_Val_DMA:
                    self.DMACount -= 1
                self._check( self.nidaq.DAQmxStopTask(self.taskHandle2) )
                self._check( self.nidaq.DAQmxClearTask(self.taskHandle2) )
                self.taskHandle2 = None
                
        elif counter_number == 3:    
            if getattr(self, 'taskHandle3', None) is not None:
                transferType = self.getXferMech('taskHandle3', counter3_channel)
                if transferType == DAQmx_Val_DMA:
                    self.DMACount -= 1
                self._check( self.nidaq.DAQmxStopTask(self.taskHandle3) )
                self._check( self.nidaq.DAQmxClearTask(self.taskHandle3) )
                self.taskHandle3 = None
       


    def createCounterChannel(self, taskHandle, counter_channel):
        self._check(
                self.nidaq.DAQmxCreateCICountEdgesChan(
                    getattr(self,taskHandle),
                    counter_channel,        # const char counter[]
                    "",                     # const char nameToAssignToChannel[]
                    DAQmx_Val_Rising,       # edge
                    0,                      # initialCount
                    DAQmx_Val_CountUp       # countDirection
                )
            )
        
    
    def setXferMech(self, taskHandle, counter_channel):
        if self.DMACount < 3:
            self._check(
                self.nidaq.DAQmxSetCIDataXferMech(
                    getattr(self,taskHandle),
                    counter_channel,        #channel
                    int32(DAQmx_Val_DMA),        #Mode
                )
            )
            self.DMACount += 1
            
        else:
            self._check(
                self.nidaq.DAQmxSetCIDataXferMech(
                    getattr(self,taskHandle),
                    counter_channel,        #channel
                    int32(DAQmx_Val_Interrupts),        #Mode
                )
            )
            
     
    def getXferMech(self, taskHandle, counter_channel):
        transferType = int32(0)
        self._check(
            self.nidaq.DAQmxGetCIDataXferMech(
                getattr(self,taskHandle),
                counter_channel,        #channel
                byref(transferType),        #Mode
            )
        )
        return transferType.value 
            
            
            
    def cfgSampleClkTiming(self, taskHandle, clock_channel):
        self._check(
                self.nidaq.DAQmxCfgSampClkTiming(
                    getattr(self,taskHandle),
                    clock_channel,        # source[]
                    float64(1000000.0),        # using 1 MHz to be a large value
                    DAQmx_Val_Rising,       # edge
                    DAQmx_Val_ContSamps,    # mode
                    uInt64(self.sample_buffer_len)            # sampsPerCHan
                )
            )
        
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
    util.runServer(NI_Counter())

    

