# Python interface for SpinAPI
# JDT, January 26, 2010

# Here are some useful definitions from spinapi.h. Not sure how to import these directly

##//Defines for start_programming

PULSE_PROGRAM = 0


##//Defines for different pb_inst instruction types


CONTINUE = 0
STOP = 1
LOOP = 2
END_LOOP = 3
JSR = 4
RTS = 5
BRANCH = 6
LONG_DELAY = 7
WAIT = 8
RTI = 9


cmdList = [ "CONTINUE","STOP","LOOP","END_LOOP","JSR","RTS","BRANCH","LONG_DELAY","WAIT","RTI"]
cmdsV = range(10)

cmddict = dict(zip(cmdList,cmdsV))

PARAM_ERROR = -99


####### Don't use these--we dont' really know what they mean
###define ALL_FLAGS_ON  0x1FFFFF
ALL_FLAGS_ON = 0x1FFFFF
###define ONE_PERIOD        0x200000
ONE_PERIOD = 0x200000
###define TWO_PERIOD        0x400000
TWO_PERIOD = 0x400000
###define THREE_PERIOD  0x600000
THREE_PERIOD = 0x600000
###define FOUR_PERIOD       0x800000
FOUR_PERIOD = 0x800000
###define FIVE_PERIOD       0xA00000
FIVE_PERIOD = 0xA00000
###define SIX_PERIOD      0xC00000
SIX_PERIOD = 0xC00000
###define ON                0xE00000
ON = 0xE00000
###########

import math

# ctypes is the library that lets us interface C functions from DLL's
from ctypes import *
# one trick that can keep things from working: you have to use c_double
# around the imported functions that require double arguments... they are
# not automatically cast from floats.

class SpinAPI:

    def __init__(self):
        
        # load the DLL
        self.spinapi = CDLL("spinapi64.dll")

        # define some return types for functions from the API (need to do this when it's not int)
        self.spinapi.pb_get_error.restype = c_char_p
        self.spinapi.pb_status_message.restype = c_char_p

        # define a few constants

        self.clock = 250   # MHz

        self.nEvents = 0   # of events programmed

        self.debug_on = 1
        
        self.loopAddrs = {}

        self.wait_points = []

        self.loop_count = 0

    def connect(self):
        # now we can call functions as spinapi.<function name>(arguments)
        #
        # For example:
        # spinapi.pb_count_boards()
        # will return the number of boards
        self.disconnect()
        num_boards = self.spinapi.pb_count_boards()

        if num_boards == 0:
            self.err( "No board found!" )
            return -1

        if num_boards > 1:
            self.err( "Too many boards! Using first one..." )

        if self.spinapi.pb_select_board(0):
            self.err( "Error selecting board 0" )
            return -1

        # if the board has already been initialized, doing it again will give an error
                
        if self.spinapi.pb_init():
            self.err( "Error initializing board" )
            return -1

        self.spinapi.pb_set_clock(c_double(self.clock))

        return 0

    def disconnect(self):
        self.spinapi.pb_stop()
        self.spinapi.pb_close()

        return 0

    def reset(self):
        #after reset it takes 8 clock cycles to start again after trigger (32 ns)
        self.loopAddrs = {}

        self.wait_points = []
        self.wait_branch = False

    def program(self, loops, states, delays):
        # Use first/ last state when waiting..... 
        first_state = states[0]
        last_state = states[-1]
        ret = self.spinapi.pb_start_programming(c_int(PULSE_PROGRAM))
        self.debug( "Starting programming... " + str(ret) )
        branch_at_end = True
        waittime = 5.0/(self.clock)
        reset_waittime = 8.0/(self.clock)
        min_delay = 6.0/(self.clock)
        
        self.wait_branch_ret = self.progEvent(first_state,50) #22 ns looks like the minimum value for the progWait to work 
        self.progWait(first_state,100)
        self.nEvents = 2 # 2 instructions programmed upto this point
                
        for ix,loop in enumerate(loops):
            
            if loop != 0:
                if loops[ix+1:].count(loop) == 1:
                    self.progLoopStart(states[ix],22,int(delays[ix]),loop) #int because the delays are floats otherwise . ALso, 22 is again the smallest instruction time
                    
                else:
                    self.progLoopStop(states[ix],22,loop) #ENDLOOP is showing error in the debug print, but the waveform output seems fine ? Keep an eye out for this
                
            else:
                this_delay = delays[ix]
                this_state = states[ix]
                
                if this_delay < 24:
                    print("Warning ! Pulse shorter than 24 ns")
					
                    continue
                 #The value of the Delay Count field (a 32-bit value) determines how long the current instruction
                #should be executed. The allowed minimum value of this field is 0x00000002 for the 4k and
                #0x00000006 for the 32k models, and the allowed maximum is 0xFFFFFFFF. The timing controller
                # has a fixed delay of three clock cycles and the value that one enters into the Delay Count field should
                #account for this inherent delay (12 ns for Rydberg lab).
                    
                if this_delay > 1000: #technically it is (2.0**8/clock)

                                       
                    delay_cycle_length = 500  # chop off to fit into regular delays and continues.
                    
                    delay_cycles = int(math.floor(this_delay / delay_cycle_length)) # number of complete cycles.
    
                    # have to use at least two delay cycles, but since we might subtract one later, be sure that there
                    # are at least 3 at this stage
                    if delay_cycles < 4:
                        delay_cycle_length = 250
                        delay_cycles = int(math.floor(this_delay / delay_cycle_length))
    
                    # the number of cycles must be less than 2**20
                    if (delay_cycles > pow(2,20)):
                        self.debug( "Need to use multiple delay sequences... this_delay=%d" % int(this_delay) )
                        delay_cycles=pow(2,20)-1
    
                    # we should also be sure we don't program a zero-length instruction afterwards
                    if (this_delay - (delay_cycles*delay_cycle_length) < 24):
                        delay_cycles -= 1
    
                    # have to use at least two delay cycles
                    if delay_cycles >= 2:
                        self.progDelay(this_state,delay_cycles,delay_cycle_length)                        
                        this_delay -= delay_cycles * delay_cycle_length
                
                
                self.progEvent(this_state,this_delay)
        
        
        
        self.progBranch(last_state,22,self.wait_branch_ret)   
        
        #Though this should work without the above command, the pulseblaster seems to have memory of the previous sequence. 
        #This will make sure that the instruction goes back to the right place...
        
        ret = self.spinapi.pb_stop_programming()
        self.debug( "Stopping programming... " + str(ret) )
        
        
    def progEvent(self,state,length):
        ret = self.spinapi.pb_inst_pbonly(c_uint(state), CONTINUE, 0, c_double(length))
        self.debug( str(ret) + ": state=" + str(state) + ", length=" + str(length) )
        if ret < 0:
            self.err( self.spinapi.pb_get_error() )
            
        self.nEvents += 1
        return ret

    def progStop(self,state):
        # I'm not sure what the last argument does for a STOP command, but we get an error if it's 0
        ret = self.spinapi.pb_inst_pbonly(c_uint(state), STOP, 0, c_double(100.0))
        self.debug( str(ret) + ": stopped on state=" + str(state) )
        if ret < 0:
            self.err( self.spinapi.pb_get_error() )

        self.nEvents += 1

    def progDelay(self,state,delay_cycles,delay_cycle_length):
        ret = self.spinapi.pb_inst_pbonly(c_uint(state), LONG_DELAY, c_int(delay_cycles), c_double(delay_cycle_length) )
        self.debug( str(ret) + ": added " + str(delay_cycles) + " delay cycles of " + str(delay_cycle_length) + " ns length.")
        if ret < 0:
            self.err( self.spinapi.pb_get_error() )

        self.nEvents += 1
        return ret

    def progLoopStart(self,state,length,loop_count,loop_name):
        ret = self.spinapi.pb_inst_pbonly(c_uint(state), LOOP, c_int(loop_count), c_double(length))
        self.debug( str(ret) + ": state=" + str(state) + ", length=" + str(length) + ", starting loop " + str(loop_name) + " with " + str(loop_count) + " cycles." )
        if ret < 0:
            self.err( self.spinapi.pb_get_error() )

        self.nEvents += 1
        self.loopAddrs[loop_name] = ret
        

    def progLoopStop(self,state,length,loop_name):
        ret = self.spinapi.pb_inst_pbonly(c_uint(state), END_LOOP, c_int(self.loopAddrs[loop_name]), c_double(length))
        self.debug( str(ret) + ": state=" + str(state) + ", length=" + str(length) + ", ending loop " + str(self.loopAddrs[loop_name]) + "." )

        if ret < 0:
            self.err( self.spinapi.pb_get_error() )
        #else:
        #    self.err("Tried to end loop that hadn't started: " + repr(loop_name))
            
        self.nEvents += 1
        
    def progWait(self,state,length):
        ret = self.spinapi.pb_inst_pbonly(c_uint(state), WAIT, 0, c_double(length))
        self.debug( str(ret) + " (WAIT): state=" + str(state) + ", length=" + str(length) )
        if ret < 0:
            self.err( self.spinapi.pb_get_error() )
            
        self.nEvents += 1

        return ret

    def progBranch(self,state,length,addr):
        ret = self.spinapi.pb_inst_pbonly(c_uint(state), BRANCH, addr, c_double(length))
        self.debug( str(ret) + " (Branch to " + str(addr) + "): state=" + str(state) + ", length=" + str(length) )
        if ret < 0:
            self.err( self.spinapi.pb_get_error() )
            
        self.nEvents += 1
        return ret

    def setupWait(self,time,loop):
        self.wait_points.append( time )
        self.wait_branch = loop
        self.wait_branch_ret = 0


    def start(self):
        ret = self.spinapi.pb_start()
        print "Starting... " + str(ret)

    def stop(self):
        ret = self.spinapi.pb_stop()
        print "Stopping... " + str(ret)

    def debug(self,msg):
        if self.debug_on:
            print msg

    def err(self,msg):
        print "ERROR: " + msg

  
