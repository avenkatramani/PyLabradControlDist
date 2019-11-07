# -*- coding: utf-8 -*-
"""
Created on Tue May 10 11:08:57 2016

@author: AdityaVignesh



This is a superclass of the experimental class. The exp params is something that every experiment will use. The class below exp_params
(do_experiment for example) will contain functions/ variables specific to certain types of experiments.

Need to take some of the functions written in test_Expt should be moved to do_experiment.

To simplify handling card programming and timing, I have asserted that everything that goes through the timing server must
go to the cards. Anything that does not go through the card means that it is acceptable to have programming delays and it therefore
becomes easier for the experimental client to handle device programming though the device servers instead of integrating that into the timing
(This may seem a little inconvenient in terms of having the highest level of abstraction, but is a lot easier to deal with)

"""

# This contains classes that process the experimental data. This will be a super class of the actual experiment client 


import labrad
from labrad import types as T
import labrad.units as U
import numpy as np
import datetime as dt     
import sys
import time
import msvcrt
import os 
import shutil
import yaml
import types

class exp_params(object):
    
    def __init__(self, expt_file, name, sequence_path, sequences, save_path, save_parameters, num_repeats, parameters):    
        # Identification for this experiemnt
        self.expt_file = expt_file
        self.name = name
        self.sequence_path = sequence_path
        self.allSequences = sequences
        self.save_path = save_path
        self.save_paramters = save_parameters
        self.num_repeats = num_repeats
        self.parameters = parameters
        self.previous_parameters = {}
        self.Counter0Data = []
        self.Counter1Data = []
        self.Counter2Data = []
        self.Counter3Data = []
        self.cameradata = []
        self.cameraPlot = 0       
        self.labrad_connect()
        self.hrm_result = 0
        if sequences != []:
            self.cxn.timingcontrol.load_seqs_file(sequence_path, str(sequences))    # Load the timing server database
        
        
class do_experiment(exp_params):
    
    def __init__(self, *args): # Check if this will work
        super(do_experiment, self).__init__(*args)
                    
    def run(self): 
        
        '''
        Loop over parameters creates a list of experiments parsed from the repeats (lists) in the experiment description file.
        It is grouped by ID. The idea behind this is that we will initialize only once the first time for a given ID. This allows
        us to scan over parameters without having to recompile sequences/ setup counting cards/ plots again. If you need to reinitialize
        a sequence - 
        
        1) Use a different ID. To avoid rewriting parameters in the experiment description file, parameters that 
        constant over multiple IDs can be write the IDs as a tuple. 
        
        2) To scan over a parameter in s sequence, use the parameter key 'Sequences_scan' and this should initialize the sequences again
        '''
        
        parameter_loop = self.loop_over_parameters(self.parameters) 
        for parameters_ID in parameter_loop:
            ID = parameters_ID[0]
            num_parameters = len(parameters_ID[1])
            for ix in xrange(num_parameters):
                if ix == 0 and ix == num_parameters -1:
                    self.run_expt(ID, parameters_ID[1][ix], 1, 1)
                elif ix == 0:
                    self.run_expt(ID, parameters_ID[1][ix], 1, 0)
                elif ix == num_parameters -1:
                    self.run_expt(ID, parameters_ID[1][ix], 0, 1)
                else:
                    self.run_expt(ID, parameters_ID[1][ix], 0, 0)
                    
                
                if msvcrt.kbhit():
                    if msvcrt.getwche() == '\r':
                        break
            
            
    def run_expt(self, ID, parameters, initial, last): 
        keys = parameters.keys()
        
        ################## Initialization #############################
               
        self.initialize(ID, parameters, initial)
        self.previous_parameters = parameters
        repeat_count = 0
        ################# Repeats ############################### 
        
        start_time = dt.datetime.now() 
        if 'acquisition_time_s' in keys:
            print('New Parameter')
            
            while (dt.datetime.now() - start_time).total_seconds() < parameters['acquisition_time_s']:   #insert some break for infinite loops....        Figure out how to deal with infinite time...
                loop_time = dt.datetime.now()
                repeat_count += 1
                if repeat_count <= self.num_repeats:
                    self.acquire(parameters)
                    self.save(ID, parameters)
                    
                else:
                    break
                    
                while (dt.datetime.now() - loop_time).total_seconds() < parameters['acquisition_delay_s']:   #insert some break for infinite loops....        Figure out how to deal with infinite time...
                    1
          
        ############# Finishing ##################    
        self.finish(ID, parameters, last)           
                   
    			
#################### Helper Functions ############################   

    def labrad_connect(self):
        cxn = labrad.connect("RoyDAQ-PC",password="p")
        self.cxn = cxn    
    
    def acquire(self, parameters): 
        self.cycle += 1
        start_time = dt.datetime.now()
        keys = parameters.keys()    
        if 'HRM_Time' in parameters['DAQ_mode'] and parameters['save_data'] == True:
            # Note that this hopes that the setup does not take more time than it the time it takes to get to the probing stage
            #p = self.cxn.hrmtime.packet()
            #p.acquire()
            #p.send_future()
            1#self.cxn.hrmtime.acquire()
        if 'DAQ_mode' in keys:
            ###DAQ
            if 'Counter0' in parameters['DAQ_mode']:
                self.cxn.countingcards.startcounter(0)
            if 'Counter1' in parameters['DAQ_mode']:
                self.cxn.countingcards.startcounter(1)
            if 'Counter2' in parameters['DAQ_mode']:
                self.cxn.countingcards.startcounter(2)
            if 'Counter3' in parameters['DAQ_mode']:
                self.cxn.countingcards.startcounter(3)
            if 'HRM_Time' in parameters['DAQ_mode'] and parameters['save_data'] == True:
                self.cxn.hrmtime.acquire()
        
                        
        if 'Sequences' in keys:
            ###Cards
            self.update_and_start_cards(parameters)  
            
      
        if 'DAQ_mode' in keys:
            ###DAQ
            if 'Counter0' in parameters['DAQ_mode']:
                if 'DAQ_mode_properties' in parameters.keys():
                    if 'Counter0' in parameters['DAQ_mode_properties'].keys():
                        if 'Num Gates' in parameters['DAQ_mode_properties']['Counter0'].keys():
                            num_gates = parameters['DAQ_mode_properties']['Counter0']['Num Gates']
                            self.Counter0Data.extend(self.cxn.countingcards.readcounter(0)[0:num_gates].tolist())
                    else:
                        self.Counter0Data.extend([self.cxn.countingcards.readcounter(0)[0]])
                        
                    
                else:
                    temp = self.cxn.countingcards.readcounter(0)
                    self.Counter0Data.extend([temp[0]])
                self.cxn.countingcards.stopcounter(0)
                
            if 'Counter1' in parameters['DAQ_mode']:
                if 'DAQ_mode_properties' in parameters.keys():
                    if 'Counter1' in parameters['DAQ_mode_properties'].keys():
                        if 'Num Gates' in parameters['DAQ_mode_properties']['Counter1'].keys():
                            num_gates = parameters['DAQ_mode_properties']['Counter1']['Num Gates']
                            self.Counter1Data.extend(self.cxn.countingcards.readcounter(1)[0:num_gates].tolist())
                
                    else:
                        self.Counter1Data.extend([self.cxn.countingcards.readcounter(1)[0]])
                else:
                    temp = self.cxn.countingcards.readcounter(1)
                    self.Counter1Data.extend([temp[0]])
                self.cxn.countingcards.stopcounter(1)
                
            if 'Counter2' in parameters['DAQ_mode']:
                if 'DAQ_mode_properties' in parameters.keys():
                    if 'Counter2' in parameters['DAQ_mode_properties'].keys():
                        if 'Num Gates' in parameters['DAQ_mode_properties']['Counter2'].keys():
                            num_gates = parameters['DAQ_mode_properties']['Counter2']['Num Gates']
                            temp = self.cxn.countingcards.readcounter(2)[0:num_gates]
                            temp2 = (temp+np.arange(1,num_gates+1,1)*10).tolist()
                            self.Counter2Data.extend(temp2)
                    else:
                        self.Counter2Data.extend([self.cxn.countingcards.readcounter(2)[0]])
                    
                else:
                    temp = self.cxn.countingcards.readcounter(2)
                    self.Counter2Data.extend([temp[0]])
                self.cxn.countingcards.stopcounter(2)
                
            if 'Counter3' in parameters['DAQ_mode']:
                if 'DAQ_mode_properties' in parameters.keys():
                    if 'Counter3' in parameters['DAQ_mode_properties'].keys():
                        if 'Num Gates' in parameters['DAQ_mode_properties']['Counter3'].keys():
                            num_gates = parameters['DAQ_mode_properties']['Counter3']['Num Gates']
                            temp = self.cxn.countingcards.readcounter(3)[0:num_gates]
                            temp2 = (temp+np.arange(1,num_gates+1,1)*10).tolist()
                            self.Counter3Data.extend(temp2)
                    else:
                        self.Counter3Data.extend([self.cxn.countingcards.readcounter(3)[0]])
                    
                else:
                    temp = self.cxn.countingcards.readcounter(3)
                    self.Counter3Data.extend([temp[0]])
                self.cxn.countingcards.stopcounter(3)
                
            if 'Camera' in parameters['DAQ_mode']:
                start_time_camera = dt.datetime.now()
                self.cameradata_file = self.cxn.camera.acquire()
                print('Camera acquire time :' + str((dt.datetime.now() - start_time_camera)))  
                
            if 'Photodetector 1' in parameters['DAQ_mode']:
                self.photodetector1.append(self.cxn.photodetector.acquire('Photodetector 1'))
                
            if 'Osc1' in parameters['DAQ_mode']:
                self.Osc1.extend([self.cxn.tds2014c_a.mean(1)])
                
            if 'Osc2' in parameters['DAQ_mode']:
                self.Osc2.extend([self.cxn.tds2014c_a.mean(2)])
            
            if 'Osc3' in parameters['DAQ_mode']:
                self.Osc3.extend([self.cxn.tds2014c_a.mean(3)])
                
            if 'Osc4' in parameters['DAQ_mode']:
                self.Osc4.extend([self.cxn.tds2014c_a.mean(4)])
 
            if 'HRM_Time' in parameters['DAQ_mode'] and parameters['save_data'] == True:
                if self.hrm_result != 0:
                    result  = self.hrm_result.result()                  
                self.cxn.hrmtime.read()
                #self.cxn.hrmtime.process(self.cycle)
                
                p = self.cxn.hrmtime.packet()
                p.process(self.cycle)
                self.hrm_result = p.send_future()
                


               
        if 'plots' in keys:
            plot_IDs = parameters['plots'].keys()
            for plot_ID in plot_IDs:
                if parameters['plots'][plot_ID]['plot'] == True:  #Push below to the plotting server...
                    plot_type = parameters['plots'][plot_ID]['plot_type']
                    
                    if plot_type == 'Single Frequency':
                        
                        sources = parameters['plots'][plot_ID]['sources']
                        data = {}
                        for source in sources:
                            if source == 'Counter0':
                                data['Counter0'] = self.Counter0Data[-1]
                                
                            if source == 'Counter1':
                                data['Counter1'] = self.Counter1Data[-1]

                            if source == 'Counter2':
                                data['Counter2'] = self.Counter2Data[-1]

                            if source == 'Counter3':
                                data['Counter3'] = self.Counter3Data[-1]

                            if source == 'Osc1':
                                data['Osc1'] = self.Osc1[-1]
                                
                            if source == 'Osc2':
                                data['Osc2'] = self.Osc2[-1]

                            if source == 'Osc3':
                                data['Osc3'] = self.Osc3[-1]

                            if source == 'Osc4':
                                data['Osc4'] = self.Osc4[-1]
                        
                        p = self.cxn.plotter.packet()
                        p.plot(str(data), plot_ID)
                        p.send_future()
                        
                    
                    if plot_type == 'Frequency Scan':
                        sources = parameters['plots'][plot_ID]['sources']
                        data = {}
                        for source in sources:
                            if source == 'Counter0':
                                data['Counter0'] = self.Counter0Data[-1]
                                
                            if source == 'Counter1':
                                data['Counter1'] = self.Counter1Data[-1]

                            if source == 'Counter0+1':
                                data['Counter0+1'] = (self.Counter0Data[-1]+self.Counter1Data[-1])/2.0

                            if source == 'Counter2':
                                data['Counter2'] = self.Counter2Data[-1]
                
                            if source == 'Counter3':
                                data['Counter3'] = self.Counter3Data[-1]

                            if source == 'Photodetector 1':
                                data['Photodetector 1'] = self.photodetector1[-1]
                        
                        p = self.cxn.plotter.packet()
                        p.plot(str(data), plot_ID)
                        p.send_future()
                        
                        
                    
                    if plot_type == 'Fast Scan':
                        sources = parameters['plots'][plot_ID]['sources']
                        data = {}
                        for source in sources:
                            if source == 'Counter0':
                                num_gates = parameters['DAQ_mode_properties']['Counter0']['Num Gates']
                                data['Counter0'] = (np.array(self.Counter0Data[-num_gates:]) - np.array([0]+self.Counter0Data[-num_gates:-1])).tolist()
                                
                            if source == 'Counter1':
                                num_gates = parameters['DAQ_mode_properties']['Counter1']['Num Gates']
                                data['Counter1'] = (np.array(self.Counter1Data[-num_gates:]) - np.array([0]+self.Counter1Data[-num_gates:-1])).tolist()
                            
                            if source == 'Counter0+1':
                                num_gates = parameters['DAQ_mode_properties']['Counter0']['Num Gates']
                                data['Counter0+1'] = ((np.array(self.Counter0Data[-num_gates:]) - np.array([0]+self.Counter0Data[-num_gates:-1]))+(np.array(self.Counter1Data[-num_gates:]) - np.array([0]+self.Counter1Data[-num_gates:-1]))).tolist()
                                
                            if source == 'Counter2':
                                num_gates = parameters['DAQ_mode_properties']['Counter2']['Num Gates']
                                data['Counter2'] = (np.array(self.Counter2Data[-num_gates:]) - np.array([0]+self.Counter2Data[-num_gates:-1])).tolist()
                                
                            if source == 'Counter3':
                                num_gates = parameters['DAQ_mode_properties']['Counter3']['Num Gates']
                                data['Counter3'] = (np.array(self.Counter3Data[-num_gates:]) - np.array([0]+self.Counter3Data[-num_gates:-1])).tolist()
                        
                        p = self.cxn.plotter.packet()
                        p.plot(str(data), plot_ID)
                        p.send_future()
                        
                        
                    
                    if plot_type == 'Camera':
                        #self.cameraPlot = self.cxn.plotter.plot(self.cameradata_file, plot_ID)
                        if self.cameraPlot != 0:
                            result  = self.cameraPlot.result()    
                        p = self.cxn.plotter.packet()
                        p.plot(self.cameradata_file, plot_ID)
                        self.cameraPlot = p.send_future()
                        
                        
            if 'Monitor' in keys:
                if 'Control AOM' in parameters['Monitor'].keys():
                    device = 'Control AOM'
                    prop = parameters['Monitor']['Control AOM']['Property']
                    seqs = str(parameters['Monitor']['Control AOM']['Sequences'])
                    set_point = parameters['Monitor']['Control AOM']['Set Point']
                    step = parameters['Monitor']['Control AOM']['Update Step']
                    self.cxn.aom.monitor_and_update(device, prop, seqs, set_point, step)
                              
        
        print('Acquire time :' + str((dt.datetime.now() - start_time)))  
        
        
    def save(self, ID, parameters):
        keys = parameters.keys()
        if 'save_data' in keys:
            if parameters['save_data'] == True:
                   
                if 'DAQ_mode' in keys:
                    if not os.path.exists(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'):
                        os.makedirs(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data')
                    
                    if 'Counter0' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Counter0.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Counter0Data)
                        self.Counter0Data = []
                    if 'Counter1' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Counter1.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Counter1Data)
                        self.Counter1Data = []
                    if 'Counter2' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Counter2.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Counter2Data)
                        self.Counter2Data = []
                    if 'Counter3' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Counter3.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Counter3Data)
                        self.Counter3Data = []
                    if 'Osc1' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Osc1.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Osc1)
                        self.Osc1 = []
                    if 'Osc2' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Osc2.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Osc2)
                        self.Osc2 = []
                    if 'Osc3' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Osc3.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Osc3)
                        self.Osc3 = []
                    if 'Osc4' in parameters['DAQ_mode']:
                        with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\Data'+'\\Osc4.txt','a') as f_handle:
                            np.savetxt(f_handle,self.Osc4)
                        self.Osc4 = []

                    
        
    def finish(self, ID, parameters, last):
        keys = parameters.keys()
        
        if 'save_data' in keys:
            if parameters['save_data'] == True:
                
                ############# Saving plot and plot data ##############   
                if last:  
                    if 'DAQ_mode' in keys:
                        if 'HRM_Time' in parameters['DAQ_mode'] and parameters['save_data'] == True:
                            self.cxn.hrmtime.stop()
        
                
                    if 'plots' in keys:
                        if not os.path.exists(self.save_path+'\\Expt_Index_'+str(ID)+'\\Plots'):
                            os.makedirs(self.save_path+'\\Expt_Index_'+str(ID)+'\\Plots')
                        save_path = self.save_path+'\\Expt_Index_'+str(ID)+'\\Plots'+'\\'
                        plot_IDs = parameters['plots'].keys()
                        for plot_ID in plot_IDs:
                            if 'save_prefixes' in parameters['plots'][plot_ID]:
                                save_prefixes = parameters['plots'][plot_ID]['save_prefixes'] + np.arange(1,100,1).tolist()
                            else:
                                save_prefixes = np.arange(1,100,1).tolist()
                            self.cxn.plotter.save(plot_ID, save_path, str(save_prefixes))




            
    def initialize(self, ID, parameters, initial): #Check and initilize anything necessary. Not really checking now, but to be implemented soon
        keys = parameters.keys()  
        self.cycle = 0
            
        if ('Device_initialization' in keys) and initial:
            if 'PTS Fast Scan Params' in parameters['Device_initialization'].keys():
                if 'Probe' in parameters['Device_initialization']['PTS Fast Scan Params'].keys():
                    min_freq = parameters['Device_initialization']['PTS Fast Scan Params']['Probe']['Min Freq'] 
                    max_freq = parameters['Device_initialization']['PTS Fast Scan Params']['Probe']['Max Freq'] 
                    step = parameters['Device_initialization']['PTS Fast Scan Params']['Probe']['Step'] 
                    self.cxn.pts.setup_fast_scan('Probe', min_freq*U.MHz, max_freq*U.MHz, step*U.MHz)
            
            if 'Arb' in parameters['Device_initialization'].keys():
                    if 'Probe' in parameters['Device_initialization']['Arb'].keys():
                        wfm_time = parameters['Device_initialization']['Arb']['Probe']['wfm_time']
                        wfm = parameters['Device_initialization']['Arb']['Probe']['wfm'] 
                        self.cxn.agilent_arb.arb(wfm_time, wfm)
                        
            if 'Agilent E8257D' in parameters['Device_initialization'].keys():
                    if 'Power' in parameters['Device_initialization']['Agilent E8257D'].keys():
                        power = parameters['Device_initialization']['Agilent E8257D']['Power']
                        self.cxn.agilente8257d.set_pow(T.Value(power, 'dBm'))
                    if 'Frequency' in parameters['Device_initialization']['Agilent E8257D'].keys():
                        freq = parameters['Device_initialization']['Agilent E8257D']['Frequency']
                        self.cxn.agilente8257d.set_freq(T.Value(freq, 'GHz'))
                        
            if 'Agilent SG8648' in parameters['Device_initialization'].keys():
                    if 'onoff' in parameters['Device_initialization']['Agilent SG8648'].keys():
                        b1  = parameters['Device_initialization']['Agilent SG8648']['onoff']
                        self.cxn.agilent_sg8648.RFonoff(b1)
                    if 'Power' in parameters['Device_initialization']['Agilent SG8648'].keys():
                        power2 = parameters['Device_initialization']['Agilent SG8648']['Power']
                        self.cxn.agilent_sg8648.setPower(power2)
                    if 'Freq' in parameters['Device_initialization']['Agilent SG8648'].keys():
                        freq2 = parameters['Device_initialization']['Agilent SG8648']['Freq']
                        self.cxn.agilent_sg8648.setFreq(freq2)                    
                
        if ('plots' in keys) and initial:
            plot_IDs = parameters['plots'].keys()
            for plot_ID in plot_IDs:
                if parameters['plots'][plot_ID]['plot'] == True:
                    plot_type = parameters['plots'][plot_ID]['plot_type']
                    plot_params_keys = filter(lambda x: x not in ['plot', 'plot_type'], parameters['plots'][plot_ID].keys() )               
                    plot_params = {}
                    for plot_params_key in plot_params_keys:
                        plot_params[plot_params_key] = parameters['plots'][plot_ID][plot_params_key]
                    
                    self.cxn.plotter.plot_init(plot_type, str(plot_params), plot_ID)
                
            
        if ('Sequences' in keys) :
            ###Cards
            if initial and ('Sequences_scan' not in keys):
                if self.previous_parameters == {}:
                    self.program_cards(parameters['Sequences'])
                elif parameters['Sequences'] == self.previous_parameters['Sequences']:
                    pass
                else:
                    self.program_cards(parameters['Sequences'])
            elif 'Sequences_scan' in keys:
                self.cxn.timingcontrol.update_sequences_scan(str(parameters['Sequences_scan'])) 
                self.program_cards(parameters['Sequences'])
        
            
        
        if 'probe_frequency' in keys :  #This must go into the lock device server
            ###PTS
            self.set_probe_frequency(parameters['probe_frequency'])
            
        if 'control_frequency' in keys:
            ###PTS
            self.set_control_frequency(parameters['control_frequency'])
        
        if 'ground_frequency' in keys:
            ###SG8648
            self.cxn.agilent_sg8648.setFreq(parameters['ground_frequency'])   
            
        if ('DAQ_mode' in keys) and initial:
            ###DAQ
            if 'Counter0' in parameters['DAQ_mode']:
                self.cxn.countingcards.setupcounter(0)
            if 'Counter1' in parameters['DAQ_mode']:
                self.cxn.countingcards.setupcounter(1) 
            if 'Counter2' in parameters['DAQ_mode']:
                self.cxn.countingcards.setupcounter(2) 
            if 'Counter3' in parameters['DAQ_mode']:
                self.cxn.countingcards.setupcounter(3) 
            if 'Photodetector 1' in parameters['DAQ_mode']:
                self.photodetector1 = []
            if 'Osc1' in parameters['DAQ_mode']:
                self.Osc1 = []
            if 'Osc2' in parameters['DAQ_mode']:
                self.Osc2 = []
            if 'Osc3' in parameters['DAQ_mode']:
                self.Osc3 = []
            if 'Osc4' in parameters['DAQ_mode']:
                self.Osc4 = []

            if 'HRM_Time' in parameters['DAQ_mode']  and parameters['save_data'] == True:
                gate_time_mus = parameters['DAQ_mode_properties']['HRM_Time']['gate_time_mus']
                save_prefix = parameters['DAQ_mode_properties']['HRM_Time']['save_prefix']
                self.cxn.hrmtime.setup(gate_time_mus,save_prefix+'\\Expt_Index_'+str(ID))     
                self.cxn.hrmtime.acquire()
                
        if 'save_data' in keys:
            if parameters['save_data'] == True:
                if not os.path.exists(self.save_path):
                    os.makedirs(self.save_path)
                
                cwd = os.getcwd()
                path = os.path.dirname(cwd)+'\\Servers'

                if not os.path.exists(self.save_path+'\\Servers'):
                    os.makedirs(self.save_path+'\\Servers')
                    for filename in os.listdir(path): 
                        if filename.endswith(".py") or filename.endswith(".yaml"):
                           shutil.copy(path+'\\'+filename, self.save_path+'\\Servers')
                           
                       
                if not os.path.exists(self.save_path+'\\ExptScript'):
                    os.makedirs(self.save_path+'\\ExptScript')
                    shutil.copy(cwd+'\\'+self.expt_file, self.save_path+'\\ExptScript')
                    shutil.copy(cwd+'\\'+'Experiment_Client.py', self.save_path+'\\ExptScript')
                
               
                if 'Sequences' in keys:
                    if not os.path.exists(self.save_path+'\\Sequence'):
                        os.makedirs(self.save_path+'\\Sequence')
                    
                    for sequence in self.allSequences:
                        sequence_folder = sequence.split('_')[0]
                        if not os.path.exists(self.save_path+'\\Sequence\\'+sequence_folder):
                            os.makedirs(self.save_path+'\\Sequence\\'+sequence_folder)
                            
                        shutil.copy(self.sequence_path+'\\'+sequence_folder+'\\'+sequence+'.xlsx', self.save_path+'\\Sequence\\'+sequence_folder)   
                        
                        
                 
                ################################################ 
                    
                ############# Save Current Params and Data in a separate folder for each new ID ##############    
                    
                if not os.path.exists(self.save_path+'\\Expt_Index_'+str(ID)+'\\CurrentParams'):
                    os.makedirs(self.save_path+'\\Expt_Index_'+str(ID)+'\\CurrentParams')
                    with open(self.save_path+'\\Expt_Index_'+str(ID)+'\\CurrentParams\\CurrentParams.yaml','w') as outfile:
                        yaml.dump(parameters,outfile)
        
    def set_probe_frequency(self, frequency):
        pts = self.cxn.pts()
        pts.set_freq('Probe', T.Value(frequency, 'MHz'))
        
    def set_control_frequency(self, frequency):
        pts = self.cxn.pts()
        pts.set_freq('Control', T.Value(frequency, 'MHz'))
        
    def program_cards(self, sequences):
        self.cxn.timingcontrol.program(str(sequences))
    
    def update_and_start_cards(self, parameters):
        data_updated = self.cxn.timingcontrol.check_df_change()
        if data_updated:
            self.program_cards(parameters['Sequences'])
            
            print('Cards Updated')
    
        temp = dt.datetime.now()
        #Block till cards are loaded:
        while self.cxn.sequenceprogrammer.cards_loaded() == 0:
            1
        
        self.cxn.sequenceprogrammer.start_cards()
        self.cxn.sequenceprogrammer.done() 
        self.cxn.sequenceprogrammer.stop_cards()
    
        print('Total Sequence time :' + str((dt.datetime.now() - temp)))
        
    def loop_over_parameters(self,parameters): # Pass the init sequence, or use the subclass function directly ?
        #Looping explained in the experiment file
        keys = parameters.keys()
        IDs  = []
        for key in keys:
            if isinstance(key[0], types.TupleType):
                IDs.extend(key[0])
            else:
                IDs.append(key[0])
                
        IDs = np.unique(IDs).tolist()
        
        parameters_loop = []
        def filterFunc(x, ID):
            ret = False
            if ID == x:
                ret = True
            if isinstance(x, types.TupleType)   :
                if ID in x:
                    ret = True                
            return ret        
        for ID in IDs:
            parameters_ID = {key[1]: parameters[key] for key in filter(lambda x: filterFunc(x[0], ID), parameters.keys())}
            parameters_loop.append([ID, self.loop_help({}, parameters_ID)])
        

        return parameters_loop
 

    def loop_help(self,unique_parameters, parameters): #Particularly inelegent... works for now, change later
       
        if len(parameters) == 0: #Checking if all keys have only one value
            return [unique_parameters]
        
        else:
            key = parameters.keys()[0]
            values = parameters[key]
            parameters_current = {k: parameters[k] for k in filter(lambda x: x != key, parameters.keys())}
            if len(values) == 1: 
               unique_parameters[key] = values[0]
               return self.loop_help(unique_parameters, parameters_current)
             
            else: 
               temp_dict = {k: unique_parameters[k] for k in unique_parameters.keys()}
               temp_dict[key] = values[0]
               parameters_current_temp = {k: parameters[k] for k in filter(lambda x: x != key, parameters.keys())}
               parameters_current_temp[key] = values[1::]
               return self.loop_help(temp_dict, parameters_current) + self.loop_help(unique_parameters, parameters_current_temp)
        
        
       