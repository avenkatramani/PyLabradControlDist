# -*- coding: utf-8 -*-
"""
Created on Fri May 27 14:21:09 2016

@author: AdityaVignesh
"""
"""
### BEGIN NODE INFO
[info]
name = plotter
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
from multiprocessing import Process
from plotting_class_pyqtgraph import plot_pyqtgraph
import numpy as np
import datetime as dt
import ujson as json 
import os

class Plotter(LabradServer):
    name = 'plotter'
        
    def initServer(self):
        self.plotter = plot_pyqtgraph()
        self.plot_data = {}
            
    @setting(0, plot_type='s', plot_params = 's', plot_ID = 'w')    
    def plot_init(self, c, plot_type, plot_params, plot_ID):
        plot_params = eval(plot_params) 
        self.plot_data[str(plot_ID)] = {}
        self.plot_data[str(plot_ID)]['plot_type'] = plot_type
        self.plot_data[str(plot_ID)]['plot_params'] = plot_params
        
        p = Process(target=self.plotter.plot_init, args=(plot_type, plot_params, plot_ID))
        p.start()
                    
    onNotification_p = Signal(543617, 'signal: plot', 's')
    @setting(1, data='s', plot_ID = 'w')     
    def plot(self, c, data, plot_ID):
        self.process_data(data, plot_ID) 
        self.onNotification_p(json.dumps([plot_ID,self.plot_data[str(plot_ID)]]))  
        
    onNotification_s = Signal(543618, 'signal: save', 's')    
    @setting(2, plot_ID = 'w', save_path = 's', save_prefixes = 's')     
    def save(self, c, plot_ID, save_path, save_prefixes): 
        self.onNotification_s(json.dumps([save_path,eval(save_prefixes)]))  
        
        
    def process_data(self, data, plot_ID):
        plot_ID = str(plot_ID)
        if self.plot_data[plot_ID]['plot_type'] == 'Single Frequency':
            data = eval(data)
            sources = self.plot_data[plot_ID]['plot_params']['sources']
            averages = self.plot_data[plot_ID]['plot_params']['averaging']

            if 'data_raw' not in self.plot_data[plot_ID].keys():
                self.plot_data[plot_ID]['data_raw'] = {}
                for source in sources:
                    self.plot_data[plot_ID]['data_raw'][source] = []  #All data

            if 'data' not in self.plot_data[plot_ID].keys():
                self.plot_data[plot_ID]['data'] = {}
                for source in sources:
                   self.plot_data[plot_ID]['data'][source] = [] # To be plotted      
            
            for source in sources:
                self.plot_data[plot_ID]['data_raw'][source].append(data[source])
                #Keeping say 20 points
                if len(self.plot_data[plot_ID]['data_raw'][source]) > 100*averages :
                    self.plot_data[plot_ID]['data_raw'][source] = self.plot_data[plot_ID]['data_raw'][source][averages::] #keep removing the first element
                
                data_len = len(self.plot_data[plot_ID]['data_raw'][source])
                data_len_plot = data_len - data_len%averages
                data_plot = self.plot_data[plot_ID]['data_raw'][source][0:data_len_plot*averages]
                data_avg = np.array(data_plot[0::averages])
                if averages > 1:
                    for count in xrange(averages-1):
                        data_avg += np.array(data_plot[count+1::averages])
                    
                data_avg /= averages
                self.plot_data[plot_ID]['data'][source] = data_avg.tolist()
                    
                    
        if self.plot_data[plot_ID]['plot_type'] == 'Frequency Scan':
            data = eval(data)
            sources = self.plot_data[plot_ID]['plot_params']['sources']
            averages = self.plot_data[plot_ID]['plot_params']['averaging']

            if 'data_raw' not in self.plot_data[plot_ID].keys():
                self.plot_data[plot_ID]['data_raw'] = {}
                for source in sources:
                    self.plot_data[plot_ID]['data_raw'][source] = []  #All data

            if 'data' not in self.plot_data[plot_ID].keys():
                self.plot_data[plot_ID]['data'] = {}
                for source in sources:
                   self.plot_data[plot_ID]['data'][source] = [] # To be plotted
                   

            for source in sources:
                self.plot_data[plot_ID]['data_raw'][source].append(data[source])
                data_len = len(self.plot_data[plot_ID]['data_raw'][source])
                data_len_plot = data_len - data_len%averages
                data_plot = self.plot_data[plot_ID]['data_raw'][source][0:data_len_plot]
                data_avg = np.array(data_plot[0::averages])
                for count in xrange(averages-1):
                    data_avg += np.array(data_plot[count+1::averages])
                        #data_avg += np.pad(temp,(0,len_0-len(temp)),'constant')
                    
                data_avg /= averages
                self.plot_data[plot_ID]['data'][source] = data_avg.tolist()
                
                
        if self.plot_data[plot_ID]['plot_type'] == 'Fast Scan':
            data = eval(data)
            sources = self.plot_data[plot_ID]['plot_params']['sources']
            averages = self.plot_data[plot_ID]['plot_params']['averaging']

            if 'data_raw' not in self.plot_data[plot_ID].keys():
                self.plot_data[plot_ID]['data_raw'] = {}
                for source in sources:
                    self.plot_data[plot_ID]['data_raw'][source] = []  #All data

            if 'data' not in self.plot_data[plot_ID].keys():
                self.plot_data[plot_ID]['data'] = {}
                for source in sources:
                   self.plot_data[plot_ID]['data'][source] = [] # To be plotted
                   

            for source in sources:
                plot_len = len(data[source])
                data_len = len(self.plot_data[plot_ID]['data_raw'][source])
                if data_len < plot_len*(averages-1):
                    self.plot_data[plot_ID]['data_raw'][source].extend(data[source])
                else:
                    self.plot_data[plot_ID]['data_raw'][source] = self.plot_data[plot_ID]['data_raw'][source][plot_len:]
                    self.plot_data[plot_ID]['data_raw'][source].extend(data[source])
                    data_plot = self.plot_data[plot_ID]['data_raw'][source]
                    data_avg = np.array(data_plot[0:plot_len])
                    for count in xrange(averages-1):
                        data_avg += np.array(data_plot[plot_len*count:plot_len*(count+1)])
                    data_avg /= averages
                    self.plot_data[plot_ID]['data'][source] = data_avg.tolist()
                
                
        if self.plot_data[plot_ID]['plot_type'] == 'Camera':
            with open('X:\Our Programs\New Labrad Setup\PyLabradControl\TEMP\\'+data, 'r') as infile:
                self.plot_data[plot_ID]['data'] = json.load(infile)
            
            

        

if __name__ == '__main__':
    
    from labrad import util
    util.runServer(Plotter())