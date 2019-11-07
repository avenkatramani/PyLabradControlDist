# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 22:07:27 2016

@author: AdityaVignesh
"""

'''
This Server will receive input information for the NI and PulseBlaster cards and 
program them. This will populate the information for all the card, process the data 
and send them to the respective base servers. 

This will recieve inforamtion from the timing server about which sequences and devices to hear from. 
Each time it recieves from a server, it checks if it has recieved everything. Once it has, it breaks 
up the database by cards and send the information to the respective base servers.

'''

"""
### BEGIN NODE INFO
[info]
name = sequenceprogrammer
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
from twisted.internet.defer import  returnValue
import numpy as np
import pandas as pd
import datetime as dt
from multiprocessing.pool import ThreadPool
import time

class Sequence_Programmer_Server(LabradServer):
    
    name = "sequenceprogrammer"
    ID = 123456 
    
    
    def initServer(self):
        
        self.init_index_cards = pd.MultiIndex(levels = [[],[],[],[],[]],
                                   labels = [[],[],[],[],[]],
                                   names = ['Card', 'Number', 'Sequence', 'Channel','Time']) 
        self.init_columns_cards = ['Ramp','Value']
        
        
        self.data_cards = pd.DataFrame(index =self.init_index_cards, columns = self.init_columns_cards)
        
        
        self.init_index_Arduino = pd.MultiIndex(levels = [[],[],[],[]],
                                   labels = [[],[],[],[]],
                                   names = ['port', 'Sequence', 'dev', 'Time']) 
        self.init_columns_Arduino = ['Value']
        
        
        self.data_Arduino = pd.DataFrame(index =self.init_index_Arduino, columns = self.init_columns_Arduino)
        
       
        
        self.received_from = []
        self.receive_list = []
        self.data_subset = {}
        self.cards_loaded = 0
        self.sequence_order_list = []

    @setting(40)
    def clearAll(self, c):
               
        self.init_index_cards = pd.MultiIndex(levels = [[],[],[],[],[]],
                                   labels = [[],[],[],[],[]],
                                   names = ['Card', 'Number', 'Sequence', 'Channel','Time']) 
        self.init_columns_cards = ['Ramp','Value']
        
        
        self.data_cards = pd.DataFrame(index =self.init_index_cards, columns = self.init_columns_cards)
        
        
        
        self.init_index_Arduino = pd.MultiIndex(levels = [[],[],[],[]],
                                   labels = [[],[],[],[]],
                                   names = ['port', 'Sequence', 'dev', 'Time']) 
        self.init_columns_Arduino = ['Value']
        
        self.data_Arduino = pd.DataFrame(index =self.init_index_Arduino, columns = self.init_columns_Arduino)
        
        
        self.received_from = []
        self.receive_list = []
        self.sequence_order_list = []
        
    def make_recieve_list(self, sequences, devices):
        self.receive_list = []
        for sequence in sequences:
            for device in devices:
                self.receive_list.append([sequence, device]) 
        
   
    @setting(2, sequences = 's', devices = '?', sequence_order_list = 's', sequence_length_list='s')
    def update_receive_list(self, c,  sequences, devices, sequence_order_list, sequence_length_list):

        self.cards_loaded = 0
        self.make_recieve_list(eval(sequences), eval(devices))
        self.sequence_length_list = eval(sequence_length_list)
        self.sequence_order_list = eval(sequence_order_list)
        if np.array_equal(np.sort(self.receive_list, 0), np.sort(self.received_from, 0)):
            self.received_from = []
            self.load_cards(c)
            self.load_Arduino(c)

  
    @setting(10, data='s')   
    def Receive_Card_Data(self, c, sequence, device, data): 
    #Expected data to be of the form (Card type(NI/PulseBlaster), Card Number (#A1,A2,A3,D1 for NI), Sequence, Channel #, Time, Ramp, Value) as a pandas database with Card# and Channel # as indices
        if not(sequence ==''):
            self.received_from.append([sequence, device])
        self.data_cards = pd.concat([self.data_cards, pd.DataFrame().from_dict(eval(data))])
        if np.array_equal(np.sort(self.receive_list, 0), np.sort(self.received_from, 0)):
            self.received_from = []
            self.load_cards(c)
            self.load_Arduino(c)
            
    @setting(11, data='s')   
    def Receive_Arduino_Data(self, c, sequence, device, data): 
    #Expected data to be of the form (USB port number, Sequence, some index, values) as a pandas database 
        if not(sequence ==''):
            self.received_from.append([sequence, device])
        self.data_Arduino = pd.concat([self.data_Arduino, pd.DataFrame().from_dict(eval(data))])
        if np.array_equal(np.sort(self.receive_list, 0), np.sort(self.received_from, 0)):
            self.received_from = []
            self.load_cards(c)
            self.load_Arduino(c)

    @setting(25, "load_Arduino")  
    def load_Arduino(self, c) :  
        if not(self.data_Arduino.empty): 
            ports = np.unique(self.data_Arduino.index.get_level_values(0)).tolist()
            dev_list = np.unique(self.data_Arduino.index.get_level_values(2)).tolist()
            for port in ports:
                processed_data = self.process_Arduino_data(self.sequence_order_list, dev_list, self.data_Arduino.xs(port))
                self.client.arduino.arduino_send(port, dev_list, str(processed_data))
        
    ## Return dict {flag: [frequency list]}  
    def process_Arduino_data(self, loop_list, dev_list, data):
        if type(loop_list) == type([]):
            if len(loop_list) == 0:
                processed_data = {}        
                for dev in dev_list:
                    processed_data[dev] = []
                return processed_data
            
            elif len(loop_list) == 1:
                return self.process_Arduino_data(loop_list[0], dev_list, data)           
        
            elif type(loop_list[1]) == type([]):
                processed_data_0 = self.process_Arduino_data(loop_list[0], dev_list, data)
                processed_data_1 = self.process_Arduino_data(loop_list[1:], dev_list, data)
                processed_data = {}        
                for dev in dev_list:
                    processed_data[dev] = processed_data_0[dev] + processed_data_1[dev]
                return processed_data
            
            elif type(loop_list[0]) == type([]):
                processed_data_0 = self.process_Arduino_data(loop_list[0], dev_list, data)
                loops = loop_list[1]
                processed_data = {} 
                for dev in dev_list:
                    processed_data[dev] = processed_data_0[dev] *loops
                return processed_data
                
            else:
                sequence = loop_list[0]
                loops = loop_list[1]
                processed_data = {}  
                
                try:
                    data_sequence = data.xs(sequence)
                    for dev in dev_list:
                        data_dev = data_sequence.xs(dev)
                        columns = np.transpose(data_dev.as_matrix(columns=['Value']))
                        processed_data[dev] = columns[0].tolist()*loops   #The last frequency has already been ignored
                except:
                    for dev in dev_list:
                        processed_data[dev] = []                    
                    
                return processed_data
            

               


    @setting(400, "cards_loaded")  
    def cards_loaded(self, c) : # To start by software
        return self.cards_loaded
        
    @setting(20, "start_cards")  
    def start_cards(self, c) : # To start by software
        # Block each to make sure that each is written            
        self.client.ni6535_digital.start() 
        
        #Start B and C first so that it waits for the trigger from A
        
        self.client.ni6733_ao.start('B') 
        self.client.ni6733_ao.start('C') 
        self.client.ni6733_ao.start('A') 
        
            
		
    @setting(21, "stop_cards")  
    def stop_cards(self, c) : # To stop by software
        
        self.client.ni6535_digital.stoptask()
        self.client.ni6733_ao.stoptask('B')
        self.client.ni6733_ao.stoptask('C')
        self.client.ni6733_ao.stoptask('A')

        
    #The current idea is that the analog card A generates the clock and provides the start trigger to the others 

    @setting(22, "done")  
    def done(self, c) : 
        return self.client.ni6733_ao.done()
		
    @setting(23, "load_cards")  
    def load_cards(self, c) :   #Maybe this is expensive in time. Do it in a deterministic way insted ?
        if not(self.data_cards.empty):
    
            p = ThreadPool()  #Does not really help here....., need to find a way to deal with this. 
            results = {}
            
            try:
                PB_data = self.data_cards.xs('PB') 
                try:
                    PB1_data = PB_data.xs('PB1')
                    results['PB1'] = p.apply_async(self.process_PB_data, args=(PB1_data,))
                except:    
                    pass  
            except:
                 pass            
             
            try:
                NI_data = self.data_cards.xs('NI') 
                try:              
                    NID1_data = NI_data.xs('D1')
                    results['D1'] = p.apply_async(self.process_NI_data, args=(NID1_data,))
                except:    
                    results['D1'] = p.apply_async(self.create_zeros_for_NI) 
                try:
                    NIA1_data = NI_data.xs('A')
                    results['A'] = p.apply_async(self.process_NI_data, args=(NIA1_data,))    
                except:    
                    results['A'] = p.apply_async(self.create_zeros_for_NI) 
                try:
                    NIA2_data = NI_data.xs('B')
                    results['B'] = p.apply_async(self.process_NI_data, args=(NIA2_data,))
                except:    
                    results['B'] = p.apply_async(self.create_zeros_for_NI) 
                try:
                    NIA3_data = NI_data.xs('C')
                    results['C'] = p.apply_async(self.process_NI_data, args=(NIA3_data,))
                except:    
                    results['C'] = p.apply_async(self.create_zeros_for_NI) 
            except:
                results['A'] = p.apply_async(self.create_zeros_for_NI) 
                results['B'] = p.apply_async(self.create_zeros_for_NI) 
                results['C'] = p.apply_async(self.create_zeros_for_NI) 
                results['D1'] = p.apply_async(self.create_zeros_for_NI) 
            
            p.close()
            p.join()
            for card in results.keys():
                if card == 'PB1':
                    [loop_list , instruction_list, delay_list] = results['PB1'].get()
                    self.client.pulseblaster.program(loop_list, instruction_list, delay_list)
                elif card == 'D1':
                    processed_NID1_data = results['D1'].get()
                    self.client.ni6535_digital.program(str(processed_NID1_data)) 
                elif card == 'A':
                    processed_NIA1_data = results['A'].get()
                    self.client.ni6733_ao.program('A', str(processed_NIA1_data))
                elif card == 'B':
                    processed_NIA2_data = results['B'].get()
                    self.client.ni6733_ao.program('B', str(processed_NIA2_data)) 
                elif card == 'C':
                    processed_NIA3_data = results['C'].get()
                    self.client.ni6733_ao.program('C', str(processed_NIA3_data))
                    
            self.cards_loaded = 1
         
         
    def create_zeros_for_NI(self): #insert zeros at appropriate times for channel 0 
        processed_data = {}        
        processed_data[0] = {'Time': [], 'Ramp': [], 'Value': []}    
        stop_time = self.find_stop_time(self.sequence_order_list, 0)
        processed_data[0]['Time'].extend([0, stop_time])
        processed_data[0]['Ramp'].extend([0,0])
        processed_data[0]['Value'].extend([0,0])  
        
        return processed_data
        
    def find_stop_time(self, loop_list, delay):   # Creates a list of values+times for a given loop_item         
        if type(loop_list) == type([]):
            if len(loop_list) == 0:
                return delay
            
            elif len(loop_list) == 1:
                return self.find_stop_time(loop_list[0], delay)           
        
            elif type(loop_list[1]) == type([]):
                new_delay_0 = self.find_stop_time(loop_list[0], delay)
                new_delay_1 = self.find_stop_time(loop_list[1:], new_delay_0)
                return new_delay_1
            
            elif type(loop_list[0]) == type([]):
                new_delay_0 = self.find_stop_time(loop_list[0], 0)  #Careful about the delay here.... Think of this as a grouped sequence
                loops = loop_list[1]  
                new_delay = (loops-1)*new_delay_0
                return delay+new_delay+new_delay_0
                
            else:
                sequence = loop_list[0]
                loops = loop_list[1]
                new_delay = delay+(loops-1)*self.sequence_length_list[sequence] 
                return new_delay+self.sequence_length_list[sequence]
         
      
        
    def process_NI_data(self, data):  
        channel_list = np.unique(data.index.get_level_values(1))  
        processed_data, delay = self.create_NI_value_list(data, self.sequence_order_list, channel_list, 0)  
        

        #Adding last element of last sequence back
        loop_list = self.create_PB_loop_list(self.sequence_order_list)    
        last_sequence = loop_list[-1][0]            
        data_sequence = data.xs(last_sequence)
        
        for channel in channel_list:
            data_channel = data_sequence.xs(channel)
            columns = np.transpose(data_channel.as_matrix(columns=['Ramp','Value']))
            processed_data[channel]['Ramp'].append(columns[0][-1])
            processed_data[channel]['Value'].append(columns[1][-1])  
            processed_data[channel]['Time'].append(delay)
        return processed_data
        
    def create_NI_value_list(self, data, loop_list, channel_list, delay):   # Creates a list of values+times for a given loop_item              
        if type(loop_list) == type([]):
            if len(loop_list) == 0:
                processed_data = {}        
                for channel in channel_list:
                    processed_data[channel] = {}
                    processed_data[channel]['Ramp'] = []
                    processed_data[channel]['Value'] = []
                    processed_data[channel]['Time'] = []
                return processed_data, delay
            
            elif len(loop_list) == 1:
                return self.create_NI_value_list(data, loop_list[0], channel_list, delay)           
        
            elif type(loop_list[1]) == type([]):
                processed_data_0, new_delay_0 = self.create_NI_value_list(data, loop_list[0], channel_list, delay)
                processed_data_1, new_delay_1 = self.create_NI_value_list(data, loop_list[1:], channel_list, new_delay_0)
                processed_data = {}        
                for channel in channel_list:
                    processed_data[channel] = {}
                    processed_data[channel]['Ramp'] = processed_data_0[channel]['Ramp'] + processed_data_1[channel]['Ramp']
                    processed_data[channel]['Value'] = processed_data_0[channel]['Value'] + processed_data_1[channel]['Value']
                    processed_data[channel]['Time'] = processed_data_0[channel]['Time'] + processed_data_1[channel]['Time']
                
                
                return processed_data, new_delay_1
            
            elif type(loop_list[0]) == type([]):
                processed_data_0, new_delay_0 = self.create_NI_value_list(data, loop_list[0], channel_list, 0)  #Careful about the delay here.... Think of this as a grouped sequence
                loops = loop_list[1]
                processed_data = {}        
                for channel in channel_list:
                    processed_data[channel] = {}
                    processed_data[channel]['Ramp'] = processed_data_0[channel]['Ramp'] *loops
                    processed_data[channel]['Value'] = processed_data_0[channel]['Value'] *loops
                    new_delay = (loops-1)*new_delay_0
                    delays = np.repeat(np.linspace(delay, delay+new_delay, loops), len(processed_data[channel]['Value'])/loops)
                    processed_data[channel]['Time'] = (np.tile(np.array(processed_data_0[channel]['Time']), loops) + delays).tolist()

                return processed_data, delay+new_delay+new_delay_0
                
            else:
                sequence = loop_list[0]
                loops = loop_list[1]
                data_sequence = data.xs(sequence)
                processed_data = {}        
                for channel in channel_list:
                    processed_data[channel] = {}
                 
                for channel in channel_list:
                    data_channel = data_sequence.xs(channel)
                    columns = np.transpose(data_channel.as_matrix(columns=['Ramp','Value']))
                    processed_data[channel]['Ramp'] = columns[0][:-1].tolist()*loops
                    processed_data[channel]['Value'] = columns[1][:-1].tolist()*loops  
                    new_delay = delay+(loops-1)*self.sequence_length_list[sequence]
                    delays = np.repeat(np.linspace(delay, new_delay, loops), len(processed_data[channel]['Value'])/loops)
                    processed_data[channel]['Time'] = (np.tile(np.array(data_channel.index.get_level_values(0)[:-1]), loops) + delays).tolist()
                   
                return processed_data, new_delay+self.sequence_length_list[sequence]
         
        
        
        
    
    '''
    
    
    Need to return the format
    
    Loop = [1, 2, 0, 0, 2, 3, 0, 0, 3, 1]
    
    instruction = [0b1111111, 0b1111111, 0b1111111, 0b010110, 0b010110, 0b010110]
    
    delay = [10, 20, 100 - 4, 50 - 4, 0, 0]
    
    
    '''    
        
    def process_PB_data(self, data): 
        
        PB_loop_list = np.array([])
        instruction_list = np.array([])
        delay_list = np.array([])
        loop_list = self.create_PB_loop_list(self.sequence_order_list)
        for i in xrange(len(loop_list)):
                
                sequence = loop_list[i][0]
                data_sequence = data.xs(sequence)
                [delays, instructions] = self.create_PB_sequence_instruction_list(data_sequence)
                [start, stop, repeats] = self.parse_PB_loop_list(i, loop_list)
                
                length = len(delays)
                start_len = len(start)
                stop_len = len(stop)


                if start_len !=0 :
                    start.reverse()
                    PB_loop_list = np.append(PB_loop_list, start)
                else:
                    PB_loop_list = np.append(PB_loop_list, start)
                    
                PB_loop_list = np.append(PB_loop_list, np.zeros(length))
                PB_loop_list = np.append(PB_loop_list, stop)
                
                
                
                instruction_list = np.append(instruction_list, np.repeat(instructions[0], start_len))
                instruction_list = np.append(instruction_list, instructions)
                instruction_list = np.append(instruction_list, np.repeat(instructions[-1], stop_len))
                
                if start_len != 0:   
                    repeats.reverse()
                    delay_list = np.append(delay_list,repeats)
                else:
                    delay_list = np.append(delay_list,repeats)
                    
                
                if len(delays) == 1 and start_len == 0 and stop_len == 0 : 
                    delay_list = np.append(delay_list, delays[0] *1000000000.0) 
                
                elif len(delays) == 1 and start_len == 0 : 
                    delay_list = np.append(delay_list, delays[0]* 1000000000.0 - (2.0)*stop_len)
                    delay_list = np.append(delay_list, np.zeros(stop_len))
                
                elif len(delays) == 1 and stop_len == 0 : 
                    delay_list = np.append(delay_list, delays[0] *1000000000.0 - (2.0)*start_len)
                
                elif len(delays) == 1 : 
                    delay_list = np.append(delay_list, delays[0] *1000000000.0 - (2.0)*(start_len+stop_len))
                    delay_list = np.append(delay_list, np.zeros(stop_len))
                
                else:    
                    delay_list = np.append(delay_list, delays[0] *1000000000.0 - (2.0)*start_len) #Assuming specified in seconds
                    delay_list = np.append(delay_list, delays[1:-1]*1000000000.0)
                    delay_list = np.append(delay_list, delays[-1]* 1000000000.0 - (2.0)*stop_len)
                    delay_list = np.append(delay_list, np.zeros(stop_len))
                
              
        return [PB_loop_list , instruction_list, delay_list]
        

    def parse_PB_loop_list(self, i, loop_list): 
        start = []
        stop = []  
        repeats = []
        loops = loop_list[i][1::]
        if i == 0:
            
            for loop in loops:
                
                if loop[1] != 1:
                    start.append(loop[0])
                    repeats.append(loop[1])
            
                    if len(loop_list) == 1:
                        stop.append(loop[0])
                          
                    elif not(loop in loop_list[i+1][1::]):
                        stop.append(loop[0])
            
            
            
        elif i == len(loop_list)-1:
            for loop in loops:
                if loop[1] != 1:
                    stop.append(loop[0])
        
                    if len(loop_list) == 1:
                        start.append(loop[0])
                        repeats.append(loop[1])
                
                    elif not(loop in loop_list[i-1][1::]):
                        start.append(loop[0])
                        repeats.append(loop[1])
                    
        
        else:
            for loop in loops:
                if loop[1] != 1:
                    if not(loop in loop_list[i-1][1::]):
                        start.append(loop[0])
                        repeats.append(loop[1])
                
                    if not(loop in loop_list[i+1][1::]):
                        stop.append(loop[0])
        
        return([start, stop, repeats])
        
     
     
    def create_PB_sequence_instruction_list(self, data):   # Creates a list of instructions (values + delays) for a given sequence
        
           
        #Conditions - ramp should be ignored. value other than 0 should be considered to be 1
        data = data.swaplevel(i=0, j=1)  #Making time the primary index
        data = data.sortlevel(level=0) #Arranging by time
        
        time_list = np.unique(data.index.get_level_values(0)) #Getting list of times
        
        delays = time_list[1:] - time_list[0:-1]
        
        #Calculating values
        
        
        value_list = []
        channel_list = []
        instruction_list = []
        
        for time_i in time_list[0:-1]: #skipping the last time
            
            current_value = data.xs(time_i)
            channel_list.append(list(current_value.index.get_level_values(0)))
            value_list.append(list(np.transpose(current_value.as_matrix(columns=['Value']))[0]))
        
        number_instructions = len(delays)
        
        previous_value_dict = {}
        channels = []
        
        for i in xrange(number_instructions): #Will be atlest of length 1
            if i == 0: #All channels are there at time 0
                instruction = 0
                channels = channel_list[i]
                for j in xrange(len(channel_list[i])):
                    previous_value_dict[channel_list[i][j]] = value_list[i][j]
                    instruction += 2**(channel_list[i][j]) * value_list[i][j]
                instruction_list = np.append(instruction_list, instruction)
            
            else :
                instruction = 0
                for j in xrange(len(channels)):
                    if channels[j] in channel_list[i]: 
                        loc = channel_list[i].index(channels[j])
                        instruction += 2**(channel_list[i][loc]) * value_list[i][loc]
                        previous_value_dict[channel_list[i][loc]] = value_list[i][loc]
                    else:
                        instruction += 2**(channels[j]) * previous_value_dict[channels[j]]
                
                instruction_list = np.append(instruction_list, instruction)

        return [delays, instruction_list]
        
    
                
    '''
    Example of PB_loop_list - 
    
    Input: [[[['a',2],['b',3],['c',1]],10],['c',4]]
    
    Output: [['a', [1, 2], [0, 10]], ['b', [2, 3], [0, 10]], ['c', [3, 1], [0, 10]], ['c', [1, 4]]] 
    '''   
    
    def create_PB_loop_list(self, sequence_order_list):
        self.loop_number = 1
        return self.create_PB_loop_list_helper([], sequence_order_list)
        
        
    def create_PB_loop_list_helper(self, outer_loops, sequence_order_list):
        if len(sequence_order_list) == 1:
            self.loop_number +=1 
            if type(sequence_order_list[0][0]) != type([]): #I think this should be sufficient, keep an eye out for this condition
                repeats =  sequence_order_list[0][1]
                sequence =  sequence_order_list[0][0]
                return [[sequence, [self.loop_number, repeats]] + outer_loops]
                
            else:
                return self.create_PB_loop_list_helper([[self.loop_number, sequence_order_list[0][1]]],  sequence_order_list[0][0])
        else:
            return self.create_PB_loop_list_helper(outer_loops, [sequence_order_list[0]]) + self.create_PB_loop_list_helper(outer_loops, sequence_order_list[1::]) 
            
            
        
if __name__ == '__main__':
    from labrad import util
    util.runServer(Sequence_Programmer_Server())
    
    