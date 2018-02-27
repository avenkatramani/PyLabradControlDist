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

class MOT_Imaging(do_experiment):
    
    def __init__(self): # initialize specific parameters
               
        name = 'MOT Imaging'
        expt_suffix = ''
        """INSERT notes on experiment here - eg: what it does, what changed from other versions, etc. 


        """
                
        sequence_path = 'C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences'
        save_path = 'C:\\Users\\RoyOutput\\Dropbox (MIT)\\2017-data\\2017-07\\20170722\\'
        save_path = save_path + name+'_' + expt_suffix+'\\'
        save_parameters = []
        num_repeats = np.Inf 
        
        parameters = {}
        
        
        ######### IDx 0 #############
        
        
        ########## Data acquisition parameters ##########
        parameters[0,'acquisition_time_s'] = [np.Inf]     # Use np.Inf for running continuously.      
        parameters[0,'acquisition_delay_s'] = [0] 
        parameters[0, 'DAQ_mode'] = [['Camera']] 
        parameters[0, 'save_data'] = [True]
        
        ######### Plotting ########
        # plot is referenced by ID. {ID: {parameteres}}
        
        parameters[0,'plots'] = {}
        
        
        plot_ID = 3
        parameters[0,'plots'][plot_ID] = {}
        parameters[0,'plots'][plot_ID]['plot'] = True
        parameters[0,'plots'][plot_ID]['plot_type'] = 'Camera'
        
        
        
        parameters[0,'plots'] = [parameters[0,'plots']]
        
        ######### Sequences #########
        parameters[0,'Sequences'] = [
                                     [['MOT_500ms', 1],['Imaging_Absorption_MOT', 1]]
                                    ]
                               
         
########## DO NOT TOUCH THESE ###############        
        sequences = self.get_sequences(parameters)  
        expt_file = os.path.basename(sys.argv[0]) 
        
        
        super(MOT_Imaging, self).__init__(expt_file, name, sequence_path, sequences, save_path, save_parameters, num_repeats, parameters)
    
    
    
    def get_sequences(self,parameters):
        sequences = []
        for key in parameters.keys():
            if key[1] == 'Sequences':
                for sequence_order_list in parameters[(key[0], 'Sequences')]:
                    sequences.extend(self.get_sequences_from_order_list(sequence_order_list))
        
        sequences = np.unique(sequences).tolist()          
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
    a = MOT_Imaging()
    a.run()
   