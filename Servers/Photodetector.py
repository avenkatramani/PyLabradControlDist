#
# Camera server
#
# Aditya 07/2016
"""
### BEGIN NODE INFO
[info]
name = photodetector
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

from labrad.server import LabradServer, Signal, setting
import numpy as np
import yaml

   
######### Settings



class Photodetector(LabradServer):
    """Photodetector Server"""

    name="photodetector"
    password=""
    
    def initServer(self):
        self.device_dictionary = self.get_device_dictionary()
        
        
    def get_device_dictionary(self):
        with open('DeviceConfig.yaml', 'r') as f:
            deviceConfig = yaml.load(f)
         
        device_dictionary = {}
        for k in deviceConfig.keys():
            if deviceConfig[k]['server'] == 'photodetector':
                device_dictionary[k] = deviceConfig[k]['properties']
                
        return device_dictionary
    
        
     
    @setting(10,"acquire", detector ='s',returns='v') 
    def acquire(self, c, detector): 
        NI6250_channel = self.device_dictionary[detector]['NI6250'] 
        value = self.client.ni6250.getstaticvoltage(NI6250_channel)
        return value
            
        
if __name__ == "__main__":
    from labrad import util
    util.runServer(Photodetector())




    
    
    
