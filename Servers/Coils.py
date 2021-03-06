# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 18:16:34 2016

@author: AdityaVignesh
"""

"""
This is the abstraction server that handles the Coils

It loads the mapping for property to channels from the Device Configuration file.

We can also specify how the property values map to card voltages in here as well.

"""

"""
### BEGIN NODE INFO
[info]
name = coils
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

class CoilServer(LabradServer):

    name = "coils"

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
            if deviceConfig[k]['server'] == 'coils':
                device_dictionary[k] = deviceConfig[k]['properties']
        return device_dictionary


    @setting(1, sequence='s', coil='s', df='s')
    def set_values(self, c, sequence , coil = '', df = '{}'):
        card_df = pd.DataFrame(index =self.init_index, columns = self.init_columns)
        df = pd.DataFrame().from_dict(eval(df))
        if not(df.empty): #Then df is the change from previous, send the information to the card
                                     #programmer - it will handle the change... But do not program anything else
            properties = np.unique(df.index.get_level_values(0)).tolist()
            
            HV_allowed_times = []
            if coil == 'Big X bias Coils' :
                """
                !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                Broken - needs fixing
                """
                
                if 'HV' in properties : #Note the HV should be defined before the times when voltage needs to be high 
                    current_prop_df = df.xs('HV')
                    times = list(current_prop_df.index)
                    HV_allowed_times = []
                    start_flag = 0
                    time0 = times[0]
                    timeend = times[-1]
                    if current_prop_df.ix[time0]['Value'] == 1:
                        HV_allowed_temp = []
                        start_flag = 1
                        HV_allowed_temp.append(time0) 
            
                    for time in times[1:-1]:
                            if current_prop_df.ix[time]['Value'] == 1:
                                if start_flag == 0 :
                                    HV_allowed_temp = []
                                    start_flag = 1
                                    HV_allowed_temp.append(time) 
                            elif current_prop_df.ix[time]['Value'] == 0:
                                if start_flag == 1 :
                                    start_flag = 0
                                    HV_allowed_temp.append(time) 
                                    HV_allowed_times.append(HV_allowed_temp)
                                    
                    if start_flag == 1 :
                        start_flag = 0
                        HV_allowed_temp.append(timeend) 
                        HV_allowed_times.append(HV_allowed_temp)
                       
                                    
               
            for prop in properties:
                prop_values = self.device_dictionary[coil][prop]
                current_prop_df = df.xs(prop)

                if coil == 'MOT Coils' and prop == 'Volt':
                    current_prop_df['Value'] = np.maximum(0,np.minimum(1.5, current_prop_df['Value']))
    
                if coil == 'Big X bias Coils' and prop == 'Volt':
                    times = list(current_prop_df.index)
                    for time in times:
                        for HV_times in HV_allowed_times:
                            if (time >= HV_times[0]) and (time <= HV_times[1]):
                                current_prop_df.ix[time]['Value'] = np.sign(current_prop_df.ix[time]['Value'])*np.minimum(2.0, np.abs(current_prop_df.ix[time]['Value']))
                            else :
                                current_prop_df.ix[time]['Value'] = np.sign(current_prop_df.ix[time]['Value'])*np.minimum(0.25, np.abs(current_prop_df.ix[time]['Value']))
                    
                        
                if prop == 'on':
                    temp = np.array(current_prop_df['Value'])
                    mask = current_prop_df['Value'] != 0
                    temp[mask] = 1
                    current_prop_df['Value'] = temp

                if  prop_values[0] == 'Card':
                    times = list(current_prop_df.index) #levels does not work for 1 index
                    
                    for time in times:
                        card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time)] = current_prop_df.ix[time]


        else :
            print('ERROR. DataFrame empty !!!')

        if not(card_df.empty):
            self.send_to_Sequence_Programmer(sequence, coil, card_df)


    def send_to_Sequence_Programmer(self, sequence, device, df):
        p = self.client.sequenceprogrammer.packet()
        p.receive_card_data(sequence, device, str(df.to_dict()))
        p.send()


if __name__ == '__main__':
    from labrad import util
    util.runServer(CoilServer())
