# -*- coding: utf-8 -*-
"""
Created on Thu Apr 14 13:12:29 2016

@author: AdityaVignesh

This is the probably the longest script that we will have in this software. Though Qt is very flexible, this flexibility requires us to define evey 
single detail like what happens when you right click a list, or when you double click a table... Its pretty straight forward even though it is a bit long.


It is possible to unify many functions between the import and current tabs to reduce the number of lines of code

I have attempted to write come comments but is not very detailed at the moment. Will update them in the future. 

(Maybe add some functions to make this more organized ?)
"""

import sys
from PyQt4 import QtCore, QtGui
from Timing_Client_Class import Ui_TimingClient
import pandas as pd
import numpy as np
from functools import partial
import re
import labrad
import time
import yaml
from twisted.internet.defer import inlineCallbacks  #The plan was to connect to Labrad and the timing server async, so that there is no
#problem when opening this when labrad is off. Not implemented yet, but could be important 

class StartQT4(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_TimingClient()
        self.ui.setupUi(self)
        
        #Pandas Dataframes
        
        init_index = pd.MultiIndex(levels = [[],[],[],[]],
                                   labels = [[],[],[],[]],
                                   names = ['Sequence','Device','Property','Time']) 
        init_columns = ['Ramp','Value']
        self.ImportedDf = pd.DataFrame(index = init_index, columns = init_columns)
        self.CurrentDf = pd.DataFrame(index = init_index, columns = init_columns)
        
        self.connect_labrad()
        
        self.device_dict = self.get_device_dict()
        
        self.ui.Close.clicked.connect(self.close)
        
        # Import
        
        #buttons
        self.ui.Import.clicked.connect(self.file_dialog) #Loading timing sequence file.
        self.ui.ImportSave.clicked.connect(partial(self.file_save, window="Import"))
                       
        #List and Tables 
               
        self.ui.ImportGraphSeqList.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.ui.ImportValuesSeqList.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.ui.ImportGraphDevList.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.ui.ImportValuesDevList.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
                        
        self.ui.ImportGraphSeqList.itemClicked.connect(partial(self.populate_DeviceList, view_type='Graph'))
        self.ui.ImportValuesSeqList.itemClicked.connect(partial(self.populate_DeviceList, view_type='Values'))
        
        self.ui.ImportGraphSeqList.itemChanged.connect(partial(self.populate_DeviceList, view_type='Graph'))
        self.ui.ImportValuesSeqList.itemChanged.connect(partial(self.populate_DeviceList, view_type='Values'))
        
        self.ui.ImportGraphDevList.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection) #Making sure that we can select multiple devices for viewing
        self.ui.ImportValuesDevList.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        
        self.ui.ImportGraphDevList.itemClicked.connect(partial(self.view_selected_devices, view_type='Graph'))
        self.ui.ImportValuesDevList.itemClicked.connect(partial(self.view_selected_devices, view_type='Values'))
    
        #Table
             
        self.ui.ImportValuesListTable.setColumnCount(20)   #Setting up an initial count. As we load more data into it, the number of rows change dynamically (Need to make sure that the coluumns do as well)
        for i in range(20):
            if i in [0,1,2,4]:
                self.ui.ImportValuesListTable.setColumnWidth(i, 75)
            elif i in [3]:
                self.ui.ImportValuesListTable.setColumnWidth(i, 20)
            else:
                self.ui.ImportValuesListTable.setColumnWidth(i, 50)
                
        self.ui.ImportValuesListTable.setRowCount(4)
        for i in range(4):
            if i in [0,1,2]:
                self.ui.ImportValuesListTable.setRowHeight(i, 20)
            if i in [3]:
                self.ui.ImportValuesListTable.setRowHeight(i, 10)
            
                
        self.ui.ImportValuesListTable.setHorizontalHeaderLabels(["SEQ", "Device", "Property", "", "Values"]+[""]*15)
        
        self.ui.ImportValuesListTable.cellChanged.connect(partial(self.update_imported_DF_table, action= "Edited"))
        self.ui.ImportValuesListTable.cellClicked.connect(partial(self.update_imported_DF_table, action="Activated")) 
        self.ui.ImportValuesListTable.cellDoubleClicked.connect(partial(self.update_imported_DF_table, action="Activated")) 
        self.ui.ImportValuesListTable.cellActivated.connect(partial(self.update_imported_DF_table, action="Activated")) 
              
        self.import_table_current_selection = 0     
        
        self.ui.ImportValuesListTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.ImportValuesListTable.customContextMenuRequested.connect(partial(self.showTableMenu, view_type='Values'))
        
        
        
        # List Context
        
        self.ui.ImportValuesSeqList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.ImportValuesSeqList.customContextMenuRequested.connect(partial(self.showListMenu, view_type='Sequence'))

        self.ui.ImportValuesDevList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.ImportValuesDevList.customContextMenuRequested.connect(partial(self.showListMenu, view_type='Device'))        
     
    
       #Current
    
    
    
    
        #buttons
        self.ui.Update.clicked.connect(self.update_button_click)
        self.ui.CurrentSave.clicked.connect(partial(self.file_save, window="Current"))
                               
        #List and Tables - Can set up columnwidths if necessary   
              
        self.ui.CurrentGraphSeqList.itemClicked.connect(partial(self.populate_current_DeviceList, view_type='Graph'))
        self.ui.CurrentValuesSeqList.itemClicked.connect(partial(self.populate_current_DeviceList, view_type='Values'))
        
        self.ui.CurrentValuesDevList.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        
        self.ui.CurrentValuesDevList.itemClicked.connect(partial(self.view_current_selected_devices, view_type='Values'))
    
        #Table
             
        self.ui.CurrentValuesListTable.setColumnCount(20)  
        for i in range(20):
            if i in [0,1,2,4]:
                self.ui.CurrentValuesListTable.setColumnWidth(i, 75)
            elif i in [3]:
                self.ui.CurrentValuesListTable.setColumnWidth(i, 20)
            else:
                self.ui.CurrentValuesListTable.setColumnWidth(i, 50)
             
        self.ui.CurrentValuesListTable.setHorizontalHeaderLabels(["SEQ", "Device", "Property", "", "Values"]+[""]*15)
        
        self.ui.CurrentValuesListTable.cellChanged.connect(partial(self.update_current_DF_table, action= "Edited"))
        self.ui.CurrentValuesListTable.cellClicked.connect(partial(self.update_current_DF_table, action="Activated")) 
        self.ui.CurrentValuesListTable.cellDoubleClicked.connect(partial(self.update_current_DF_table, action="Activated")) 
        self.ui.CurrentValuesListTable.cellActivated.connect(partial(self.update_current_DF_table, action="Activated")) 
              
        self.current_table_selection = 0
        
        self.ui.CurrentValuesListTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.CurrentValuesListTable.customContextMenuRequested.connect(partial(self.showTableMenu, view_type='Values'))
        
        # List Context
        
        self.ui.CurrentValuesSeqList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.CurrentValuesSeqList.customContextMenuRequested.connect(partial(self.showListMenu, view_type='Sequence'))

        self.ui.CurrentValuesDevList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.CurrentValuesDevList.customContextMenuRequested.connect(partial(self.showListMenu, view_type='Device'))        
   

####Other Functions  ------ sort later ########

    def get_device_dict(self):
        with open('C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Servers\DeviceConfig.yaml', 'r') as f:
            deviceConfig = yaml.load(f)
         
        device_dict = {}
        for k in deviceConfig.keys():
            property_dict = deviceConfig[k]['properties']
            device_dict[k] = property_dict.keys()
        
        return device_dict

####Functions that are associated with Labrad ######
        
    def signal_handler(self, message_ctx, data): # To receive messages from the timing client
        self.CurrentDf = pd.DataFrame().from_dict(eval(data))
        self.populate_current_seq_list()
        print('Recieved Signal')
        
    def connect_labrad(self):
        notification_ID = 4444        
        
        cxn = labrad.connect()
        self.cxn = cxn
        server = self.cxn.timingcontrol    #deal with this if the timing client is not open
        cxn._backend.cxn.addListener(self.signal_handler, source=server.ID, context=None,  ID = notification_ID) 
        server.signal__test(notification_ID)
           
        
##################################################
  

#####Functions that deal with the imported tab ###########


    def update_imported_DF_table(self, row, column, action): 
        #detect only changes in the property and timing for now
        if action == "Activated":
            self.import_table_current_selection = str(self.ui.ImportValuesListTable.item(row, column).text())
            print('yay')
                
        elif action == "Edited":   
            if self.ui.ImportValuesListTable.selectedItems() != []:  
                repopulate_sequence_list = 1
                clear_device_list = 1
                self.ImportedDf.sortlevel(inplace=True)
                sequence = str(self.ui.ImportValuesListTable.item(row - row%4, 0).text())
                device = str(self.ui.ImportValuesListTable.item(row - row%4, 1).text())
                prop = str(self.ui.ImportValuesListTable.item(row - row%4 + 1, 2).text())
                
                if column == 0 and row%4 == 0:
                    self.ImportedDf = self.ImportedDf.drop((self.import_table_current_selection, device, prop))
                
                if column == 1 and row%4 == 0:
                    repopulate_sequence_list = 0
                    self.ImportedDf = self.ImportedDf.drop((sequence, self.import_table_current_selection, prop))
                
                if column == 2 and row%4 == 1:
                    repopulate_sequence_list = 0
                    clear_device_list = 0
                    self.ImportedDf = self.ImportedDf.drop((sequence,device,self.import_table_current_selection))
                
                elif column >= 4:
                    repopulate_sequence_list = 0
                    clear_device_list = 0
                    self.ImportedDf = self.ImportedDf.drop((sequence,device,prop))
                
                time_indices = []
                
                for index in xrange(self.ui.ImportValuesListTable.columnCount() - 4):
                    value = self.ui.ImportValuesListTable.item(row - row%4, index + 4)
                    if value != None:
                        time_indices.append(float(value.text()))
                
                
                for i in xrange(len(time_indices)):
                    ramp = float(self.ui.ImportValuesListTable.item(row - row%4 + 2, i + 4).text())
                    value = float(self.ui.ImportValuesListTable.item(row - row%4 + 1, i + 4).text())
                    print(ramp)
                    print(value)
                    print(time_indices[i])
                    
                    self.ImportedDf.ix[(sequence, device, prop, time_indices[i])] = [ramp, value]
                
                if repopulate_sequence_list:
                    self.populate_seq_list()
                if clear_device_list:
                    self.ui.ImportValuesDevList.clear() 
                  
        
    def get_device_and_property(self):
        devices = self.device_dict.keys()
        device, device_ok = QtGui.QInputDialog.getItem(self, "Device Select", "Device list", devices, 0, False)
        device = str(device)        
        if not(device_ok):
            return ["", False, "", False]
           
        properties = self.device_dict[device]
        prop, prop_ok = QtGui.QInputDialog.getItem(self, "Property Select", "Property list", properties, 0, False)
        prop = str(prop)    
        return [device, device_ok, prop, prop_ok]      
        
         
    
    def showListMenu(self, pos, view_type):  #Function to add new sequences and devices. Not necessary for current tab
            
            if view_type == 'Sequence':
                menu= QtGui.QMenu(self)
                new_Seq = menu.addAction("New Sequence")
                delete = menu.addAction("Delete")
                action = menu.exec_(self.ui.ImportValuesSeqList.mapToGlobal(pos))
                
                if action == new_Seq:
                    
                    [device, device_ok, prop, prop_ok] = self.get_device_and_property()
                    
                    if not(device_ok) or not(prop_ok):
                        return 1                        
                        
                    item = QtGui.QListWidgetItem(self.ui.ImportValuesSeqList)
                    
                    items = []
                    for index in xrange(self.ui.ImportValuesSeqList.count()):
                        items.append(self.ui.ImportValuesSeqList.item(index))
                    
                                
                    new_seqs = map(lambda x: x.group(), filter(lambda x: x != None, [re.search(r'New Sequence \d+', i.text()) for i in items]))
                    
                    
                    if new_seqs == []:
                        
                        item.setText("New Sequence 0")  # Make this new sequence i and simultaneously create a new device for this sequence and a new property and 0 time
                                                
                        self.ImportedDf.ix[("New Sequence 0", device, prop, 0)] = [0,0]
                                                
                    else:
                    
                        max_new = max([int(re.search(r'\d+', str(seq)).group()) for seq in new_seqs])
                        item.setText("New Sequence "+ str(max_new+1))  # Make this new sequence i and simultaneously create a new device for this sequence and a new property and 0 time
                        self.ImportedDf.ix[("New Sequence "+ str(max_new+1), device, prop, 0)] = [0,0]
                       
                    item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                    self.ui.ImportGraphDevList.clear() 
                    
                elif action == delete:
                    
                    for item in self.ui.ImportValuesSeqList.selectedItems():
                        self.ImportedDf = self.ImportedDF.drop((str(item.text())))
                        self.populate_seq_list()
                        item_index = self.ui.ImportValuesSeqList.row(item)
                        self.ui.ImportValuesSeqList.takeItem(item_index)
                        
            
            elif view_type == 'Device':
                menu= QtGui.QMenu(self)
                new_Dev = menu.addAction("New Device") # Make this new device i to prevent conflicts in the database. Also create a new property and 0 time
                delete = menu.addAction("Delete")
                action = menu.exec_(self.ui.ImportValuesDevList.mapToGlobal(pos))
                
                if action == new_Dev:
                    [device, device_ok, prop, prop_ok] = self.get_device_and_property()
                    if not(device_ok) or not(prop_ok):
                        return 1   
                    
                    item = QtGui.QListWidgetItem(self.ui.ImportValuesDevList)
                    item.setText(device)  # Make this new sequence i and simultaneously create a new device for this sequence and a new property and 0 time
                    self.ImportedDf.ix[(str(self.ui.ImportValuesSeqList.currentItem().text()), device, prop, 0)] = [0,0]
                        
                     
                    item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                    
                elif action == delete:
                    for item in self.ui.ImportValuesDevList.selectedItems():
                        seq = self.ui.ImportValuesSeqList.currentItem().text()
                        self.ImportedDf = self.ImportedDF.drop([seq, item.text()])
                        self.populate_Devicelist(self, seq, "Values")
                        item_index = self.ui.ImportValuesDevList.row(item)
                        self.ui.ImportValuesDevList.takeItem(item_index)


    def view_selected_devices(self, devices, view_type): #This will be the central processing and visualizing function
        # Work on graph later, not very important for now
        
        if view_type == 'Values':
            selected_seq = str(self.ui.ImportValuesSeqList.currentItem().text())
            selected_devices = map(lambda x: str(x.text()), self.ui.ImportValuesDevList.selectedItems())
                        
            display_matrix = []
            self.ui.ImportValuesListTable.clearContents()
            
            for i in selected_devices:
                current_device = self.ImportedDf.ix[selected_seq].ix[i]    
                for j in np.unique(current_device.index.get_level_values('Property')): #parsing through the device properties                
                    display_matrix.append([selected_seq,i,'Time','']+list(current_device.ix[j].index.get_level_values('Time')))                  
                    display_matrix.append(['','',j,'']+list(current_device.ix[j]['Value']))
                    display_matrix.append(['','','Ramp','']+list(current_device.ix[j]['Ramp']))  
                    display_matrix.append([''])
                    
            
            #self.ui.ImportValuesListTable.setColumnCount(max(map(len,display_matrix)))    #Setting a fixed column count for now and updating row count dynamically
            self.ui.ImportValuesListTable.setRowCount(len(display_matrix) + 3)
            
            for i in range(len(display_matrix) + 3):
                if i%4 in [0,1,2]:
                    self.ui.ImportValuesListTable.setRowHeight(i, 20)
                if i%4 in [3]:
                    self.ui.ImportValuesListTable.setRowHeight(i, 10)
                
            for i in range(len(display_matrix)):
                for j in range(len(display_matrix[i])):
                    
                    # This code is there just to show how to diable, but not going to implement that for others right now
                    
                    if j == 0 and i%4 == 0: #i.e the first column and every 4th row. Cannot Choose sequence for now
                        item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                        self.ui.ImportValuesListTable.setItem(i,j,item)
                    
                    elif j == 0: #Disable all other cells in the first column
                        item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                        item.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled) #Disbling modification of these empty cells
                        self.ui.ImportValuesListTable.setItem(i,j,item)

                    elif j in [1,2,3]: #Disable all other cells in the first column
                        item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                        item.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled) #Disbling modification of these empty cells
                        self.ui.ImportValuesListTable.setItem(i,j,item)
                        
                    elif i == 3: #Disable all other cells in the first column
                        item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                        item.setFlags(QtCore.Qt.NoItemFlags) #Disbling modification of these empty cells
                        self.ui.ImportValuesListTable.setItem(i,j,item)
                    
                    
                    else:
                        item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                        self.ui.ImportValuesListTable.setItem(i,j,item)
            
            
                        
            
        elif view_type == 'Graph':
            1
            
    def showTableMenu(self, pos, view_type):   
        if view_type == 'Values':
            menu= QtGui.QMenu(self)
            insert_Column = menu.addAction("Insert Column Right") # Not implemented yet
            add_Row = menu.addAction("Add Row") #Might not be necessary. Not implemented yet.
            delete = menu.addAction("Delete")
            action = menu.exec_(self.ui.ImportValuesListTable.mapToGlobal(pos))
            
            if action == delete:
                
                for item in self.ui.ImportValuesListTable.selectedItems(): #This seems to work ?
                    item_index = self.ui.ImportValuesListTable.row(item)
                    seq = str(self.ui.ImportValuesListTable.item(item_index - item_index%4, 0).text())
                    device = str(self.ui.ImportValuesListTable.item(item_index - item_index%4, 1).text())
                    prop = str(self.ui.ImportValuesListTable.item(item_index - item_index%4 + 1, 2).text())
                    
                                        
                    self.ImportedDf = self.ImportedDf.drop((seq,device, prop))
                    if seq in self.ImportedDf.index.get_level_values(0):
                        self.populate_DeviceList(self.ui.ImportValuesSeqList.currentItem(), "Values")
                    
                    else:
                        self.ui.ImportValuesDevList.clear() 
                        self.populate_seq_list()
                        
                        
                    self.ui.ImportValuesListTable.removeRow(item_index - item_index%4)
                    self.ui.ImportValuesListTable.removeRow(item_index - item_index%4)
                    self.ui.ImportValuesListTable.removeRow(item_index - item_index%4)
                    self.ui.ImportValuesListTable.removeRow(item_index - item_index%4)
                    
            elif action == add_Row:
                1
            elif action == insert_Column:
                1       
    
    def populate_DeviceList(self,sequence, view_type):
        
        if view_type == 'Graph':
            self.ui.ImportGraphDevList.clear() 
            
            for device in np.unique(np.unique(self.ImportedDf.ix[str(sequence.text())].index.get_level_values('Device'))):
                
                item_graph = QtGui.QListWidgetItem(self.ui.ImportGraphDevList)
                item_graph.setText(device)
                item_graph.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
        
        elif view_type == 'Values':
            self.ui.ImportValuesDevList.clear() 
            try:
                devices = np.unique(self.ImportedDf.ix[str(sequence.text())].index.get_level_values('Device'))
                for device in devices:
                    item_values = QtGui.QListWidgetItem(self.ui.ImportValuesDevList)
                    item_values.setText(device)
                    item_values.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                    
            except:
                print('Yet to be populated')
            
    
     
    
    def populate_seq_list(self):  #Not necessary for current tab
        self.ui.ImportValuesSeqList.clear() 
        self.ui.ImportGraphSeqList.clear() 
        for sequence in np.unique(self.ImportedDf.index.get_level_values('Sequence')):
            
            item_graph = QtGui.QListWidgetItem(self.ui.ImportGraphSeqList)
            item_graph.setText(sequence)
            item_graph.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
            
            item_values = QtGui.QListWidgetItem(self.ui.ImportValuesSeqList)
            item_values.setText(sequence)
            item_values.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                    
############################################
      
      
###### Functions that deal with the current tab ######
               
    def update_current_DF_table(self, row, column, action): 
        #detect only changes in the timing for now
        if action == "Edited":   
            if self.ui.CurrentValuesListTable.selectedItems() != []:  
                self.CurrentDf.sortlevel(inplace=True)
                sequence = str(self.ui.CurrentValuesListTable.item(row - row%4, 0).text())
                device = str(self.ui.CurrentValuesListTable.item(row - row%4, 1).text())
                prop = str(self.ui.CurrentValuesListTable.item(row - row%4 + 1, 2).text())
                self.CurrentDf = self.CurrentDf.drop((sequence,device,prop))
                
                time_indices = []
                
                for index in xrange(self.ui.CurrentValuesListTable.columnCount() - 4):
                    value = self.ui.CurrentValuesListTable.item(row - row%4, index + 4)
                    if value != None:
                        time_indices.append(float(value.text()))
                
                
                for i in xrange(len(time_indices)):
                    ramp = float(self.ui.CurrentValuesListTable.item(row - row%4 + 2, i + 4).text())
                    value = float(self.ui.CurrentValuesListTable.item(row - row%4 + 1, i + 4).text())
                    print(ramp)
                    print(value)
                    print(time_indices[i])
                    
                    self.CurrentDf.ix[(sequence, device, prop, time_indices[i])] = [ramp, value]
                
                if self.ui.AutoUpdate.isChecked():
                    self.cxn.timingcontrol.update_df(str(self.CurrentDf.to_dict()))  #Can keep track of sequence, device and property if necessary
                    
    def update_button_click(self):
        self.cxn.timingcontrol.update_df(str(self.CurrentDf.to_dict()))
        
    def populate_current_seq_list(self):
        self.ui.CurrentValuesSeqList.clear() 
        self.ui.CurrentGraphSeqList.clear() 
        for sequence in np.unique(self.CurrentDf.index.get_level_values(0)):
            item_graph = QtGui.QListWidgetItem(self.ui.CurrentGraphSeqList)
            item_graph.setText(sequence)
            item_graph.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
            
            item_values = QtGui.QListWidgetItem(self.ui.CurrentValuesSeqList)
            item_values.setText(sequence)
            item_values.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
          
    def populate_current_DeviceList(self,sequence,view_type):
              
        if view_type == 'Graph':
            self.ui.CurrentGraphDevList.clear() 
            
            for device in np.unique(np.unique(self.CurrentDf.ix[str(sequence.text())].index.get_level_values(0))):
                
                item_graph = QtGui.QListWidgetItem(self.ui.CurrentGraphDevList)
                item_graph.setText(device)
                item_graph.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
        
        elif view_type == 'Values':
            self.ui.CurrentValuesDevList.clear() 
            try:
                devices = np.unique(self.CurrentDf.ix[str(sequence.text())].index.get_level_values(0))
                for device in devices:
                    item_values = QtGui.QListWidgetItem(self.ui.CurrentValuesDevList)
                    item_values.setText(device)
                    item_values.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                    
            except:
                print('Yet to be populated')
                
    def view_current_selected_devices(self, devices, view_type): #This will be the central processing and visualizing function
    # Work on graph later, not very important for now
      if view_type == 'Values':
          selected_seq = str(self.ui.CurrentValuesSeqList.currentItem().text())
          selected_devices = map(lambda x: str(x.text()), self.ui.CurrentValuesDevList.selectedItems())
                    
          display_matrix = []
          self.ui.CurrentValuesListTable.clearContents()
        
          for i in selected_devices:
              current_device = self.CurrentDf.ix[selected_seq].ix[i]    
              for j in np.unique(current_device.index.get_level_values(0)): #parsing through the device properties                
                  display_matrix.append([selected_seq,i,'Time','']+list(current_device.ix[j].index.get_level_values(0)))                  
                  display_matrix.append(['','',j,'']+list(current_device.ix[j]['Value']))
                  display_matrix.append(['','','Ramp','']+list(current_device.ix[j]['Ramp']))  
                  display_matrix.append([''])
                
        
          self.ui.CurrentValuesListTable.setRowCount(len(display_matrix))
          for i in range(len(display_matrix)):
                if i%4 in [0,1,2]:
                    self.ui.CurrentValuesListTable.setRowHeight(i, 20)
                if i%4 in [3]:
                    self.ui.CurrentValuesListTable.setRowHeight(i, 10)
                    
          for i in range(len(display_matrix)):
              for j in range(len(display_matrix[i])):
                    
                if j in [0,1,2,3]: #Disable all other cells in the first to fourth column
                    item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                    item.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled) #Disbling modification of these empty cells
                    self.ui.CurrentValuesListTable.setItem(i,j,item)
   
                elif i%4 == 3: #Disable all 4th row
                    item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                    item.setFlags(QtCore.Qt.NoItemFlags) #Disbling modification of these empty cells
                    self.ui.CurrentValuesListTable.setItem(i,j,item)
                
                else:
                    item = QtGui.QTableWidgetItem(str(display_matrix[i][j]))
                    item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                    self.ui.CurrentValuesListTable.setItem(i,j,item)
        
                    
        
      elif view_type == 'Graph':
          1             
###############################################
   
        
    
###### Function for both current and import tabs examples #####    
    def file_save(self, window):
        #file_location = str(QtGui.QFileDialog.getSaveFileName(self, "Export to Excel", "", 'Excel File (*.xlsx)'))
        file_location = 'C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences'
        # Write file saving
        
        if window == "Import":
            sequences = np.unique(self.ImportedDf.index.get_level_values(0)).tolist()
            for sequence in sequences:
                sequence_folder = sequence.split('_')[0]
                writer = pd.ExcelWriter(file_location+'\\'+sequence_folder+'\\'+sequence+'.xlsx')
                self.ImportedDf.xs(sequence).to_excel(writer)
                writer.save()
                
        elif window == "Current":
            sequences = np.unique(self.CurrentDf.index.get_level_values(0)).tolist()
            for sequence in sequences:
                sequence_folder = sequence.split('_')[0]
                writer = pd.ExcelWriter(file_location+'\\'+sequence_folder+'\\'+sequence+'.xlsx')
                self.CurrentDf.xs(sequence).to_excel(writer)
                writer.save()
            
            
        
        
   
#######################################################   





######## Other miscellenaeous functions ##########

    def file_dialog(self):
        fd = QtGui.QFileDialog(self)
        file_location = str(fd.getOpenFileName())
        file_type = file_location.split('.')[1]   
        if file_type == 'txt':
            
            with open(file_location, 'r') as f:
                allSequences = f.readlines()
            allSequences = [x.strip('\n') for x in allSequences]
            df_list = []
            address = 'C:\Users\RoyOutput\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Sequences'
            for sequence in allSequences:
                sequence_folder = sequence.split('_')[0]
                df_list.append(pd.read_excel(address+'\\'+sequence_folder+'\\'+sequence+'.xlsx', index_col = [0,1,2]))
            
            self.ImportedDf = pd.concat(df_list, keys = allSequences, names = ['Sequence'])
                                
        self.populate_seq_list()

    def closeEvent(self, event): 
        print "Closing" 
        self.destroy() 
        
#################################################                
    
    
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = StartQT4()
    myapp.show()
    sys.exit(app.exec_())
    