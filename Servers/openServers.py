# -*- coding: utf-8 -*-
"""
Created on Fri Aug 12 10:39:24 2016

@author: AdityaVignesh

This script 
"""

import os 
cwd = os.getcwd()
path = cwd+'\MustOpen'
not_run_list = ["Timing_Client_Class.py", "spincore.py", "Unibrain.py", "plotting_class_pyqtgraph.py"]

print(path)

for filename in os.listdir(path):
    if filename.endswith(".py"):
       if filename in not_run_list:
           pass
       else:
           os.startfile(path+'\\'+filename)