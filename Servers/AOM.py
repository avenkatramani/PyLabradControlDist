#Created on Thu Apr 21 18:16:34 2016
#
#@author: AdityaVignesh
#
#This is the abstraction server that handles the AOMs
#It loads the mapping for property to channels from the Device Configuration file. 
#We can also specify how the property values map to card voltages in here as well.


"""
### BEGIN NODE INFO
[info]
name = aom
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
import datetime as dt

class AOMServer(LabradServer):
    
    name = "aom"
    
    def initServer(self):
        
        self.init_index_cards = pd.MultiIndex(levels = [[],[],[],[],[]],
                                   labels = [[],[],[],[],[]],
                                   names = ['Card','Number', 'Sequence', 'Channel','Time']) 
        self.init_columns_cards = ['Ramp','Value']
        
        
        self.init_index_USB = pd.MultiIndex(levels = [[],[],[]],
                                   labels = [[],[],[]],
                                   names = ['Port', 'Sequence', 'Index']) 
        self.init_columns_USB = ['Value']

                
        self.device_dictionary = self.get_device_dictionary()
        

        
        
        
    def get_device_dictionary(self):
        with open('DeviceConfig.yaml', 'r') as f:
            deviceConfig = yaml.load(f)
         
        device_dictionary = {}
        for k in deviceConfig.keys():
            if deviceConfig[k]['server'] == 'aom':
                device_dictionary[k] = deviceConfig[k]['properties']
                
        return device_dictionary

    
    @setting(1, sequence='s', AOM='s', df='s')
    def set_values(self, c, sequence , AOM = '', df = '{}'):
        card_df = pd.DataFrame(index =self.init_index_cards, columns = self.init_columns_cards)
        USB_df = pd.DataFrame(index =self.init_index_USB, columns = self.init_columns_USB)

        
        df = pd.DataFrame().from_dict(eval(df))
        if not(df.empty): #Then df is the change from previous, send the information to the card
                                     #programmer - it will handle the change... But do not program anything else
            properties = np.unique(df.index.get_level_values(0)).tolist()
        
            for prop in properties:
                
                prop_values = self.device_dictionary[AOM][prop]
                current_prop_df = df.xs(prop)
                
                if prop == 'on':
                    temp = np.array(current_prop_df['Value'])
                    mask = current_prop_df['Value'] != 0
                    temp[mask] = 1 
                    current_prop_df['Value'] = temp

                if  prop_values[0] == 'Card':
                    times = list(current_prop_df.index) #levels does not work for 1 index
                    
                    for time in times:
                        card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time)] = current_prop_df.ix[time]
                                   
                if  prop_values[0] == 'USB':
                        #times = list(current_prop_df.index) #levels does not work for 1 index
                        1
                        #for time in times:
                        #    card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time)] = current_prop_df.ix[time]
                
                
        
        else :
            print('ERROR. DataFrame empty !!!')
    
        if not(card_df.empty) and USB_df.empty:
            self.send_to_Sequence_Programmer(sequence, AOM, card_df, 'card')
            
        if card_df.empty and not(USB_df.empty):
            self.send_to_Sequence_Programmer(sequence, AOM, USB_df, 'USB')
            
        if not(card_df.empty) and not(USB_df.empty):
            self.send_to_Sequence_Programmer(sequence, AOM, card_df, 'card+USB')
            self.send_to_Sequence_Programmer(sequence, AOM, USB_df, 'USB+card')
        
        
    @setting(2, device = 's', prop = 's', sequences = 's', set_point = 'v[]', step='v[]')
    def monitor_and_update(self, c, device, prop, sequences, set_point, step):
        if device in self.device_dictionary.keys():
            p = self.client.tds2014c_a.packet()
            p.pk2pk(1, sync=True) 
            current_value = round((yield p.send())['pk2pk'],4)
            set_point = np.float(set_point)
            step = np.float(step)
            if np.abs(current_value - set_point) > step:
                value_update = step*np.sign(set_point - current_value)
                self.client.timingcontrol.update_sequences(sequences, device, prop, value_update)
                
                    
    def send_to_Sequence_Programmer(self, sequence, device, df, typ):
        if typ == 'card':
            p = self.client.sequenceprogrammer.packet()
            p.receive_card_data(sequence, device, str(df.to_dict()))
            p.send()
        elif typ == 'USB':
            p = self.client.sequenceprogrammer.packet()
            p.receive_card_data(sequence, device, str(df.to_dict()))
            p.send()
        if typ == 'card+USB':
            p = self.client.sequenceprogrammer.packet()
            p.receive_card_data(sequence, device, str(df.to_dict()))
            p.send()
        if typ == 'USB+card':
            p = self.client.sequenceprogrammer.packet()
            p.receive_card_data('', '', str(df.to_dict()))
            p.send()
                
    def send_via_USB(self): #Function to program though other means
        
        # Or any other functions we may need to program the AOM values
        self.USB_df = pd.DataFrame()
  
if __name__ == '__main__':
    from labrad import util
    util.runServer(AOMServer())
    
    