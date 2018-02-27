# -*- coding: utf-8 -*-
"""
Created on Tue May 10 11:08:57 2016

@author: AdityaVignesh

This is the file that contains all the details about the experiment. It is written as a class so that 
we can define some variables as well as some functions. It inherits the properties from a class (do_experiment and exp_params for now ).
Those classes will will know how to process the information provided here.

Required parameters (could change in future) : name, sequence path, save path, number repeats, and parameters. 
Parameters can take in any detail required for implementing the experiment like acquisition time, data anaylsis method, sequences, 
device properties, and so on...

Some notes on how looping is implemented : The looping is parsed in the experimental client, but the test experiment uses the parsed loops and 
runs them one after the other. The loop is done two fold. One is over ID's (the first entry in the tuple) and each of the parameters.
Each parameters is written as a list. To loop over we just add more elements to the list. The ID helps with looping over disjoint sets of parameters.
Within each ID, the looping takes every possible combination of parameters.  

"""

from Experiment_Client import do_experiment
import numpy as np
import datetime as dt
import sys
import os
import pandas as pd
import scipy.interpolate
from scipy import signal

class Probe_Scan(do_experiment):
    
    def __init__(self): # initialize specific parameters
               
        name = 'Probe Scan'
        expt_suffix = 'Efield1'
        """INSERT notes on experiment here - eg: what it does, what changed from other versions, etc. 
       
        """
                
        
        sequence_path = 'C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences'
        calib_path = 'C:\\Users\\RoyOutput\\Dropbox (MIT)\\Our Programs\\New Labrad Setup\\PyLabradControl\\Calibrations'
        save_path = 'C:\\Users\\RoyOutput\\Dropbox (MIT)\\2018-data\\2018-02\\20180217\\'
        save_path = save_path + name+'_' + expt_suffix+'\\'
        save_parameters = []
        num_repeats = np.Inf
        
        parameters = {}
        

        ##########Scanning X,Y,Z, electic fields
        x = 0.017
        y = 0.03
        z = 0.003
        scan_start = -0.1
        scan_stop = 0.1
        scan_step = 0.02
        scan_range = np.arange(scan_start, scan_stop+scan_step, scan_step)
        
        init_index = pd.MultiIndex(levels = [[],[],[]],
                                   labels = [[],[],[]],
                                   names = ['Device','Property','Time']) 
        init_columns = ['Ramp','Value']
        MOT_Df = pd.DataFrame(index = init_index, columns = init_columns)
        MOT_Df = pd.read_excel('C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences\MOT\MOT_500ms.xlsx', index_col = [0,1,2])
            
        id_list = []
#        for scan_item in scan_range:
#            ID = ',Vx='+str(round(x,3))+',Vy='+str(round(y,3))+',Vz='+str(round(z+scan_item,3))
#            id_list.append(ID)
#            MOT_Df.ix[('Field Plates', 'Vx', 0)] = [0, round(x,3)]
#            MOT_Df.ix[('Field Plates', 'Vx', 0.5)] = [0, round(x,3)]
#            MOT_Df.ix[('Field Plates', 'Vy', 0)] = [0, round(y,3)]
#            MOT_Df.ix[('Field Plates', 'Vy', 0.5)] = [0, round(y,3)]
#            MOT_Df.ix[('Field Plates', 'Vz', 0)] = [0, round(z+scan_item,3)]
#            MOT_Df.ix[('Field Plates', 'Vz', 0.5)] = [0, round(z+scan_item,3)]
#            writer = pd.ExcelWriter('C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences\MOT\MOT_500ms'+ID+'.xlsx')
#            MOT_Df.to_excel(writer)
#            writer.save()  
#            
#            
#        for scan_item in scan_range:
#            ID = ',Vx='+str(round(x,3))+',Vy='+str(round(y+scan_item,3))+',Vz='+str(round(z,3))
#            id_list.append(ID)
#            MOT_Df.ix[('Field Plates', 'Vx', 0)] = [0, round(x,3)]
#            MOT_Df.ix[('Field Plates', 'Vx', 0.5)] = [0, round(x,3)]
#            MOT_Df.ix[('Field Plates', 'Vy', 0)] = [0, round(y+scan_item,3)]
#            MOT_Df.ix[('Field Plates', 'Vy', 0.5)] = [0, round(y+scan_item,3)]
#            MOT_Df.ix[('Field Plates', 'Vz', 0)] = [0, round(z,3)]
#            MOT_Df.ix[('Field Plates', 'Vz', 0.5)] = [0, round(z,3)]
#            writer = pd.ExcelWriter('C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences\MOT\MOT_500ms'+ID+'.xlsx')
#            MOT_Df.to_excel(writer)
#            writer.save()  
            
            
        for scan_item in scan_range:
            ID = ',Vx='+str(round(x+scan_item,3))+',Vy='+str(round(y,3))+',Vz='+str(round(z,3))
            id_list.append(ID)
            MOT_Df.ix[('Field Plates', 'Vx', 0)] = [0, round(x+scan_item,3)]
            MOT_Df.ix[('Field Plates', 'Vx', 0.5)] = [0, round(x+scan_item,3)]
            MOT_Df.ix[('Field Plates', 'Vy', 0)] = [0, round(y,3)]
            MOT_Df.ix[('Field Plates', 'Vy', 0.5)] = [0, round(y,3)]
            MOT_Df.ix[('Field Plates', 'Vz', 0)] = [0, round(z,3)]
            MOT_Df.ix[('Field Plates', 'Vz', 0.5)] = [0, round(z,3)]
            writer = pd.ExcelWriter('C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences\MOT\MOT_500ms'+ID+'.xlsx')
            MOT_Df.to_excel(writer)
            writer.save()  
        
        id_list = tuple(id_list)
        
        ########## Data acquisition parameters ##########
        parameters[id_list,'acquisition_time_s'] = [0.1] 
        parameters[id_list,'acquisition_delay_s'] = [0]  
        parameters[id_list, 'DAQ_mode'] = [[ 'Counter0','Counter1']]
        parameters[id_list, 'save_data'] = [True]


        
        #IMPORTANT NOTE - There will be timing problems with the analog card if any sequence is less than 10 mu s (or not a multiple of one). Need to fix this by modifying the final card programming stage
        ######### Sequences #########
                
        for ID in id_list:
            parameters[ID,'Sequences'] = [
                                             [['MOT_500ms'+ID, 1],['MOT_compressed_10ms_40ms', 1],['Molasses', 1],['Molasses_turnoff_F1', 1],['SPCM On',1],['Probe_DT_MOD', 1600], ['Counting Card Gate', 1],['HRM Time_Filler_MOD', 256],['Imaging_Absorption_Molasses_DT', 1]]
                                         ]


        probe_center = 5646.24 #
        probe_start = (probe_center-5.0)/16
        probe_stop = (probe_center+5.0)/16
        probe_step = 1*0.1/16
        
        parameters[id_list, 'probe_frequency'] = np.repeat(np.arange(probe_start, probe_stop, probe_step),1)
        
        ##probe shaping
        
        ArbV, AOMV = np.loadtxt(os.path.join(calib_path,'ProbeAOMcalib.csv'),delimiter=',', unpack = True)
        interpf2 = scipy.interpolate.interp1d(ArbV, AOMV)
        interpf = scipy.interpolate.interp1d(AOMV, ArbV)

        Pprobe = interpf2(0.15)#interpf2(0.43) #0.43 for 3 photons /mus, 2 for 15 photons /mus, 0.8 for 9 photons/ mus
        Tflat = 8  # time in microseconds of  of pulse
        
        wfm = np.max(AOMV)*np.round(np.array(list(1.0*signal.gaussian(400,150)[0:199]) + [1]*int((Tflat)*100)+ list(1.0*signal.gaussian(400,150)[200:])), 2)
        wfm = wfm - np.min(wfm)

        parameters[id_list, 'Device_initialization'] = {}
        parameters[id_list, 'Device_initialization']['Arb'] = {}
        parameters[id_list, 'Device_initialization']['Arb']['Probe'] = {}
        parameters[id_list, 'Device_initialization']['Arb']['Probe']['wfm_time'] = (Tflat+4.0)*10**-6 # in seconds
        parameters[id_list, 'Device_initialization']['Arb']['Probe']['wfm'] = interpf(Pprobe*wfm)

        parameters[id_list, 'Device_initialization'] = [parameters[id_list, 'Device_initialization']]
        ######### Plotting ########
        # plot is referenced by ID. {ID: {parameteres}}`
        
        parameters[id_list,'plots'] = {}  

        plot_ID = 1
        parameters[id_list,'plots'][plot_ID] = {}
        parameters[id_list,'plots'][plot_ID]['plot'] = True
        parameters[id_list,'plots'][plot_ID]['plot_type'] = 'Frequency Scan'
        parameters[id_list,'plots'][plot_ID]['sources'] = ['Counter0','Counter1'] # Implement consistency check with DAQ mode         
        parameters[id_list,'plots'][plot_ID]['averaging'] = 1
        parameters[id_list,'plots'][plot_ID]['Frequency Range'] = np.arange(16*probe_start, 16*probe_stop, 16*probe_step).tolist()
        
      
        parameters[id_list,'plots'] = [parameters[id_list,'plots']]
        
        

########## DO NOT TOUCH THESE ###############   
        sequences = self.get_sequences(parameters)  
        expt_file = os.path.basename(sys.argv[0]) 
        
        
        super(Probe_Scan, self).__init__(expt_file, name, sequence_path, sequences, save_path, save_parameters, num_repeats, parameters)
    
    
    def delete_sequence_files():
        1
        
        
        
    def get_sequences(self,parameters):
        sequences = []
        for key in parameters.keys():
            if key[1] == 'Sequences':
                for sequence_order_list in parameters[(key[0], 'Sequences')]:
                    sequences.extend(self.get_sequences_from_order_list(sequence_order_list))
        
        sequences = np.unique(sequences).tolist()  
        print sequences          
        return sequences
                
    def get_sequences_from_order_list(self,sequence_order_list):  #This function picks out all the sequences from the order list. Could be pushed to the card programmer
        if len(sequence_order_list) == 1:
            if type(sequence_order_list[0][0]) != type([]): #I think this should be sufficient, keep an eye out for this condition
                return [sequence_order_list[0][0]]
            else:
                return self.get_sequences_from_order_list(sequence_order_list[0][0])+self.get_sequences_from_order_list(sequence_order_list[0][0])
        else:
            return self.get_sequences_from_order_list([sequence_order_list[0]]) + self.get_sequences_from_order_list(sequence_order_list[1::])
                
            
if __name__ == '__main__':
    a = Probe_Scan()
    a.labrad_connect()
    a.run()
    a.delete_sequence_files()
   