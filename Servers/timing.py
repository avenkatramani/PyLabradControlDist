# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 11:26:49 2016

@author: AdityaVignesh

This server holds the full timing database for each exxperiment. The expectation is that the experiment sequence file contains all the 
sequences even though they might not all be used for each run. For a completely new experiment, the database must be reloaded. 

On the order to program, it tells the card_programmer which devices and sequences to recieve data from. Then it sends database cross sections 
to the appropriate device servers. This procedure also assuments that for each sequences, we specify the values of all devices.  
"""


"""
### BEGIN NODE INFO
[info]
name = timingcontrol
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


from labrad.server import LabradServer, setting,  Signal
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.reactor import callLater
import labrad.units as units
import pandas as pd
import numpy as np
import yaml
import re
import datetime as dt

  
class TimingServer(LabradServer):
    
    name = "timingcontrol"
             
    def initServer(self):
        self.dfUpdated = 0
        self.df = pd.DataFrame()
        self.updated_df = pd.DataFrame()
        self.sequence_order_list = []
        self.sequence_length_list = {}
        #Dictionary mapping the devices to the appropriate device servers
        self.Device_to_Server = self.get_Device_to_Server_dict()
               
    
    def clearAll(self):
        self.df = pd.DataFrame()
        self.updated_df = pd.DataFrame()
        self.sequence_order_list = []
        self.sequence_length_list = {}
        
    def get_Device_to_Server_dict(self):
        with open('DeviceConfig.yaml', 'r') as f:
            deviceConfig = yaml.load(f)
         
        Device_to_Server = {}
        for k in deviceConfig.keys():
            Device_to_Server[k] = deviceConfig[k]['server']
        
        return Device_to_Server
        
        
    @setting(0, address = 's', allSequences = 's')
    def load_seqs_file(self, c, address, allSequences):  #To create a local database of the current experimental sequences
            allSequences = eval(allSequences)            
            temp = dt.datetime.now()
            self.clearAll()
            df_list = []
            for sequence in allSequences:
                sequence_folder = sequence.split('_')[0]
                
                df_list.append(pd.read_excel(address+'\\'+sequence_folder+'\\'+sequence+'.xlsx', index_col = [0,1,2]))
            
            self.df = pd.concat(df_list, keys = allSequences, names = ['Sequence'])

            self.create_sequence_length_list()
            self.notify_clients(c, str(self.df.to_dict()))
            print('Load from Excel time :' + str((dt.datetime.now() - temp)))
        
    
    @setting(10, ddf='s')
    def update_df(self,c,ddf): 
        self.df = pd.DataFrame.from_dict(eval(ddf))
        self.dfUpdated = 1
     
    @setting(11) 
    def check_df_change(self, c):
        if self.dfUpdated:
            self.dfUpdated = 0
            return 1
        else:
            return 0
            
            
    @setting(101, sequences='s',device='s', prop='s', value='v[]')
    def update_sequences(self, c, sequences, device, prop, value): 
        sequences = eval(sequences)
        for sequence in sequences:
            current_df = self.df.xs(sequence).xs(device).xs(prop)
            times = list(np.unique(current_df.index.get_level_values(0)))
            for time in times:
                self.df.ix[(sequence, device, prop, time), 'Ramp'] = 0
                self.df.ix[(sequence, device, prop, time), 'Value'] = self.df.ix[(sequence, device, prop, time), 'Value']+ np.float(value)

            
        self.dfUpdated = 1
        
    
    @setting(1001, sequences_scan = 's')
    def update_sequences_scan(self, c, sequences_scan): 
        sequences_scan = eval(sequences_scan)
        for sequence in sequences_scan:
            sequence_name = sequence[0]
            device = sequence[1]
            prop = sequence[2]
            times = sequence[3]
            values = sequence[4]
            
            for ix,time in enumerate(times):
                self.df.ix[(sequence_name, device, prop, time), 'Ramp'] = 0
                self.df.ix[(sequence_name, device, prop, time), 'Value'] = values[ix]

        
        
    def get_sequences_from_order_list(self,sequence_order_list):  #This function picks out all the sequences from the order list. Could be pushed to the card programmer
        if len(sequence_order_list) == 1:
            if type(sequence_order_list[0][0]) != type([]): #I think this should be sufficient, keep an eye out for this condition
                return [sequence_order_list[0][0]]
            else:
                return self.get_sequences_from_order_list(sequence_order_list[0][0])+self.get_sequences_from_order_list(sequence_order_list[0][0])
        else:
            return self.get_sequences_from_order_list([sequence_order_list[0]]) + self.get_sequences_from_order_list(sequence_order_list[1::])
            
            
    def get_device_list(self): #Needs to pick out all devices in this run, to tell the card programmer what to receive from. Cannot be pushed to the card programmer. To prevent breaking it up I've also included the function to pick out sequenes above      
        allDevices = np.unique(self.df.index.get_level_values(1))
        device_dict = {}
        for device in allDevices:
            deviceDf = self.df.xs(device, level=1)
            device_dict[device] = list(np.unique(deviceDf.index.get_level_values(1)))
        return device_dict
         
    @setting(2, sequence_order_list='s')
    def program(self,c, sequence_order_list):
        temp = dt.datetime.now()
        self.client.sequenceprogrammer.clearall()
        sequence_order_list = eval(sequence_order_list)
             
            
        if sequence_order_list == self.sequence_order_list:
            1#self.client.cardprogrammer.load_cards() # self.updated_df) #It checks for emptyness in that function. Worry about updating later
        if 1 :  
            self.sequence_order_list = sequence_order_list
            sequences_order = list(self.get_sequences_from_order_list(sequence_order_list)) # Ordered list of sequences based on the order list
            sequences = list(np.unique(sequences_order))
            device_dict = self.get_device_list()
            devices = list(device_dict.keys())
            
            ##### Keep a record of previous property for each device and maintain the last value if absent in the sequence. Initialize with zeros. 
            previous_property_value = {}
            previous_sequence_property_value = {}
            sequenceCount  = {} #Everytime that a sequence changes because of the previous value, add 1 and call it a by a new name str(sequence)+str(sequenceCount)
            sequenceCountPrevious = {}
            changeFlag = 0
            sequencesSent = []

            for sequence in sequences:
                sequenceCount[sequence] = 0
                sequenceCountPrevious[sequence] = 0
                previous_sequence_property_value[sequence] = {}
                for device in devices:
                    previous_sequence_property_value[sequence][device] = {}
                    for prop in device_dict[device]:
                        previous_sequence_property_value[sequence][device][prop] = None
                    
            for device in devices:
                previous_property_value[device] = {}
                for prop in device_dict[device]:
                    previous_property_value[device][prop] = 0

            sequences_order_updated = []
            for sequence in sequences_order:
                sequenceCount[sequence] += 1
                current_sequence = self.df.xs(sequence)
                current_devices = list(current_sequence.index.get_level_values(0))  
                times = np.unique(current_sequence.index.get_level_values(2))
                start_time = times.min() #should be zero
                stop_time = times.max()
                
                for device in devices:
                    
                        
                    if device in current_devices:
                        current_sequence_device = current_sequence.xs(device)
                        current_properties = list(np.unique(current_sequence_device.index.get_level_values(0)))
                        for prop in device_dict[device]:
                            if prop in current_properties:
                                previous_property_value[device][prop] = current_sequence_device.xs(prop).xs(stop_time)[1]
                                previous_sequence_property_value[sequence][device][prop] = previous_property_value[device][prop]
                            
                            else:
                                 
                                if (previous_sequence_property_value[sequence][device][prop] != previous_property_value[device][prop]):
                                    if previous_sequence_property_value[sequence][device][prop] == None:
                                        previous_sequence_property_value[sequence][device][prop] = previous_property_value[device][prop]
                                    else:
                                        changeFlag += 1
                                        previous_sequence_property_value[sequence][device][prop] = previous_property_value[device][prop]
                                current_sequence.ix[(device, prop, start_time), 'Ramp'] = 0
                                current_sequence.ix[(device, prop, start_time), 'Value'] = previous_property_value[device][prop]
                                current_sequence.ix[(device, prop, stop_time), 'Ramp'] = 0
                                current_sequence.ix[(device, prop, stop_time), 'Value'] = previous_property_value[device][prop]
                            

                                
                    else:
                        for prop in device_dict[device]:
                            if (previous_sequence_property_value[sequence][device][prop] != previous_property_value[device][prop]):
                                if previous_sequence_property_value[sequence][device][prop] == None:
                                    previous_sequence_property_value[sequence][device][prop] = previous_property_value[device][prop]
                                else:
                                    changeFlag += 1
                                    previous_sequence_property_value[sequence][device][prop] = previous_property_value[device][prop]
                                    
                            current_sequence.ix[(device, prop, start_time), 'Ramp'] = 0
                            current_sequence.ix[(device, prop, start_time), 'Value'] = previous_property_value[device][prop]
                            current_sequence.ix[(device, prop, stop_time), 'Ramp'] = 0
                            current_sequence.ix[(device, prop, stop_time), 'Value'] = previous_property_value[device][prop]

                        
                 
                if changeFlag == 0:
                    if sequenceCountPrevious[sequence] == 0:   
                        if sequence not in sequencesSent:
                            sequencesSent.append(sequence)
                            for device in devices:
                                getattr(self.client,self.Device_to_Server[device]).set_values(str(sequence), str(device), str(current_sequence.xs(device).to_dict()))
                        sequences_order_updated.append(sequence)
                    else:
                        sequences_order_updated.append(str(sequence)+'___'+str(sequenceCountPrevious[sequence]))
                else: 
                    changeFlag = 0
                    sequenceCountPrevious[sequence] = sequenceCount[sequence]
                    for device in devices:
                            getattr(self.client,self.Device_to_Server[device]).set_values(str(sequence)+'___'+str(sequenceCount[sequence]), str(device), str(current_sequence.xs(device).to_dict()))
                    if str(sequence)+'___'+str(sequenceCount[sequence]) not in sequences:
                        sequences.append(str(sequence)+'___'+str(sequenceCount[sequence]))
                    
                    sequences_order_updated.append(str(sequence)+'___'+str(sequenceCount[sequence]))
                    self.sequence_length_list[str(sequence)+'___'+str(sequenceCount[sequence])] = self.sequence_length_list[sequence] 
                    
            self.index = -1
            new_sequence_order_list =  self.update_sequence_order_list(sequence_order_list, sequences_order_updated)
            
            

            self.client.sequenceprogrammer.update_receive_list(str(sequences), str(devices), str(new_sequence_order_list), str(self.sequence_length_list)) #This function tells the card programmer what to expect
        print('Sequence processing time :' + str((dt.datetime.now() - temp)))        
    
    onNotification = Signal(1234, 'signal: test', 's')
    @setting(20, message='s')
    def notify_clients(self, c, message):
        self.onNotification(message)  

    def update_sequence_order_list(self, sequence_order_list, sequences_order_updated):  
        if len(sequence_order_list) == 1:
            if type(sequence_order_list[0][0]) != type([]):
                self.index += 1
                return [[sequences_order_updated[self.index],sequence_order_list[0][1]]]
            else:
                return self.update_sequence_order_list(sequence_order_list[0][0], sequences_order_updated) + [[self.update_sequence_order_list(sequence_order_list[0][0], sequences_order_updated), sequence_order_list[0][1]-1]]
        else:
            return self.update_sequence_order_list([sequence_order_list[0]], sequences_order_updated) + self.update_sequence_order_list(sequence_order_list[1::], sequences_order_updated)
            
    def create_sequence_length_list(self): #This will be passed down to the card programmer . This is neceassry  because the card programmer does not know the length of each sequence and that information is required while stitching together sequences of the experiment
        self.sequence_length_list = {}
        sequences = np.unique(self.df.index.get_level_values(0))
        for sequence in sequences:
            max_time = np.max(list(self.df.xs(sequence).index.get_level_values(2)))
            self.sequence_length_list[sequence] = max_time
            
       
   
         
if __name__ == '__main__':
    from labrad import util
    util.runServer(TimingServer())