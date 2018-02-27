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
import labrad
from labrad import types as T
import numpy as np
import datetime as dt
import sys
import os
from scipy import signal
import scipy.interpolate

sys.setrecursionlimit(100000000)

class Probe_Scan(do_experiment):
    
    def __init__(self): # initialize specific parameters
               
        name = 'Probe Scan'
        expt_suffix = 'OD_3'
        
        """INSERT notes on experiment here - eg: what it does, what changed from other versions, etc. 
        """
                
        
        sequence_path = 'C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences'
        calib_path = 'C:\\Users\\RoyOutput\\Dropbox (MIT)\\Our Programs\\New Labrad Setup\\PyLabradControl\\Calibrations'
        save_path = 'C:\\Users\\RoyOutput\\Dropbox (MIT)\\2018-data\\2018-02\\20180226\\'
        save_path = save_path + name+'_' + expt_suffix+'\\'
        save_parameters = []
        num_repeats = np.Inf
        
        parameters = {}
        


        ######### IDx 0 #############
        
        
        ########## Data acquisition parameters ##########
        parameters['0','acquisition_time_s'] = [30.0] 
        parameters['1','acquisition_time_s'] = [0.1] 
        parameters[('0','1'),'acquisition_delay_s'] = [0.5]  
        parameters[('0','1'), 'DAQ_mode'] = [['Counter0','Counter1']]
        parameters['0', 'save_data'] = [False]
        parameters['1', 'save_data'] = [True]


        ########### Device Initialization #####
        
        ##probe shaping
        
        ArbV, AOMV = np.loadtxt(os.path.join(calib_path,'ProbeAOMcalibSmooth.csv'),delimiter=',', unpack = True)
        interpf2 = scipy.interpolate.interp1d(ArbV, AOMV)
        interpf = scipy.interpolate.interp1d(AOMV, ArbV)

        Pprobe = interpf2(0.27)#interpf2(0.43) #0.43 for 3 photons /mus, 2 for 15 photons /mus, 0.8 for 9 photons/ mus
        Tflat = 8 # time in microseconds of  of pulse
        
        #wfm = np.max(AOMV)*np.round(np.array(list(1.0*signal.blackman(400)[0:199]) + [1]*int((Tflat)*100)+ list(1.0*signal.blackman(400)[200:])), 2)
        wfm = np.max(AOMV)*np.round(np.array(list(1.0*signal.gaussian(400,150)[0:199]) + [1]*int((Tflat)*100)+ list(1.0*signal.gaussian(400,150)[200:])), 2)
        
        #wfm = np.max(AOMV)*np.round(np.array(list(1.0*signal.gaussian(400, 20) )),2)
        #wfm = np.tile(wfm,4)
        
        wfm = wfm - np.min(wfm)
        
        
        parameters['0', 'Device_initialization'] = {}
        parameters['0', 'Device_initialization']['Arb'] = {}
        parameters['0', 'Device_initialization']['Arb']['Probe'] = {}
        parameters['0', 'Device_initialization']['Arb']['Probe']['wfm_time'] =  (Tflat+4.0)*10**-6 # in seconds
        parameters['0', 'Device_initialization']['Arb']['Probe']['wfm'] = interpf(Pprobe*wfm)

        
        ##Ground Control
        parameters['0', 'Device_initialization']['Agilent SG8648'] = {}
        #parameters['0', 'Device_initialization']['Agilent SG8648']['onoff'] = False
        #parameters['0', 'Device_initialization']['Agilent SG8648']['Power'] = T.Value(14, 'dBm') # in seconds
        parameters['0', 'Device_initialization']['Agilent SG8648']['Freq'] = T.Value(1385.947-10+0.8, 'MHz') #-10+0.8
        
        
        parameters['0', 'Device_initialization'] = [parameters['0', 'Device_initialization']]

        #IMPORTANT NOTE - There will be timing problems with the analog card if any sequence is less than 10 mu s (or not a multiple of one). Need to fix this by modifying the final card programming stage
        
        ######### Sequences #########
        parameters[('0','1'),'Sequences'] = [
                                     [['MOT_500ms', 1],['MOT_compressed_10ms_40ms', 1],['Molasses', 1],['Molasses_turnoff_F1', 1],['DT_MOD_Pumping', 200],['SPCM On',1],['Probe_DT_MOD', 1600], ['Counting Card Gate', 1],['HRM Time_Filler_MOD', 256],['Imaging_Absorption_Molasses_DT', 1]]
                                    ]
        ##probe frequencies
                            
        probe_step_list = np.array([])

        probe_center = 5646.24 # 940.7 -> 2to3 X field , 1119.0  -> 2to3 Z field,  5649.0 -> 1to2 X field
        probe_start = (probe_center-25.0)/16
        probe_stop = (probe_center-10.0)/16
        probe_step = 0.4/16
        probe_step_list = np.append(probe_step_list,np.arange(probe_start, probe_stop, probe_step))
        
        probe_start = (probe_center-10.0)/16
        probe_stop = (probe_center+10.0)/16
        probe_step = 0.4/16
        probe_step_list = np.append(probe_step_list,np.arange(probe_start, probe_stop, probe_step))
        
        probe_start = (probe_center+10.0)/16
        probe_stop = (probe_center+25.0)/16
        probe_step = 0.4/16
        probe_step_list = np.append(probe_step_list,np.arange(probe_start, probe_stop, probe_step))
        
        
        parameters['1', 'probe_frequency'] = np.repeat(probe_step_list,1)
        ######### Plotting ########
        # plot is referenced by ID. {ID: {parameteres}}`
        
        parameters['1','plots'] = {}  

        plot_ID = 1
        parameters['1','plots'][plot_ID] = {}
        parameters['1','plots'][plot_ID]['plot'] = True
        parameters['1','plots'][plot_ID]['plot_type'] = 'Frequency Scan'
        parameters['1','plots'][plot_ID]['sources'] = ['Counter0','Counter1'] # Implement consistency check with DAQ mode         
        parameters['1','plots'][plot_ID]['averaging'] = 1
        parameters['1','plots'][plot_ID]['Frequency Range'] = (16*probe_step_list).tolist()
#        
#        plot_ID = 3
#        parameters['0','plots'][plot_ID] = {}
#        parameters['0','plots'][plot_ID]['plot'] = True
#        parameters['0','plots'][plot_ID]['plot_type'] = 'Camera'       
#        
        parameters['1','plots'] = [parameters['1','plots']]
        
        

########## DO NOT TOUCH THESE ###############   
        sequences = self.get_sequences(parameters)  
        expt_file = os.path.basename(sys.argv[0]) 
        
        
        super(Probe_Scan, self).__init__(expt_file, name, sequence_path, sequences, save_path, save_parameters, num_repeats, parameters)
    
    
    
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
   