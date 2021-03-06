# -*- coding: utf-8 -*-
"""
Created on Fri May 27 14:21:09 2016

@asuthor: AdityaVignesh
"""
import json
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import datetime as dt
from scipy import optimize
import pyqtgraph.opengl as gl
import matplotlib as mpl
import matplotlib.cm as cm
from functools import partial
import os
import pyqtgraph.exporters
import labrad
import scipy.ndimage.interpolation as sp
from pyqtgraph.GraphicsScene import exportDialog

count = 0

topmag = 1.0/(1.5) # we are using a 10cm/15cm telescope for the top camera SC 2019/03/25  *)
sidemag = 1.0/(1.0) # we are using a 10cm/15cm telescope for the top camera SC 2019/03/25  *)

pos = np.linspace(0.75,1,10)
norm = mpl.colors.Normalize(vmin=0.75, vmax=1.0)
cmap = cm.hot
m = cm.ScalarMappable(norm=norm, cmap=cmap)
colors = m.to_rgba(np.linspace(0.75,1.0,10))
mp = pg.ColorMap(pos, colors)
lut = mp.getLookupTable(0.75, 1.0, 256)

class plot_pyqtgraph():

    def __init__(self):
        self.plot_ID = 0
        self.plot_type = ''
        self.data_out = np.array([[0]])
        self.plot_data = {}


    def connect_labrad(self):
        cxn = labrad.connect()
        self.cxn = cxn
        server = self.cxn.plotter    #deal with this if the timing client is not open
        cxn._backend.cxn.addListener(self.plot, source=server.ID, context=None,  ID = self.plot_ID)
        cxn._backend.cxn.addListener(self.save, source=server.ID, context=None,  ID = self.plot_ID+10000)
        server.signal__plot(self.plot_ID)
        server.signal__save(self.plot_ID+10000)


    def plot(self, c, data):
        data = json.loads(data)
        if data[0] == self.plot_ID:

            if (data[1] == 'Camera') or (data[1] =='Side Camera'):
                with open(data[2]['data']['Location'], 'r') as infile:
                    self.plot_data['data'] = json.load(infile)
            else:
                self.plot_data = data[2]



    def save(self, c, data):
        data = json.loads(data)
        self.plot_data['save'] = True
        self.plot_data['save_path'] = data[0]
        self.plot_data['save_prefixes'] = data[2] + np.arange(0,100,1).tolist()


    def plot_init(self, plot_type, plot_params, plot_ID):
        self.plot_ID = plot_ID
        self.plot_type = plot_type
        self.connect_labrad()

        if plot_type == 'Single Frequency': # Required parameters = sources, averaging #. Data will be in format {Source: value}
            sources = plot_params['sources'] #Acceptable sources - Counter 0/1/2/3.
            self.plot_data['sources'] = sources
            self.plot_data['data'] = {}
            for source in sources:
                self.plot_data['data'][source] = [] # To be plotted

            a = QtGui.QApplication( [] )

            win = pg.GraphicsWindow()
            win.resize(1000,600)
            win.setWindowTitle('Single Frequency')

            p1 = win.addPlot(title="Single Frequency")
            curves = {}
            for source in sources:
                if source == 'Counter0':
                    curves[source] = p1.plot(pen={'color':'y', 'width':5})
                elif source == 'Counter1':
                    curves[source] = p1.plot(pen={'color':'r', 'width':5})
                elif source == 'Counter2':
                    curves[source] = p1.plot(pen={'color':'w', 'width':5})
                elif source == 'Osc1':
                    curves[source] = p1.plot(pen={'color':'y', 'width':5})
                elif source == 'Osc2':
                    curves[source] = p1.plot(pen={'color':'r', 'width':5})
                elif source == 'Osc3':
                    curves[source] = p1.plot(pen={'color':'w', 'width':5})
                else:
                    curves[source] = p1.plot(pen={'color':'c', 'width':5})



            # Enable antialiasing for prettier plots
            pg.setConfigOptions(antialias=True)

            def update(timer):
                if 'save' in self.plot_data.keys():
                    if self.plot_data['save'] == True:
                        timer.stop()
                        save_path =  self.plot_data['save_path']
                        save_prefixes  = self.plot_data['save_prefixes']
                        exporter = pg.exporters.ImageExporter(p1)
                        exporterCSV = pg.exporters.CSVExporter(p1)
                        for save_prefix in save_prefixes:
                            if not os.path.exists(save_path+str(save_prefix)+'.png'):
                                exporter.export(save_path+str(save_prefix)+'.png')
                                exporterCSV.export(save_path+str(save_prefix)+'.csv')
                                break

                for source in sources:
                    data = self.plot_data['data'][source]
                    curves[source].setData(data)


            timer = QtCore.QTimer()
            timer.timeout.connect(partial(update,timer))
            timer.start(50)
            QtGui.QApplication.instance().exec_()



        elif plot_type == 'Frequency Scan': # Required parameters = sources, averaging #, Frequency Range. Data will be in format {Source: value}
            sources = plot_params['sources'] #Acceptable sources - Counter 0/1/2/3.
            frequencies = plot_params['Frequency Range']
            self.plot_data['sources'] = sources
            self.plot_data['data'] = {}

            for source in sources:
                self.plot_data['data'][source] = [] # To be plotted


            a = QtGui.QApplication( [] )

            win = pg.GraphicsWindow()
            win.resize(1000,600)
            win.setWindowTitle('Frequency Scan')

            p1 = win.addPlot(title="Frequency Scan")
            curves = {}
            for source in sources:
                if source == 'Counter0':
                    curves[source] = p1.plot(pen={'color':'y', 'width':5})
                elif source == 'Counter1':
                    curves[source] = p1.plot(pen={'color':'r', 'width':5})
                elif source == 'Counter1':
                    curves[source] = p1.plot(pen={'color':'w', 'width':5})
                else:
                    curves[source] = p1.plot(pen={'color':'c', 'width':5})

            # Enable antialiasing for prettier plots
            pg.setConfigOptions(antialias=True)

            def update(timer):
                if 'save' in self.plot_data.keys():
                    if self.plot_data['save'] == True:
                        self.plot_data['save'] = False
                        timer.stop()
                        save_path =  self.plot_data['save_path']
                        save_prefixes  = self.plot_data['save_prefixes']
                        exporter = pg.exporters.ImageExporter(p1)
                        exporterCSV = pg.exporters.CSVExporter(p1)
                        for save_prefix in save_prefixes:
                            if not os.path.exists(save_path+str(save_prefix)+'.png'):
                                exporter.export(save_path+str(save_prefix)+'.png')
                                exporterCSV.export(save_path+str(save_prefix)+'.csv')
                                break

                for source in sources:
                    data = self.plot_data['data'][source]
                    num_points = len(data)
                    curves[source].setData(x = frequencies[0:num_points], y = data)

            timer = QtCore.QTimer()
            timer.timeout.connect(partial(update,timer))
            timer.start(50)
            QtGui.QApplication.instance().exec_()


        elif plot_type == 'Fast Scan': # Required parameters = sources, averaging #, Frequency Range. Data will be in format {Source: value}
            sources = plot_params['sources'] #Acceptable sources - Counter 0/1/2/3
            self.plot_data['sources'] = sources
            self.plot_data['data'] = {}

            for source in sources:
                self.plot_data['data'][source] = [] # To be plotted


            a = QtGui.QApplication( [] )


            win = pg.GraphicsWindow()
            win.setWindowTitle('Frequency Scan')
            win.resize(1000,600)

            keepTrace = QtGui.QCheckBox('Keep current trace')

            p1 = win.addPlot(title="Frequency Scan")
            curves = {}
            for source in sources:
                if source == 'Counter0':
                    curves[source] = p1.plot(pen={'color':'y', 'width':5})
                    curves['keepTrace'+source] = p1.plot(pen={'color':'r', 'width':5})
                elif source == 'Counter1':
                    curves[source] = p1.plot(pen={'color':'w', 'width':5})
                    curves['keepTrace'+source] = p1.plot(pen={'color':'g', 'width':5})
                else:
                    curves[source] = p1.plot(pen={'color': 'c', 'width':5})
                    curves['keepTrace'+source] = p1.plot(pen={'color':'r', 'width':5})



            # Enable antialiasing for prettier plots
            pg.setConfigOptions(antialias=True)

            layout = pg.LayoutWidget()
            layout.addWidget(keepTrace, row=1, col = 0)
            layout.addWidget(win, row = 2, col = 0)
            layout.show()
            layout.resize(1000,600)
            self.fast_scan_keepTrace_past = False

            def update(timer):
                if 'save' in self.plot_data.keys():
                    if self.plot_data['save'] == True:
                        self.plot_data['save'] = False
                        timer.stop()
                        save_path =  self.plot_data['save_path']
                        save_prefixes  = self.plot_data['save_prefixes']
                        exporter = pg.exporters.ImageExporter(p1)
                        exporterCSV = pg.exporters.CSVExporter(p1)
                        for save_prefix in save_prefixes:
                            if not os.path.exists(save_path+str(save_prefix)+'.png'):
                                exporter.export(save_path+str(save_prefix)+'.png')
                                exporterCSV.export(save_path+str(save_prefix)+'.csv')
                                break

                if keepTrace.isChecked() and not(self.fast_scan_keepTrace_past):
                    self.fast_scan_keepTrace_past = True
                    for source in sources:
                        data = self.plot_data['data'][source]
                        curves['keepTrace'+source].setData( y = data)


                elif not(keepTrace.isChecked()):
                    self.fast_scan_keepTrace_past = False
                    for source in sources:
                        data = self.plot_data['data'][source]
                        curves['keepTrace'+source].setData( y = [])


                for source in sources:
                    data = self.plot_data['data'][source]
                    curves[source].setData( y = data)

            timer = QtCore.QTimer()
            timer.timeout.connect(partial(update,timer))
            timer.start(50)
            QtGui.QApplication.instance().exec_()


        elif plot_type == 'Camera':
            self.plot_data['data'] = np.zeros((550,550), dtype=np.uint8).tolist()
            self.data_out = np.array([[0]])
            pg.mkQApp()

            win = pg.GraphicsView()
            win.setWindowTitle('Top Camera')

            win_lay = pg.GraphicsLayout()
            win_vb = win_lay.addViewBox()
            win.setCentralItem(win_lay)
            # Item for displaying image data
            img = pg.ImageItem()
            win_vb.addItem(img)


            roi = pg.ROI([82, 82], [386,386], angle=0.0, snapSize= 1.0, scaleSnap = True, translateSnap = True, pen = pg.mkPen('r',width=2))  # "top","left","height""width"
            roi.addScaleHandle([1, 1], [0, 0])
            roi.addScaleHandle([0, 0], [1, 1])
            roi.setZValue(10)  # make sure ROI is drawn above image
            win_vb.addItem(roi)

            (rx0,ry0) = roi.pos()
            (rxsize,rysize) = roi.size()


            win2 = pg.GraphicsWindow()

            p2x = win2.addPlot(title="Y projection")
            win2.nextRow()
            p2y = win2.addPlot(title="X projection")
            win2.resize(75,75)
            curvex_data = p2x.plot(pen='r', y = np.zeros(int(rxsize)) , x = np.arange(int(rxsize))+int(rx0)-275)
            curvey_data = p2y.plot(pen='r', y = np.zeros(int(rysize)) , x = np.arange(int(rysize))+int(ry0)-275)
            curvex_fit = p2x.plot(pen='w')
            curvey_fit = p2y.plot(pen='w')



            NASave = QtGui.QPushButton('Set as No Atoms (NA)')
            NARemove = QtGui.QCheckBox('Divide NA')
            BkgSave = QtGui.QPushButton('Set as noise')
            BkgRemove = QtGui.QCheckBox('Subtract noise')
            GetANumber = QtGui.QCheckBox('Get atom number')



            newfont = QtGui.QFont("Times", 25, QtGui.QFont.Bold)
            atomNumberDisplay = QtGui.QLabel('0')
            atomNumberDisplay.setFont(newfont)
            atomNumberDisplay_label = QtGui.QLabel('Atom Number')
            atomNumberDisplay_label.setFont(newfont)

            Rot_label = QtGui.QLabel('Rot angle')
            Rot_label.setFont(QtGui.QFont("Times", 15))
            Rot = QtGui.QLineEdit('47')

            Avg_label = QtGui.QLabel('Averages')
            Avg_label.setFont(QtGui.QFont("Times", 15))
            Avg = QtGui.QLineEdit('1')

            f_label = QtGui.QLabel('Fname: ')
            f_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            f_label.setFont(QtGui.QFont("Times", 15))
            finput = QtGui.QLineEdit('IM0')

            ImSave = QtGui.QPushButton('Save Data')


            XDisplay = QtGui.QLabel('0')
            XDisplay.setFont(newfont)
            XDisplay_label = QtGui.QLabel('X')
            XDisplay_label.setFont(newfont)

            YDisplay = QtGui.QLabel('0')
            YDisplay.setFont(newfont)
            YDisplay_label = QtGui.QLabel('Y')
            YDisplay_label.setFont(newfont)


            SigmaXDisplay = QtGui.QLabel('0')
            SigmaXDisplay.setFont(newfont)
            SigmaXDisplay_label = QtGui.QLabel(u"\u03C3"+'X')
            SigmaXDisplay_label.setFont(newfont)


            SigmaYDisplay = QtGui.QLabel('0')
            SigmaYDisplay.setFont(newfont)
            SigmaYDisplay_label = QtGui.QLabel(u"\u03C3"+'Y')
            SigmaYDisplay_label.setFont(newfont)

            def saveIm():

                filename = QtGui.QFileDialog.getSaveFileName(None ,"Save Image as...", "C:/Users/RoyOutput/Dropbox (MIT)/" + str(finput.text()) + '.png', "Image files (*.png)" )
                basename = filename.replace(".png","")

                Imexporter = pg.exporters.ImageExporter(win_vb)
                Imexporter.export(basename + '.png')
                Imexporter = pg.exporters.ImageExporter(p2y)
                Imexporter.export(basename + '_X.png')
                Imexporter = pg.exporters.ImageExporter(p2x)
                Imexporter.export(basename + '_Y.png')
                exporterCSV = pg.exporters.CSVExporter(p2x)
                exporterCSV.export(basename + '_Y.csv')
                exporterCSV = pg.exporters.CSVExporter(p2y)
                exporterCSV.export(basename + '_X.csv')

                np.savetxt( str(basename) + '.txt', (img.image).astype(float)  , delimiter=',')


            ImSave.clicked.connect(saveIm)


            layout = pg.LayoutWidget()
            layout.addWidget(NASave)
            layout.addWidget(NARemove)
            layout.addWidget(BkgSave)
            layout.addWidget(BkgRemove)
            layout.addWidget(GetANumber)
            layout.addWidget(Rot_label, col=10)
            layout.addWidget(Rot, col=11)
            layout.addWidget(Avg_label, col=12)
            layout.addWidget(Avg, col=13)
            layout.addWidget(ImSave, row=6, col = 0 , colspan=2, rowspan=1)
            layout.addWidget(f_label,row=6, col = 2 , colspan=1, rowspan=1)
            layout.addWidget(finput ,row=6, col = 3 , colspan=1.5, rowspan=1)
            layout.addWidget(win, row=1, col=0, colspan=6, rowspan=4)
            layout.addWidget(win2, row=2, col=10, colspan=5, rowspan=1)
            layout.addWidget(atomNumberDisplay_label, row=5, col=0, colspan=1, rowspan=1)
            layout.addWidget(atomNumberDisplay, row=5, col=2, colspan=1, rowspan=1)
            layout.addWidget(XDisplay_label, row=5, col=13, colspan=1, rowspan=1)
            layout.addWidget(XDisplay, row=5, col=14, colspan=1, rowspan=1)
            layout.addWidget(YDisplay_label, row=6, col=13, colspan=1, rowspan=1)
            layout.addWidget(YDisplay, row=6, col=14, colspan=1, rowspan=1)
            layout.addWidget(SigmaXDisplay_label, row=5, col=10, colspan=1, rowspan=1)
            layout.addWidget(SigmaXDisplay, row=5, col=11, colspan=1, rowspan=1)
            layout.addWidget(SigmaYDisplay_label, row=6, col=10, colspan=1, rowspan=1)
            layout.addWidget(SigmaYDisplay, row=6, col=11, colspan=1, rowspan=1)
            layout.resize(1000,800)
            layout.show()




            def saveBkg():
                #data = np.array(self.plot_data['data']).astype(np.uint8)
                self.cameraBkg = self.data_ave

            BkgSave.clicked.connect(saveBkg)

            def saveNA():
                #data = np.array(self.plot_data['data']).astype(np.uint8)
                self.cameraNA = self.data_ave

            NASave.clicked.connect(saveNA)

            def gaussian(offset, height, center_x, center_y, width_x, width_y):
                """Returns a gaussian function with the given parameters"""
                width_x = float(width_x)
                width_y = float(width_y)
                return lambda x,y: offset+height*np.exp(
                            -(((x-center_x)/width_x)**2+((y-center_y)/width_y)**2)/2)

            self.camera_data_prev= [0]
            self.avg_count = 0
            self.data_ave = []
            self.data = []

            def update():
                    #Be smarter about this....
                    temp_data = np.array(self.plot_data['data']).astype(np.float)

                    if np.array_equal(self.camera_data_prev, temp_data):
                        return 1
                    else :
                        self.camera_data_prev = temp_data


                    averages  = int(Avg.text())

                    if self.avg_count < averages:
                        self.avg_count += 1
                        self.data.append(temp_data)
                    elif self.avg_count > averages:
                        self.avg_count = averages
                        if self.data[0:averages-1]== []:
                            self.data = [temp_data]
                        else:
                            self.data = [temp_data]+ self.data[0:averages-1]
                    else:
                        if self.data[1:averages]== []:
                            self.data = [temp_data]
                        else:
                            self.data = [temp_data] + self.data[0:averages-1]


                    self.data_ave = self.data[0]
                    data_len = len(self.data)
                    

                    for i in xrange(data_len-1):
                        self.data_ave += self.data[i+1]
                    self.data_ave /= data_len
                    
                    data = self.data_ave

                    autoLevels = True




                    if BkgRemove.isChecked() and NARemove.isChecked():
                        data = np.true_divide((data - self.cameraBkg),(self.cameraNA - self.cameraBkg))
                        data[data == np.inf] = 1
                        data[np.isnan(data)] = 1
                        data[data <= 0] = 1
                        autoLevels =False

                    elif NARemove.isChecked():
                        data = np.true_divide(data, self.cameraNA)
                        data[data == np.inf] = 1
                        data[np.isnan(data)] = 1
                        autoLevels =False


                    elif BkgRemove.isChecked():
                         data = data - self.cameraBkg
                         data[data <= 0] = 1

                    rot_angle = float(Rot.text())
                    data = sp.rotate(data, rot_angle, reshape=False)


                    try:
                        data_roi= roi.getArrayRegion(data, img)
                    except:
                        print 'Exception!'
                        data_roi = np.array(data)


                    self.data_out = data_roi
                    (rx0,ry0) = roi.pos()
                    (rxsize,rysize) = roi.size()


                    if GetANumber.isChecked():

                        atom_number, offset, height, x, y, width_x, width_y = self.FindAtomNumber(data_roi )
                        atomNumberDisplay.setText( "{:.3E}".format(atom_number*(topmag**2)))

                        pixel_ratio = 4.65 #micrometer / pixel
                        XDisplay.setText( "{:.2E}".format(x+rx0 - 275))
                        YDisplay.setText( "{:.2E}".format(y+ry0 - 275))
                        SigmaXDisplay.setText( "{:.2E}".format(pixel_ratio*width_x*topmag))
                        SigmaYDisplay.setText( "{:.2E}".format(pixel_ratio*width_y*topmag))

                        fit = gaussian(*[offset, height, x, y, width_x, width_y])
                        data_fit = fit(*np.indices(data_roi.shape))


                        curvey_fit.setData(y = data_fit.sum(axis=1), x = np.arange( data_fit.shape[0])+ int(rx0)-275 ) #data_fit.sum(axis=0)
                        curvex_fit.setData(y = data_fit.sum(axis=0), x = np.arange( data_fit.shape[1])+ int(ry0)-275 ) #data_fit.sum(axis=1)


                    curvex_data.setData( y = np.log(data_roi).sum(axis=0), x = np.arange(data_roi.shape[1])+ int(ry0)-275 ) #np.log(data_roi).sum(axis=0),
                    curvey_data.setData( y = np.log(data_roi).sum(axis=1), x = np.arange(data_roi.shape[0])+ int(rx0)-275 ) #np.log(data_roi).sum(axis=1),

                    if autoLevels:
                        img.setImage(image=data, autoDownsample = True)
                    else:
                        img.setImage(image=data, autoLevels=False, autoDownsample = True, levels = (0.5, 1), lut=lut)


            timer = QtCore.QTimer()
            timer.timeout.connect(update)
            timer.start(100)

            QtGui.QApplication.instance().exec_()

        elif plot_type == 'Side Camera':

            self.plot_data['data'] = np.zeros((480,640), dtype=np.uint8).tolist()
            self.data_out = np.array([[0]])
            pg.mkQApp()

            win = pg.GraphicsView()
            win_lay = pg.GraphicsLayout()
            win_vb = win_lay.addViewBox()
            win.setCentralItem(win_lay)
            # Item for displaying image data
            img = pg.ImageItem()
            win_vb.addItem(img)


            roi = pg.ROI([82, 82], [386,386], angle=0.0, snapSize= 1.0, scaleSnap = True, translateSnap = True, pen = pg.mkPen('r',width=2))  # "top","left","height""width"
            roi.addScaleHandle([1, 1], [0, 0])
            roi.addScaleHandle([0, 0], [1, 1])
            roi.setZValue(10)  # make sure ROI is drawn above image
            win_vb.addItem(roi)

            (rx0,ry0) = roi.pos()
            (rxsize,rysize) = roi.size()


            win2 = pg.GraphicsWindow()
            p2x = win2.addPlot(title="Y projection")
            win2.nextRow()
            p2y = win2.addPlot(title="X projection")
            win2.resize(75,75)
            curvex_data = p2x.plot(pen='r', y = np.zeros(int(rxsize)) , x = np.arange(int(rxsize))+int(rx0)-275)
            curvey_data = p2y.plot(pen='r', y = np.zeros(int(rysize)) , x = np.arange(int(rysize))+int(ry0)-275)
            curvex_fit = p2x.plot(pen='w')
            curvey_fit = p2y.plot(pen='w')



            NASave = QtGui.QPushButton('Set as No Atoms (NA)')
            NARemove = QtGui.QCheckBox('Divide NA')
            BkgSave = QtGui.QPushButton('Set as noise')
            BkgRemove = QtGui.QCheckBox('Subtract noise')
            GetANumber = QtGui.QCheckBox('Get atom number')




            newfont = QtGui.QFont("Times", 25, QtGui.QFont.Bold)
            atomNumberDisplay = QtGui.QLabel('0')
            atomNumberDisplay.setFont(newfont)
            atomNumberDisplay_label = QtGui.QLabel('Atom Number')
            atomNumberDisplay_label.setFont(newfont)

            Rot_label = QtGui.QLabel('Rot angle')
            Rot_label.setFont(QtGui.QFont("Times", 15))
            Rot = QtGui.QLineEdit('0')

            Avg_label = QtGui.QLabel('Averages')
            Avg_label.setFont(QtGui.QFont("Times", 15))
            Avg = QtGui.QLineEdit('1')

            f_label = QtGui.QLabel('Fname: ')
            f_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            f_label.setFont(QtGui.QFont("Times", 15))
            finput = QtGui.QLineEdit('IM0')

            ImSave = QtGui.QPushButton('Save Data')


            XDisplay = QtGui.QLabel('0')
            XDisplay.setFont(newfont)
            XDisplay_label = QtGui.QLabel('X')
            XDisplay_label.setFont(newfont)

            YDisplay = QtGui.QLabel('0')
            YDisplay.setFont(newfont)
            YDisplay_label = QtGui.QLabel('Y')
            YDisplay_label.setFont(newfont)


            SigmaXDisplay = QtGui.QLabel('0')
            SigmaXDisplay.setFont(newfont)
            SigmaXDisplay_label = QtGui.QLabel(u"\u03C3"+'X')
            SigmaXDisplay_label.setFont(newfont)


            SigmaYDisplay = QtGui.QLabel('0')
            SigmaYDisplay.setFont(newfont)
            SigmaYDisplay_label = QtGui.QLabel(u"\u03C3"+'Y')
            SigmaYDisplay_label.setFont(newfont)

            def saveIm():

                filename = QtGui.QFileDialog.getSaveFileName(None ,"Save Image as...", "C:/Users/RoyOutput/Dropbox (MIT)/" + str(finput.text()) + '.png', "Image files (*.png)" )
                basename = filename.replace(".png","")

                Imexporter = pg.exporters.ImageExporter(win_vb)
                Imexporter.export(basename + 'S.png')
                Imexporter = pg.exporters.ImageExporter(p2y)
                Imexporter.export(basename + '_XS.png')
                Imexporter = pg.exporters.ImageExporter(p2x)
                Imexporter.export(basename + '_YS.png')
                exporterCSV = pg.exporters.CSVExporter(p2x)
                exporterCSV.export(basename + '_YS.csv')
                exporterCSV = pg.exporters.CSVExporter(p2y)
                exporterCSV.export(basename + '_XS.csv')

                np.savetxt( str(basename) + '_S.txt', (img.image).astype(float)  , delimiter=',')


            ImSave.clicked.connect(saveIm)


            layout = pg.LayoutWidget()
            layout.addWidget(NASave)
            layout.addWidget(NARemove)
            layout.addWidget(BkgSave)
            layout.addWidget(BkgRemove)
            layout.addWidget(GetANumber)
            layout.addWidget(Rot_label, col=10)
            layout.addWidget(Rot, col=11)
            layout.addWidget(Avg_label, col=12)
            layout.addWidget(Avg, col=13)
            layout.addWidget(ImSave, row=6, col = 0 , colspan=2, rowspan=1)
            layout.addWidget(f_label,row=6, col = 2 , colspan=1, rowspan=1)
            layout.addWidget(finput ,row=6, col = 3 , colspan=1.5, rowspan=1)
            layout.addWidget(win, row=1, col=0, colspan=6, rowspan=4)
            layout.addWidget(win2, row=2, col=10, colspan=5, rowspan=1)
            layout.addWidget(atomNumberDisplay_label, row=5, col=0, colspan=1, rowspan=1)
            layout.addWidget(atomNumberDisplay, row=5, col=2, colspan=1, rowspan=1)
            layout.addWidget(XDisplay_label, row=5, col=13, colspan=1, rowspan=1)
            layout.addWidget(XDisplay, row=5, col=14, colspan=1, rowspan=1)
            layout.addWidget(YDisplay_label, row=6, col=13, colspan=1, rowspan=1)
            layout.addWidget(YDisplay, row=6, col=14, colspan=1, rowspan=1)
            layout.addWidget(SigmaXDisplay_label, row=5, col=10, colspan=1, rowspan=1)
            layout.addWidget(SigmaXDisplay, row=5, col=11, colspan=1, rowspan=1)
            layout.addWidget(SigmaYDisplay_label, row=6, col=10, colspan=1, rowspan=1)
            layout.addWidget(SigmaYDisplay, row=6, col=11, colspan=1, rowspan=1)
            layout.resize(1000,800)
            layout.show()




            def saveBkg():
                #data = np.array(self.plot_data['data']).astype(np.uint8)
                self.cameraBkg = self.data_ave

            BkgSave.clicked.connect(saveBkg)

            def saveNA():
                #data = np.array(self.plot_data['data']).astype(np.uint8)
                self.cameraNA = self.data_ave

            NASave.clicked.connect(saveNA)

            def gaussian(offset, height, center_x, center_y, width_x, width_y):
                """Returns a gaussian function with the given parameters"""
                width_x = float(width_x)
                width_y = float(width_y)
                return lambda x,y: offset+height*np.exp(
                            -(((x-center_x)/width_x)**2+((y-center_y)/width_y)**2)/2)

            self.camera_data_prev= [0]
            self.avg_count = 0
            self.data = []

            def update():
                    #Be smarter about this....
                    temp_data = np.array(self.plot_data['data']).astype(np.float)

                    if np.array_equal(self.camera_data_prev, temp_data):
                        return 1
                    else :
                        self.camera_data_prev = temp_data


                    averages  = int(Avg.text())

                    if self.avg_count < averages:
                        self.avg_count += 1
                        self.data.append(temp_data)
                    elif self.avg_count > averages:
                        self.avg_count = averages
                        if self.data[0:averages-1]== []:
                            self.data = [temp_data]
                        else:
                            self.data = [temp_data]+ self.data[0:averages-1]
                    else:
                        if self.data[1:averages]== []:
                            self.data = [temp_data]
                        else:
                            self.data = [temp_data] + self.data[0:averages-1]


                    data = self.data[0]
                    data_len = len(self.data)


                    for i in xrange(data_len-1):
                        data += self.data[i+1]
                    data /= data_len


                    autoLevels = True




                    if BkgRemove.isChecked() and NARemove.isChecked():
                        data = np.true_divide((data - self.cameraBkg),(self.cameraNA - self.cameraBkg))
                        data[data == np.inf] = 1
                        data[np.isnan(data)] = 1
                        data[data <= 0] = 1
                        autoLevels =False

                    elif NARemove.isChecked():
                        data = np.true_divide(data, self.cameraNA)
                        data[data == np.inf] = 1
                        data[np.isnan(data)] = 1
                        autoLevels =False


                    elif BkgRemove.isChecked():
                         data = data - self.cameraBkg
                         data[data <= 0] = 1

                    rot_angle = float(Rot.text())
                    data = sp.rotate(data, rot_angle, reshape=False)


                    try:
                        data_roi= roi.getArrayRegion(data, img)
                    except:
                        print 'Exception!'
                        data_roi = np.array(data)


                    self.data_out = data_roi
                    (rx0,ry0) = roi.pos()
                    (rxsize,rysize) = roi.size()


                    if GetANumber.isChecked():

                        atom_number, offset, height, x, y, width_x, width_y = self.FindAtomNumber(data_roi )
                        atomNumberDisplay.setText( "{:.3E}".format(atom_number*(sidemag**2)))

                        pixel_ratio = 7.4 #micrometer / pixel
                        XDisplay.setText( "{:.2E}".format(x+rx0 - 275))
                        YDisplay.setText( "{:.2E}".format(y+ry0 - 275))
                        SigmaXDisplay.setText( "{:.2E}".format(pixel_ratio*width_x*sidemag))
                        SigmaYDisplay.setText( "{:.2E}".format(pixel_ratio*width_y*sidemag))

                        fit = gaussian(*[offset, height, x, y, width_x, width_y])
                        data_fit = fit(*np.indices(data_roi.shape))


                        curvey_fit.setData(y = data_fit.sum(axis=1), x = np.arange( data_fit.shape[0])+ int(rx0)-275 ) #data_fit.sum(axis=0)
                        curvex_fit.setData(y = data_fit.sum(axis=0), x = np.arange( data_fit.shape[1])+ int(ry0)-275 ) #data_fit.sum(axis=1)


                    curvex_data.setData( y = np.log(data_roi).sum(axis=0), x = np.arange(data_roi.shape[1])+ int(ry0)-275 ) #np.log(data_roi).sum(axis=0),
                    curvey_data.setData( y = np.log(data_roi).sum(axis=1), x = np.arange(data_roi.shape[0])+ int(rx0)-275 ) #np.log(data_roi).sum(axis=1),

                    if autoLevels:
                        img.setImage(image=data, autoDownsample = True)
                    else:
                        img.setImage(image=data, autoLevels=False, autoDownsample = True, levels = (0.5, 1), lut=lut)


            timer = QtCore.QTimer()
            timer.timeout.connect(update)
            timer.start(100)

            QtGui.QApplication.instance().exec_()

        elif plot_type == 'Side Camera3':

            self.plot_data['data'] = np.zeros((480,640), dtype=np.uint8).tolist()
            self.data_out = np.array([[0]])
            pg.mkQApp()

            win = pg.GraphicsView()
            win_lay = pg.GraphicsLayout()
            win_vb = win_lay.addViewBox()
            win.setCentralItem(win_lay)
            # Item for displaying image data
            img = pg.ImageItem()
            win_vb.addItem(img)


            roi = pg.ROI([82, 82], [386,386], angle=0.0, snapSize= 1.0, scaleSnap = True, translateSnap = True, pen = pg.mkPen('r',width=2))  # "top","left","height""width"
            roi.addScaleHandle([1, 1], [0, 0])
            roi.addScaleHandle([0, 0], [1, 1])
            roi.setZValue(10)  # make sure ROI is drawn above image
            win_vb.addItem(roi)

            (rx0,ry0) = roi.pos()
            (rxsize,rysize) = roi.size()


            win2 = pg.GraphicsWindow()
            p2x = win2.addPlot(title="Y projection")
            win2.nextRow()
            p2y = win2.addPlot(title="X projection")
            win2.resize(75,75)
            curvex_data = p2x.plot(pen='r', y = np.zeros(int(rxsize)) , x = np.arange(int(rxsize))+int(rx0)-275)
            curvey_data = p2y.plot(pen='r', y = np.zeros(int(rysize)) , x = np.arange(int(rysize))+int(ry0)-275)
            curvex_fit = p2x.plot(pen='w')
            curvey_fit = p2y.plot(pen='w')



            NASave = QtGui.QPushButton('Set as No Atoms (NA)')
            NARemove = QtGui.QCheckBox('Divide NA')
            BkgSave = QtGui.QPushButton('Set as noise')
            BkgRemove = QtGui.QCheckBox('Subtract noise')
            GetANumber = QtGui.QCheckBox('Get atom number')




            newfont = QtGui.QFont("Times", 25, QtGui.QFont.Bold)
            atomNumberDisplay = QtGui.QLabel('0')
            atomNumberDisplay.setFont(newfont)
            atomNumberDisplay_label = QtGui.QLabel('Atom Number')
            atomNumberDisplay_label.setFont(newfont)

            Rot_label = QtGui.QLabel('Rot angle')
            Rot_label.setFont(QtGui.QFont("Times", 15))
            Rot = QtGui.QLineEdit('0')

            Avg_label = QtGui.QLabel('Averages')
            Avg_label.setFont(QtGui.QFont("Times", 15))
            Avg = QtGui.QLineEdit('1')

            f_label = QtGui.QLabel('Fname: ')
            f_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            f_label.setFont(QtGui.QFont("Times", 15))
            finput = QtGui.QLineEdit('IM0')

            ImSave = QtGui.QPushButton('Save Data')


            XDisplay = QtGui.QLabel('0')
            XDisplay.setFont(newfont)
            XDisplay_label = QtGui.QLabel('X')
            XDisplay_label.setFont(newfont)

            YDisplay = QtGui.QLabel('0')
            YDisplay.setFont(newfont)
            YDisplay_label = QtGui.QLabel('Y')
            YDisplay_label.setFont(newfont)


            SigmaXDisplay = QtGui.QLabel('0')
            SigmaXDisplay.setFont(newfont)
            SigmaXDisplay_label = QtGui.QLabel(u"\u03C3"+'X')
            SigmaXDisplay_label.setFont(newfont)


            SigmaYDisplay = QtGui.QLabel('0')
            SigmaYDisplay.setFont(newfont)
            SigmaYDisplay_label = QtGui.QLabel(u"\u03C3"+'Y')
            SigmaYDisplay_label.setFont(newfont)

            def saveIm():

                filename = QtGui.QFileDialog.getSaveFileName(None ,"Save Image as...", "C:/Users/RoyOutput/Dropbox (MIT)/" + str(finput.text()) + '.png', "Image files (*.png)" )
                basename = filename.replace(".png","")

                Imexporter = pg.exporters.ImageExporter(win_vb)
                Imexporter.export(basename + 'S.png')
                Imexporter = pg.exporters.ImageExporter(p2y)
                Imexporter.export(basename + '_XS.png')
                Imexporter = pg.exporters.ImageExporter(p2x)
                Imexporter.export(basename + '_YS.png')
                exporterCSV = pg.exporters.CSVExporter(p2x)
                exporterCSV.export(basename + '_YS.csv')
                exporterCSV = pg.exporters.CSVExporter(p2y)
                exporterCSV.export(basename + '_XS.csv')

                np.savetxt( str(basename) + '_S.txt', (img.image).astype(float)  , delimiter=',')


            ImSave.clicked.connect(saveIm)


            layout = pg.LayoutWidget()
            layout.addWidget(NASave)
            layout.addWidget(NARemove)
            layout.addWidget(BkgSave)
            layout.addWidget(BkgRemove)
            layout.addWidget(GetANumber)
            layout.addWidget(Rot_label, col=10)
            layout.addWidget(Rot, col=11)
            layout.addWidget(Avg_label, col=12)
            layout.addWidget(Avg, col=13)
            layout.addWidget(ImSave, row=6, col = 0 , colspan=2, rowspan=1)
            layout.addWidget(f_label,row=6, col = 2 , colspan=1, rowspan=1)
            layout.addWidget(finput ,row=6, col = 3 , colspan=1.5, rowspan=1)
            layout.addWidget(win, row=1, col=0, colspan=6, rowspan=4)
            layout.addWidget(win2, row=2, col=10, colspan=5, rowspan=1)
            layout.addWidget(atomNumberDisplay_label, row=5, col=0, colspan=1, rowspan=1)
            layout.addWidget(atomNumberDisplay, row=5, col=2, colspan=1, rowspan=1)
            layout.addWidget(XDisplay_label, row=5, col=13, colspan=1, rowspan=1)
            layout.addWidget(XDisplay, row=5, col=14, colspan=1, rowspan=1)
            layout.addWidget(YDisplay_label, row=6, col=13, colspan=1, rowspan=1)
            layout.addWidget(YDisplay, row=6, col=14, colspan=1, rowspan=1)
            layout.addWidget(SigmaXDisplay_label, row=5, col=10, colspan=1, rowspan=1)
            layout.addWidget(SigmaXDisplay, row=5, col=11, colspan=1, rowspan=1)
            layout.addWidget(SigmaYDisplay_label, row=6, col=10, colspan=1, rowspan=1)
            layout.addWidget(SigmaYDisplay, row=6, col=11, colspan=1, rowspan=1)
            layout.resize(1000,800)
            layout.show()




            def saveBkg():
                #data = np.array(self.plot_data['data']).astype(np.uint8)
                self.cameraBkg = self.data_ave

            BkgSave.clicked.connect(saveBkg)

            def saveNA():
                #data = np.array(self.plot_data['data']).astype(np.uint8)
                self.cameraNA = self.data_ave

            NASave.clicked.connect(saveNA)

            def gaussian(offset, height, center_x, center_y, width_x, width_y):
                """Returns a gaussian function with the given parameters"""
                width_x = float(width_x)
                width_y = float(width_y)
                return lambda x,y: offset+height*np.exp(
                            -(((x-center_x)/width_x)**2+((y-center_y)/width_y)**2)/2)

            self.camera_data_prev= [0]
            self.avg_count = 0
            self.data = []

            def update():
                    #Be smarter about this....
                    temp_data = np.array(self.plot_data['data']).astype(np.float)

                    if np.array_equal(self.camera_data_prev, temp_data):
                        return 1
                    else :
                        self.camera_data_prev = temp_data


                    averages  = int(Avg.text())

                    if self.avg_count < averages:
                        self.avg_count += 1
                        self.data.append(temp_data)
                    elif self.avg_count > averages:
                        self.avg_count = averages
                        if self.data[0:averages-1]== []:
                            self.data = [temp_data]
                        else:
                            self.data = [temp_data]+ self.data[0:averages-1]
                    else:
                        if self.data[1:averages]== []:
                            self.data = [temp_data]
                        else:
                            self.data = [temp_data] + self.data[0:averages-1]


                    data = self.data[0]
                    data_len = len(self.data)


                    for i in xrange(data_len-1):
                        data += self.data[i+1]
                    data /= data_len


                    autoLevels = True




                    if BkgRemove.isChecked() and NARemove.isChecked():
                        data = np.true_divide((data - self.cameraBkg),(self.cameraNA - self.cameraBkg))
                        data[data == np.inf] = 1
                        data[np.isnan(data)] = 1
                        data[data <= 0] = 1
                        autoLevels =False

                    elif NARemove.isChecked():
                        data = np.true_divide(data, self.cameraNA)
                        data[data == np.inf] = 1
                        data[np.isnan(data)] = 1
                        autoLevels =False


                    elif BkgRemove.isChecked():
                         data = data - self.cameraBkg
                         data[data <= 0] = 1

                    rot_angle = float(Rot.text())
                    data = sp.rotate(data, rot_angle, reshape=False)


                    try:
                        data_roi= roi.getArrayRegion(data, img)
                    except:
                        print 'Exception!'
                        data_roi = np.array(data)


                    self.data_out = data_roi
                    (rx0,ry0) = roi.pos()
                    (rxsize,rysize) = roi.size()


                    if GetANumber.isChecked():

                        atom_number, offset, height, x, y, width_x, width_y = self.FindAtomNumber(data_roi )
                        atomNumberDisplay.setText( "{:.3E}".format(atom_number*(sidemag**2)))

                        pixel_ratio = 7.4 #micrometer / pixel
                        XDisplay.setText( "{:.2E}".format(x+rx0 - 275))
                        YDisplay.setText( "{:.2E}".format(y+ry0 - 275))
                        SigmaXDisplay.setText( "{:.2E}".format(pixel_ratio*width_x*sidemag))
                        SigmaYDisplay.setText( "{:.2E}".format(pixel_ratio*width_y*sidemag))

                        fit = gaussian(*[offset, height, x, y, width_x, width_y])
                        data_fit = fit(*np.indices(data_roi.shape))


                        curvey_fit.setData(y = data_fit.sum(axis=1), x = np.arange( data_fit.shape[0])+ int(rx0)-275 ) #data_fit.sum(axis=0)
                        curvex_fit.setData(y = data_fit.sum(axis=0), x = np.arange( data_fit.shape[1])+ int(ry0)-275 ) #data_fit.sum(axis=1)


                    curvex_data.setData( y = np.log(data_roi).sum(axis=0), x = np.arange(data_roi.shape[1])+ int(ry0)-275 ) #np.log(data_roi).sum(axis=0),
                    curvey_data.setData( y = np.log(data_roi).sum(axis=1), x = np.arange(data_roi.shape[0])+ int(rx0)-275 ) #np.log(data_roi).sum(axis=1),

                    if autoLevels:
                        img.setImage(image=data, autoDownsample = True)
                    else:
                        img.setImage(image=data, autoLevels=False, autoDownsample = True, levels = (0.5, 1), lut=lut)


            timer = QtCore.QTimer()
            timer.timeout.connect(update)
            timer.start(100)

            QtGui.QApplication.instance().exec_()


    def FindAtomNumber(self, data_roi):

        def gaussian(offset, height, center_x, center_y, width_x, width_y):
            """Returns a gaussian function with the given parameters"""
            width_x = float(width_x)
            width_y = float(width_y)
            return lambda x,y: offset+height*np.exp(
                        -(((x-center_x)/width_x)**2+((y-center_y)/width_y)**2)/2)

        def twogaussian(offset, height, center_x, center_y, width_x, width_y, phi):
            width_x = float(width_x)
            width_y = float(width_y)
            phi = float(phi)

            center_xrot = center_x*np.cos(phi)-center_y*np.sin(phi);
            center_yrot = center_x*np.sin(phi)+center_y*np.cos(phi);
            return lambda x,y: offset+height*np.exp(-(((center_xrot-(x*np.cos(phi) - y*np.sin(phi)))/width_x)**2+((center_yrot-(x*np.sin(phi) + y*np.cos(phi)))/width_y)**2)/2)

        def moments(data):
            """Returns (height, x, y, width_x, width_y)
            the gaussian parameters of a 2D distribution by calculating its
            moments """
            height = data.min()
            offset = data.max() - data.min()
            total = data.sum()
            X, Y = np.indices(data.shape)
            x = (X*data).sum()/total
            y = (Y*data).sum()/total
            col = data[:, int(y)]
            width_x = np.sqrt(np.abs(((np.arange(col.size)-y)**2*col).sum()/col.sum()))
            row = data[int(x), :]
            width_y = np.sqrt(np.abs(((np.arange(row.size)-x)**2*row).sum()/row.sum()))

            return offset, height, x, y, np.abs(width_x), np.abs(width_y)

        def fitgaussian(data):
            """Returns (offset, height, x, y, width_x, width_y)
            the gaussian parameters of a 2D distribution found by a fit"""
            #
            data[np.isnan(data)] = 1
            data[np.isinf(data)] = 1
            params = moments(data)
            errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                         data)
            p, success = optimize.leastsq(errorfunction,params, maxfev = 300)
            #p, success = optimize.fmin_slsqp(errorfunction,params, maxfev = 300)
            return p



        offset, height, x, y, width_x, width_y = fitgaussian(np.log(data_roi))

        cross_section = 0.29 #micro meter ^2
        pixel_ratio = 4.65 #micrometer / pixel
        atom_number = 2*np.pi*(pixel_ratio**2/cross_section) * np.abs(height)* np.abs(width_x)* np.abs(width_y)

        return atom_number, offset, height, x, y, np.abs(width_x), np.abs(width_y)
