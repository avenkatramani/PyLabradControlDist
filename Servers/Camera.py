#
# Camera server
#
# Aditya 07/2016
"""
### BEGIN NODE INFO
[info]
name = camera
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
import ujson  as json

import datetime as dt

from Unibrain import Unibrain

import matplotlib.pyplot as plt


   
######### Settings



class Camera(LabradServer):
    """Camera Server"""

    name="camera"
    password=""
    
    def initServer(self):
        self.camera = Unibrain()
        self.camera.setImaqRetType()
        self.camera.setupCamera()
        self.camera.startCamera()
        self.camera.createImage(1)
        
        
    def stopServer(self):
        
        self.camera.closeAll()


    @setting(10,"acquire", returns='s') # Returning it as integer is too slow.....
    def acquire(self, c): 
        img = self.camera.grabImage(1)
        temp_filename = 'cam3.txt'
        
        start_time = dt.datetime.now()
        with open('B:\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\TEMP\\'+temp_filename,'w') as outfile:
            json.dump(img, outfile)
            
        print('UJson save time :' + str((dt.datetime.now() - start_time)))  
         
        return temp_filename
            
        
if __name__ == "__main__":
    from labrad import util
    util.runServer(Camera())




    
    
    
