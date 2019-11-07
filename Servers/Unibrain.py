#
# Class for Unibrain Camera
#
# Aditya 07/2016



#############NOTE--
# Some issues with setting the trigger Attribute here : getting a ctypes value error and don't know how to fix it
#So, a work around it set the attributes in NI MAX and then run our program. 
#This works because the setting are saved even on restarting the camera 
#and secondly becuase we don't need to change these parameters often 




####################

import numpy as np
from ctypes import *
import os
import psutil
import datetime as dt
import time

########### nidaq.h types and constants
# set up c type names

int32 = c_long
uInt32 = c_ulong
uInt64 = c_ulonglong
float64 = c_double


# define some stuff which would have been done in a header file

SESSION_ID = uInt32

IMAQ_IMAGE_U8 = 0
        
class Rect(Structure):
    _fields_ = [
                ("top", int32), 
                ("left", int32),
                ("height", int32),
                ("width", int32),
                ]


######### Settings
                
cam = 'cam2'

#############


class Unibrain:
        
    def __init__(self):
        
        self.imaqdx = windll.niimaqdx
        self.imaq = windll.nivision
        self.image = {} #Maintain a dictionary of images here
        self.sid = SESSION_ID(0)
        #self.setupCamera()
        self.imaq.imaqMakeRect.restype = Rect
        self.IMAQ_NO_RECT =  self.imaq.imaqMakeRect(int32(0), int32(0), int32(0x7FFFFFFF), int32(0x7FFFFFFF)) 
        self.setImaqRetType()
        self.IMAQ_RECT =  self.imaq.imaqMakeRect(int32(0), int32(0), int32(1024), int32(1024)) 
        self.rows = int32(0)
        self.columns = int32(0)
		
    def setAttributes(self): #Making it all in one for now, split it for programming each attribute
        self._checkdx(self.imaqdx.IMAQSetAttribute(self.sid ))
    
    def setImaqRetType(self): 
       self.imaq.imaqImageToArray.restype = POINTER(c_ubyte)
		
        
    def closeAll(self):
        for img_name in self.image.keys():
            self.closeImage(img_name)        
        self.stopCamera()
        self.closeCamera()
        
    def createImage(self, img_name):
        self.image[img_name] = self._check(self.imaq.imaqCreateImage(IMAQ_IMAGE_U8, 3)) #ImageType GreyScale_U8 = 0, border = 3
        
    def setupCamera(self):
        self._checkdx(self.imaqdx.IMAQdxOpenCamera(cam, 0, byref(self.sid))) #0 is controller mode, 1 is listener mode, (const char *name, IMAQdxCameraControlMode mode, IMAQdxSession *id)
        print("Session ID :" + str(self.sid))
        self._checkdx(self.imaqdx.IMAQdxConfigureAcquisition(self.sid, 1, 2)) #(IMAQdxSession id, unsigned int continuous, unsigned int bufferCount)
        
    def startCamera(self):
        self._checkdx(self.imaqdx.IMAQdxStartAcquisition(self.sid))
        
        
        
    def stopCamera(self):   #Not the right way to deal with errors. modify it .....
        try:
            self._checkdx(self.imaqdx.IMAQdxStopAcquisition(self.sid))
        except:
            pass
        
    def closeCamera(self):
        try:
            self._checkdx(self.imaqdx.IMAQdxCloseCamera(self.sid))    
        except:
            pass
        
    def closeImage(self, img_name):
        try:
            self._check(self.imaq.imaqDispose(self.image[image_name]))
        except:
            pass
        
    def grabImage(self, img_name): 
        #time.sleep(0.1) #wait for image taken during imaging stage to be moved to the buffer. 100 ms is just about enough
                        #A smarter way is to wait for next buffer instead of using a fixed delay as done now
        
        actualBufferNumber = uInt32(0)
        desiredBufferNumber = uInt32(0)
        #self._checkdx(self.imaqdx.IMAQdxGrab(self.sid, self.image[img_name], uInt32(0), byref(actualBufferNumber))) #(IMAQdxSession id, Image *image, unsigned int waitForNextBuffer, unsigned int *actualBufferNumber)
        #print actualBufferNumber
        
        self._checkdx(self.imaqdx.IMAQdxGetImage(self.sid, self.image[img_name], uInt32(1), desiredBufferNumber, byref(actualBufferNumber))) #IMAQdxGetImage(IMAQdxSession id, Image* image, IMAQdxBufferNumberMode mode, uInt32 desiredBufferNumber, uInt32* actualBufferNumber)
        print actualBufferNumber
        
        img_array_buf = self.imaq.imaqImageToArray(self.image[img_name], self.IMAQ_RECT , byref(self.columns), byref(self.rows))
        img_array = np.zeros(1024*1024, dtype = np.ubyte)
        memmove(img_array.ctypes.data, img_array_buf, 1024*1024)
        self.imaq.imaqDispose(img_array_buf) #fixes memory leak
        img_array = img_array.reshape((1024,1024))
        img_array = img_array[237 : 787 , 237 :787] #Cutting it short
        img_array = img_array.astype(int)
        
        
        
        
        
        return img_array
     
    def _check(self, ret):
        """Checks NI-IMAQdx error messages, prints results"""
        if ret == None:
            err = self.imaq.imaqGetLastError()
            err_txt = self.imaq.imaqGetErrorText(err)
            raise RuntimeError('NI-IMAQ call failed with error %d: %s'%(err, err_txt))
        else:
            return ret
        
        
    def _checkdx(self, ret):
        """Checks NI-IMAQdx error messages, prints results"""
        if ret != 0:
            buf_size = 128
            buf = create_string_buffer('\000' * buf_size)
            self.imaqdx.IMAQdxGetErrorString(ret,byref(buf),buf_size)
            raise RuntimeError('NI-IMAQdx call failed with error %d: %s'%(ret,repr(buf.value)))
        else: 
            return ret
        
        




    
    
    
