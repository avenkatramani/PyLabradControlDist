#
# Server for Analog Outout NI6733
#
#Based off NI6535_Digital Server
#Modified by Sergio and Aditya 07/2016

# NOTE - I'm making analog card A the master card for defining the sample clock (routed to other NI cards through RTSI)
# and the start trigger, routed through RTSI and PFI (for PulseBlaster). Ideally would use the Digital card to do this to 
# restore symmety with the Analog cards. The NI MAX shows no connections between the sampleclock and RTSI, but it seems to work ?
# Also, we would need to wire up the PFI pins for the digital card (is readily avaiable for the all analog cards) 

"""
### BEGIN NODE INFO
[info]
name = arduino
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
import serial
import time

class Arduino(LabradServer):
    """ANALOG output server"""

    name="arduino"
    
    
    def initServer(self):
        self.ser = None

    @setting(100,"arduino_send",port='s', dev_list = '*i', processed_data = 's')
    def arduino_send(self, c, port, dev_list, processed_data):
        if self.ser == None:
            self.ser = serial.Serial(port, 9600)
            time.sleep(1)
            
        processed_data = eval(processed_data)
        

        for dev in dev_list:
            self.ser.write(chr(dev)) 
            data_list = processed_data[dev]
            send_length = len(data_list)
            self.ser.write(chr(send_length))
            for i in range(send_length):
                highest_digit_1 = (int(data_list[i]) & 0b111111110000000000000000)>>16
                middle_digit_1 = (int(data_list[i]) & 0b1111111100000000)>>8
                lowest_digit_1 = (int(data_list[i]) & 0b11111111)
                
                self.ser.write(chr(highest_digit_1)) 
                self.ser.write(chr(middle_digit_1))            
                self.ser.write(chr(lowest_digit_1))
        
    def stopServer(self):
        self.ser.close()

 
    
    
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(Arduino())
