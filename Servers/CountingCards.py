# Aditya 7/16

"""
### BEGIN NODE INFO
[info]
name = countingcards
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
import pandas as pd
import numpy as np
import yaml

class CountingCards(LabradServer):
    """Counting cards device server"""

    name="countingcards"

    password=""

   
    def initServer(self):
        
        self.init_index = pd.MultiIndex(levels = [[],[],[],[],[]],
                                   labels = [[],[],[],[],[]],
                                   names = ['Card','Number', 'Sequence', 'Channel','Time']) 
        self.init_columns = ['Ramp','Value']
        
        
                
        self.device_dictionary = self.get_device_dictionary()
        
        
        
        
        
    def get_device_dictionary(self):
        with open('DeviceConfig.yaml', 'r') as f:
            deviceConfig = yaml.load(f)
         
        device_dictionary = {}
        for k in deviceConfig.keys():
            if deviceConfig[k]['server'] == 'countingcards':
                device_dictionary[k] = deviceConfig[k]['properties']
                
        return device_dictionary
        
        
    @setting(2, sequence='s', CC='s', df='s')
    def set_values(self, c, sequence , CC = '', df = '{}'):
        
        card_df = pd.DataFrame(index =self.init_index, columns = self.init_columns)
        
       
        
        df = pd.DataFrame().from_dict(eval(df))
        if not(df.empty): #Then df is the change from previous, send the information to the card
                                     #programmer - it will handle the change... But do not program anything else
            properties = np.unique(df.index.get_level_values(0)).tolist()
        
            for prop in properties:
                
                prop_values = self.device_dictionary[CC][prop]
                current_prop_df = df.xs(prop)
                
                if  prop_values[0] == 'Card':
                    times = list(current_prop_df.index) #levels does not work for 1 index
                    
                    for time in times:
                        card_df.ix[(prop_values[1], prop_values[2], sequence, prop_values[3], time)] = current_prop_df.ix[time]
                
                
        
        else :
            print('ERROR. DataFrame empty !!!')
    
        if not(card_df.empty):
            self.send_to_Card_Programmer(sequence, CC, card_df)
        
                    
    def send_to_Card_Programmer(self, sequence, device, df):
        p = self.client.cardprogrammer.packet()
        p.receive_card_data(sequence, device, str(df.to_dict()))
        p.send()
        
          
    @setting(3,"setupCounter", counter_number="w",returns="")
    def setupCounter(self, c, counter_number = 0):
        self.client.nicounter.setupcounter(counter_number)
    
        
    @setting(4,"startCounter",returns="")
    def startCounter(self,c, counter_number):
        self.client.nicounter.startcounter(counter_number)
            
    @setting(5,"stopCounter",returns="")
    def stopCounter(self,c, counter_number):
        self.client.nicounter.stopcounter(counter_number)
        

    @setting(6,"readCounter", counter_number="w", returns="*w")
    def readCounter(self,c, counter_number):
        return self.client.nicounter.readcounter(counter_number)
        
        



if __name__ == "__main__":
    from labrad import util
    util.runServer(CountingCards())

    

