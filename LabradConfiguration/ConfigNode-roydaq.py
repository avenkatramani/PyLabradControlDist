# -*- coding: utf-8 -*-
"""
Created on Thu Jan 26 17:41:44 2016

@author: AdityaVignesh

"""

import labrad

server_list = [
				'camera',
				'nicounter',
				'ni6535_digital',
				'ni6733_ao',
				'pulseblaster',
				'pts',
				'ni6250',
				'arduino',
				'agilent_arb',
				'tds2014c_a',
				'agilente8257d',
				'agilent_sg8648'
				]
#server_list = []
directories = ['B:\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Servers']


cxn = labrad.connect()
r = cxn.registry()

r.cd('Nodes')
r.cd('RoyDAQ')

r.set('directories',directories)
r.set('autostart', server_list)
 