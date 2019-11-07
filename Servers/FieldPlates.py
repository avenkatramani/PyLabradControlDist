# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 18:16:34 2016

@author: AdityaVignesh
"""

"""
This is the abstraction server that handles the plates

It loads the mapping for property to channels from the Device Configuration file. 

We can also specify how the property values map to card voltages in here as well.

"""

"""
### BEGIN NODE INFO
[info]
name = fieldplates
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
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.reactor import callLater
import labrad.units as units
import pandas as pd
import numpy as np
import yaml

class FieldPlatesServer(LabradServer):
    
    name = "fieldplates"
       
    def initServer(self):
        
        self.init_index = pd.MultiIndex(levels = [[],[],[],[],[]],
                                   labels = [[],[],[],[],[]],
                                   names = ['Card', 'Number', 'Sequence', 'Channel', 'Time']) 
        self.init_columns = ['Ramp','Value']
        
        
                
        self.device_dictionary = self.get_device_dictionary()
        
        
        
        
        
    def get_device_dictionary(self):
        with open('DeviceConfig.yaml', 'r') as f:
            deviceConfig = yaml.load(f)
                       
        device_dictionary = {}
        for k in deviceConfig.keys():
            if deviceConfig[k]['server'] == 'fieldplates':
                device_dictionary[k] = deviceConfig[k]['properties']
             
        return device_dictionary

    
    @setting(1, sequence='s', plate='s', df='s')
    def set_values(self, c, sequence , plate = '', df = '{}'):
        card_df = pd.DataFrame(index =self.init_index, columns = self.init_columns)
        df = pd.DataFrame().from_dict(eval(df))
        if not(df.empty): #Then df is the change from previous, send the information to the card
                                     #programmer - it will handle the change... But do not program anything else
            properties = np.unique(df.index.get_level_values(0)).tolist()
            prop0_df = df.xs(properties[0])
            prop_values = self.device_dictionary[plate][properties[0]]
            times = list(prop0_df.index)
            length = len(times)
            Vx = np.zeros(length)
            Vy = np.zeros(length)
            Vz = np.zeros(length)
            Gx = np.zeros(length)
            Gy = np.zeros(length)
            Gz = np.zeros(length)
            offset = np.zeros(length)

            for prop in properties:
                if prop == 'Vx':
                    temp = df.xs('Vx')
                    Vx =  np.array(temp['Value'])
                if prop == 'Vy':
                    temp = df.xs('Vy')
                    Vy =  np.array(temp['Value'])
                if prop == 'Vz':
                    temp = df.xs('Vz')
                    Vz =  np.array(temp['Value'])
                if prop == 'Gx':
                    temp = df.xs('Gx')
                    Gx =  np.array(temp['Value'])
                if prop == 'Gy':
                    temp = df.xs('Gy')
                    Gy =  np.array(temp['Value'])
                if prop == 'Gz':
                    temp = df.xs('Gz')
                    Gz =  np.array(temp['Value'])
                    
        
            for ix, time in enumerate(times):
                card_df.ix[(prop_values[1], prop_values[2], sequence, 0, time)] = [0,  Vy[ix] - Vz[ix] - Gy[ix] ]
                card_df.ix[(prop_values[1], prop_values[2], sequence, 1, time)] = [0,  Vx[ix] - Vz[ix] - Gx[ix] ]
                card_df.ix[(prop_values[1], prop_values[2], sequence, 2, time)] = [0, -Vy[ix] - Vz[ix] + Gy[ix] ]
                card_df.ix[(prop_values[1], prop_values[2], sequence, 3, time)] = [0, -Vx[ix] - Vz[ix] + Gx[ix] ]
                card_df.ix[(prop_values[1], prop_values[2], sequence, 4, time)] = [0,  Vy[ix] + Vz[ix] + Gy[ix] ]
                card_df.ix[(prop_values[1], prop_values[2], sequence, 5, time)] = [0, -Vx[ix] + Vz[ix] - Gx[ix] ]
                card_df.ix[(prop_values[1], prop_values[2], sequence, 6, time)] = [0, -Vy[ix] + Vz[ix] - Gy[ix] ]
                card_df.ix[(prop_values[1], prop_values[2], sequence, 7, time)] = [0,  Vx[ix] + Vz[ix] + Gx[ix] ]
                                       
                                   
        else :
            print('ERROR. DataFrame empty !!!')
        
        if not(card_df.empty):
            self.send_to_Sequence_Programmer(sequence, plate, card_df)
        
                    
    def send_to_Sequence_Programmer(self, sequence, device, df):
        p = self.client.sequenceprogrammer.packet()
        p.receive_card_data(sequence, device, str(df.to_dict()))
        p.send()
                
     
if __name__ == '__main__':
    from labrad import util
    util.runServer(FieldPlatesServer())
    
    