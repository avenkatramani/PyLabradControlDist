# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 18:16:34 2016

@author: AdityaVignesh
"""

"""
This is the abstraction server that handles the locks

It loads the mapping for property to channels from the Device Configuration file. 

We can also specify how the property values map to card voltages in here as well.




#### To Implement - bring in the PTS here for control and probe lock 

"""

"""
### BEGIN NODE INFO
[info]
name = lock
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
import pandas as pd
import numpy as np
import yaml

class lockServer(LabradServer):
    
    name = "lock"
    
    def initServer(self):
        
        self.init_index_cards = pd.MultiIndex(levels = [[],[],[],[],[]],
                                   labels = [[],[],[],[],[]],
                                   names = ['Card','Number', 'Sequence', 'Channel','Time']) 
        self.init_columns_cards = ['Ramp','Value']
        
        self.init_index_Arduino = pd.MultiIndex(levels = [[],[],[],[]],
                                   labels = [[],[],[],[]],
                                   names = ['port', 'Sequence', 'dev', 'Time']) 
        self.init_columns_Arduino = ['Value']
        
                
        self.device_dictionary = self.get_device_dictionary()
        
        
        
        
        
    def get_device_dictionary(self):
        with open('DeviceConfig.yaml', 'r') as f:
            deviceConfig = yaml.load(f)
         
        device_dictionary = {}
        for k in deviceConfig.keys():
            if deviceConfig[k]['server'] == 'lock':
                device_dictionary[k] = deviceConfig[k]['properties']
                
        return device_dictionary

    
    @setting(1, sequence='s', lock='s', df='s')
    def set_values(self, c, sequence , lock = '', df = '{}'):
        
        card_df = pd.DataFrame(index =self.init_index_cards, columns = self.init_columns_cards)
        Arduino_df = pd.DataFrame(index =self.init_index_Arduino, columns = self.init_columns_Arduino)
        
       
        
        df = pd.DataFrame().from_dict(eval(df))
        if not(df.empty): #Then df is the change from previous, send the information to the card
                                     #programmer - it will handle the change... But do not program anything else
            properties = np.unique(df.index.get_level_values(0)).tolist()
        
            for prop in properties:
                
                prop_values = self.device_dictionary[lock][prop]
                current_prop_df = df.xs(prop)
                
                if  prop_values[0] == 'Card':
                    times = list(current_prop_df.index) #levels does not work for 1 index
                    
                    for time in times:
                        card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time)] = current_prop_df.ix[time]
                                   
                
                if  prop_values[0] == 'Card+Arduino' : 
                    times = list(current_prop_df.index) #levels does not work for 1 index
                    #problem when dealing with a short sequence. One way to fix this is if the sequence is less 500 mu s (a large overestimate) do nothing
                    
                    if (times[-1] - times[0]) < 500*10**(-6):
                        for time in times[:-1]:
                            card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time)] = [0,0]
                                        
                    # Also if the frequency is not defined earlier. It will be zero from the sequence generator in the timing server. If we see zero, do nothing
                    else:    
                        for ix, time in enumerate(times[:-1]):
                            
                            #Implementing ramps:
                            if current_prop_df.ix[time][0] == 1: 
                                times_ramp = np.arange(times[ix], times[ix+1], 250*10**(-6))
                                if times[ix+1] - times_ramp[-1] < 250*10**(-6):
                                    times_ramp[-1] = times[ix+1]
                                else:
                                    times_ramp = np.append(times_ramp,times[ix+1])
                                for time_ramp in times_ramp[:-1]:
                                    card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time_ramp)] = [0,0]
                                    if current_prop_df.ix[time][1] != 0: 
                                        card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time_ramp+0.000002)] = [0,1]
                                        card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time_ramp+ 0.000062)] = [0,0]
                                        Arduino_df.ix[(prop_values[4], sequence, prop_values[5], time_ramp)] = [current_prop_df.ix[time_ramp][1]]
                                     
                                                                   
                            
                            else:
                                # Adding 60 mus for trigger on off. Make sure that the frequency is not changed at the end of the sequence
                                card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time)] = [0,0] #Only a temporary fix for the first element to be zero... Needs a more global fix to allow the first and last element to be different
                                if current_prop_df.ix[time][1] != 0: 
                                    card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time+0.000002)] = [0,1]
                                    card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time+ 0.000062)] = [0,0]
                                    Arduino_df.ix[(prop_values[4], sequence, prop_values[5], time)] = [current_prop_df.ix[time][1]]
                        
                    #Dummy for end... Ignores last frequency 
                    
                    card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], times[-1])] = [0,0]
                                     
                               
                             
                
        
        else :
            print('ERROR. DataFrame empty !!!')
    
        if not(card_df.empty) and (Arduino_df.empty):
            self.send_card_to_Sequence_Programmer(sequence, lock, card_df)
        
        if card_df.empty and not(Arduino_df.empty):
            self.send_Arduino_to_Sequence_Programmer(sequence, lock, Arduino_df)
        
        if not(card_df.empty) and not(Arduino_df.empty):
            self.send_card_to_Sequence_Programmer('', '', card_df) #Send sequence and device info only once
            self.send_Arduino_to_Sequence_Programmer(sequence, lock, Arduino_df)
 
                    
    def send_card_to_Sequence_Programmer(self, sequence, device, df):
        p = self.client.sequenceprogrammer.packet()
        p.receive_card_data(sequence, device, str(df.to_dict()))
        p.send()
    
    def send_Arduino_to_Sequence_Programmer(self, sequence, device, df):
        p = self.client.sequenceprogrammer.packet()
        p.receive_arduino_data(sequence, device, str(df.to_dict()))
        p.send()
                
                
    @setting(2, lock='s', frequency='v[MHz]')
    def set_frequency(self, c, lock, frequency):
        1

  
if __name__ == '__main__':
    from labrad import util
    util.runServer(lockServer())
    
    