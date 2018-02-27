"""
### BEGIN NODE INFO
[info]
name = hrmprocessor
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

import ctypes, numpy, sys, os
from labrad.server import LabradServer, setting
import pickle

import psutil
pid = os.getpid()
py = psutil.Process(pid)


class HRMTime(LabradServer):
    
    name="hrmtime"
    
    def initServer(self):

		self.sensl = ctypes.WinDLL('HRMTimeAPI.dll')
        
        # initialize HRM module
		self.sensl.HRM_GetDLLVersion.restype = ctypes.c_char_p
		dll_str = self.sensl.HRM_GetDLLVersion()
		print "HRM DLL Version %s" % dll_str
        
		self.sensl.HRM_RefreshConnectedModuleList()
		num_mod = self.sensl.HRM_GetConnectedModuleCount()

		print "Found %d module(s)." % num_mod
        
		handle_buf_type = ctypes.c_int*3
		handle_buf = handle_buf_type(0,0,0)

        # get handle to identify device in future communiations
		status = self.sensl.HRM_GetConnectedModuleList(ctypes.pointer(handle_buf))
		self.h = handle_buf[0]

		sb = ctypes.create_string_buffer(128)
		status = self.sensl.HRM_GetModuleIDRegister(self.h,sb)

		id_str = ''
		for i in sb:
			id_str += i
        
		srr = ctypes.c_ushort(0)

		status = self.sensl.HRM_GetSoftwareRevisionRegister(self.h,ctypes.byref(srr))

		print "Module ID is %s; FPGA Vers. 0x%x" % (id_str,srr.value)
		
		status_buf = ctypes.c_ushort(0)
		status3 = self.sensl.HRM_GetStatusRegister(self.h, ctypes.byref(status_buf))
		print("Status before setting Frequency")
		print(repr(status_buf.value))
		
		status = self.sensl.HRM_SetFrequencySelectionRegister(self.h,  0x9999)
		
                    
		status3 = self.sensl.HRM_GetStatusRegister(self.h, ctypes.byref(status_buf))
		print("Status after setting Frequency")
		print(repr(status_buf.value))


		sys.stdout.flush()

		self.reset_vars()
        
        
        ################ Variables for reading
    def reset_vars(self):
        self.max_read_size = 16*16*1024
        self.act_read_size = ctypes.c_ulong(0)
        
        read_buf_type = ctypes.c_ulong*self.max_read_size
        self.read_buf = read_buf_type()
        self.to_save = []

        self.nCh = 4
        
        self.last_tt = numpy.zeros((self.nCh,2),dtype=ctypes.c_ulong)
        
        self.first_cycle = numpy.zeros((self.nCh,))
        
        self.times = [[],[],[],[]]
        
        self.last_gate = numpy.zeros((self.nCh,),dtype=ctypes.c_double)
        self.num_gates_global = numpy.zeros((self.nCh,),dtype=ctypes.c_ulong)
        self.num_cycles = numpy.zeros((self.nCh,),dtype=ctypes.c_ulong)
        self.num_gates_cycle = numpy.zeros((self.nCh,),dtype=ctypes.c_ulong)
        
        self.num_gates_arr = [ [], [], [], [] ]

        self.proc_output = []
        
        self.ch_buf = ctypes.c_char()
        self.gap_buf = ctypes.c_double()
        
        
    @setting(1,"setup",gate_time_mus = 'w',save_prefix='s')
    def setup(self,c,gate_time_mus,save_prefix): 
		self.reset_vars()
		self.save_prefix = save_prefix
		self.gate_time_mus = gate_time_mus         
		self.target_filesize_MB = 2
		

		self.max_file_num = 0
		if not os.path.exists(self.save_prefix):
                    os.makedirs(self.save_prefix)   
		files = os.listdir(self.save_prefix)  
                
		for f in files:
			if int(f.split('.')[0])> self.max_file_num:
				self.max_file_num = int(f.split('.')[0]) + 1
        
    @setting(2,"acquire")
    def acquire(self, c):
        tt_mode = ctypes.c_ushort(1)
        status = self.sensl.HRM_RunFifoTimeTagging(self.h, ctypes.c_ushort(0x5555), ctypes.c_ushort(0), tt_mode)
    
    @setting(3,"stop")
    def stop(self, c): 
        #status = self.sensl.HRM_SetModeBitsRegister(self.h, 0x0030)
        output_chs = numpy.array( [x[0] for x in self.proc_output],dtype=ctypes.c_ubyte)
        output_times = numpy.array( [x[1] for x in self.proc_output],dtype=ctypes.c_double)
        output_gates = numpy.array( [x[2] for x in self.proc_output],dtype=ctypes.c_ushort)
        output_cycles = numpy.array( [x[3] for x in self.proc_output],dtype=ctypes.c_ushort)
        output_dict =  { 'ch':output_chs,
                         'times': output_times,
                         'gates': output_gates,
                         'cycles': output_cycles}    
                                    
        if not os.path.exists(self.save_prefix):
            os.makedirs(self.save_prefix)   
        files = os.listdir(self.save_prefix)  
        max_file_num = 0
        for f in files:
            if int(f.split('.')[0])>= max_file_num:
                max_file_num = int(f.split('.')[0]) + 1
        with open(self.save_prefix +'\\'+str(max_file_num)+ '.pkl', 'wb') as f:
                pickle.dump(output_dict, f, pickle.HIGHEST_PROTOCOL)
    
        self.proc_output = []
                    
    @setting(4,"read")
    def read(self, c):      
		mem_prog_buf = ctypes.c_ulong(0)
		status_buf = ctypes.c_ushort(0)
					
		#HRM_STATUS WINAPI HRM_GetWriteCountRegister(HANDLE handle, ULONG *wrrData)
		status2 = self.sensl.HRM_GetWriteCountRegister(self.h, ctypes.byref(mem_prog_buf) )
		print(repr(mem_prog_buf.value))        
		status3 = self.sensl.HRM_GetStatusRegister(self.h, ctypes.byref(status_buf))
		print(repr(status_buf.value))

			
		status = self.sensl.HRM_GetFifoData(self.h,
										ctypes.c_ushort(1),
										self.max_read_size,
										ctypes.byref(self.act_read_size),
										ctypes.byref(self.read_buf)
										)
		
		status = self.sensl.HRM_SetRoutingResetRegister(self.h, ctypes.c_ushort(0))
        
    @setting(5,"process", cycle = 'w')
    def process(self, c, cycle): 
        if self.act_read_size.value > 0:
            read_buf = self.read_buf[0:self.act_read_size.value]
            self.act_read_size = ctypes.c_ulong(0)
            buflen = len(read_buf)
            print(buflen)
            
            ptr = 0
            print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')                
            while ptr < buflen:
                micro = read_buf[ptr]
                macro = read_buf[ptr+1]
                ch = micro & 0b11
                ptr += 2
                
                status = self.sensl.HRM_GetTimeTagGap(ctypes.c_ulong(self.last_tt[ch][1]),
                                                ctypes.c_ulong(self.last_tt[ch][0]),
                                                ctypes.c_ulong(macro),
                                                ctypes.c_ulong(micro),
                                                ctypes.byref(self.ch_buf),
                                                ctypes.byref(self.gap_buf)
                                                )
                
                
                    
                self.last_tt[ch][1] = macro
                self.last_tt[ch][0] = micro
                

                
                self.times[ch].append(1e-6 * self.gap_buf.value) # convert from ps to us
                

            for ch in xrange(self.nCh):
                if self.times[ch] != []:
					gate = 1
					time_temp = numpy.array(self.times[ch])
					self.times[ch] = []
					#Assuming the first click is a fake click and using the known gate period to define gates
					time_cumulative = 0
					for i in xrange(len(time_temp)-1):
						time_cumulative += time_temp[i+1]
						if time_cumulative >= self.gate_time_mus:
							time_cumulative = 0
							gate+=1
							if gate >= 1600:
								break
						else:
							self.proc_output.append( (ch, time_cumulative, gate, cycle) )
                     
            print(str(len(self.proc_output)/(self.target_filesize_MB*1024*1024/25.0) *100.0) + ' %')
            if len(self.proc_output) > self.target_filesize_MB*1024*1024/25:                
                output_chs = numpy.array( [x[0] for x in self.proc_output])
                output_times = numpy.array( [x[1] for x in self.proc_output])
                output_gates = numpy.array( [x[2] for x in self.proc_output])
                output_cycles = numpy.array( [x[3] for x in self.proc_output])
                output_dict =  { 'ch':output_chs,
                                 'times': output_times,
                                 'gates': output_gates,
                                 'cycles': output_cycles}    
                
                
                with open(self.save_prefix +'\\'+str(self.max_file_num)+ '.pkl', 'wb') as f:
                        pickle.dump(output_dict, f, pickle.HIGHEST_PROTOCOL)
                self.max_file_num += 1
                print('$$$$$$$$ - Saved !!!!!!!')
            
                self.proc_output = []
    

        
                                            
                
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(HRMTime())


