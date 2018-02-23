# -*- coding: utf-8 -*-
"""
IRISS/RECUV Program for streaming data from Semi Lagrangian Drifters (LD).
Loads data, saves in its original format as 'rawdata' and converts
raw data(hexidecimal bytes) into interpretable data. Finally, it 
saves the manipulated values into files depending on the 'remote'/LD
to see real time/access at later time.

@author: Sara Swenson
"""

import datetime
import numpy as np
import serial
import re
import json
flt_format = lambda x:"%.3f" % x
np.set_printoptions(formatter={'float_kind':flt_format})


class DataStream(object):
    def __init__(self):
        ## Change this for path where data will be saved: ##
        self.pathjs = 'C:/Users/Sara Swenson/Documents/kaist_web/geojson/'
        self.pathcsv = 'C:/Users/Sara Swenson/Documents/Lagrangian Drifters/DataStream/'
        self.server = ''
        self.header = "Time since boot(s),Remote #, RSSI, # Bytes,Transmition #, Lat. Offsest (deg), Lon. Offset (deg),Altitude (mASL),Pressure (Pa), Temperature (C), Humidity (%), Ground Velocity (m/s), Course (deg), Hour,Minute,Second,Voltage,Lto,Lno, Pressure,GPS#","\n"
        #self.json_data = {"geometry": {"type": "Point","coordinates": [self.lat_off, self.lon_off]}, "type": "Feature", "properties": {"jsonString": {"acgndspd": self.grnd_vel, "acvolt": self.volt, "lon": self.lon_off, "relAlt": 0, "acheading": self.course, "time": "20170518-15:12:09", "lat": self.lat_off, "alt": self.alt, "RH": self.RH, "pres": self.RH, "DEG": self.temp}}}
        self.sysg = {}
        self.files = {}
        self.jfiles = {}

    def timeStamped(self,pathn,fname, fmt = '{pathn}%Y%m%d-%H%M_{fname}'):
        return datetime.datetime.now().strftime(fmt).format(pathn=pathn,fname=fname)
        
    def Timestamp(self,fmt='%Y%m%d'):
         return datetime.datetime.now().strftime(fmt).format()
    
    def Transmission(self,reported):
        tr = int(''.join(reported),16)
        return tr
        
    def Lattitude_Offset(self,reported):
        dec = int(''.join(reported),16)
        lao = 40.-(3./10000.)*dec
        return lao
        
    def Longitude_Offset(self,reported):
        dec = int(''.join(reported),16)
        lno = 100.-(3./10000.)*dec
        return lno
        
    def Altitude(self,reported):
        dec = int(''.join(reported),16)
        a = dec/10
        return a
        
    def Pressure_Offset(self,reported):
        dec = int(''.join(reported),16)
        p = (dec+45000)/10
        return p
        
    def Temperature(self,reported):
        dec = int(''.join(reported),16)
        T = dec/100
        return T
        
    def Humidity(self,reported):
        dec = int(''.join(reported),16)
        h = dec/100
        return h
        
    def Ground_Velocity(self,reported):
        dec = int(''.join(reported),16)
        v = dec/10
        return v
        
    def Course_Heading(self,reported):
        dec = int(''.join(reported),16)
        c = dec*2
        return c
      
      ##check if need to use self here or if local variable. if local, CHANGE NAME ##
    def System_Vals(self,sysrem,sysval,val,rem):
        try:
            if sysval==0: #hour
                sysrem[0] = val
         
            elif sysval==1: #minute
                sysrem[1] = val
    
            elif sysval==2: #second
                sysrem[2] = val
            elif sysval==3: #voltage
                sysrem[3] = val*100-200
    
            elif sysval==4: #lat offset integer
                sysrem[4] = val
         
            elif sysval==5: #lon offset integer
                sysrem[6] = val        
           
            elif sysval==6: #pressure offset*1000 
                sysrem[6] = val*1000
       
            elif sysval==7: #gps offset
                sysrem[7] = val
           
            else:
                return
    
        except NameError:
            print "Error calculating System Values for remote:",rem
        
    def System(self,rem,code,val):
        sysval = int(code,16)
        v = int(val,16)
        try:
            self.System_Vals(self.sysg[rem],sysval,v,rem)
            return self.sysg[rem]
        except KeyError:
            self.sysg[rem]=np.zeros(8)
            self.System_Vals(self.sysg[rem],sysval,v,rem)
            return self.sysg[rem]
        
    
    def raw2vals(self,data):
        ## Function to return calculated values (based off of datagram specs) 
        ## for corresponding incoming byte.  
        if len(data) > 23:
            try:
                ## ms since booting ##
                self.ms = int(data[1])
                self.s = self.ms/1000
                ## remote number ##
                self.remote = int(data[2],16)
                ## RSSI (signal strength) ##
                self.sig = int(data[3])
                ## Distance
                self.dis = int(data[4])
                ## Azimuth
                self.az = int(data[5])
                ## bytes in payload (17 now) ##
                self.byte_num = int(data[6])
                
                ## Sequence number(increments each transmission) ##
                raw_tnum = data[7]
                self.tnum = self.Transmission(raw_tnum)
                
                ## Lattitude Offset (deg) ##
                raw_lat_offset = list(reversed(data[8:10]))
                self.lat_off = self.Lattitude_Offset(raw_lat_offset)
                
                ## Longitude Offset (deg) ##
                raw_lon_offset = list(reversed(data[10:12]))
                self.lon_off = self.Longitude_Offset(raw_lon_offset)
               
                ## Altitude (m above Sea Level) ##
                raw_alt = list(reversed(data[12:14]))
                self.alt = self.Altitude(raw_alt)
                
                ## Pressure (Pa) ##
                raw_press = list(reversed(data[14:16]))
                self.press = self.Pressure_Offset(raw_press)
                
                ## Temperature (degrees C)
                raw_temp = list(reversed(data[16:18]))
                self.temp = self.Temperature(raw_temp)
                
                ## Humidity (percentage)
                raw_hum = list(reversed(data[18:20]))
                self.RH = self.Humidity(raw_hum)
                
                ## Ground Velocity (m/s) ##
                raw_grnd_vel = data[20]
                self.grnd_vel = self.Ground_Velocity(raw_grnd_vel)    
                
                ## Course Heading (degrees) ##
                raw_course = data[21]
                self.course = self.Course_Heading(raw_course)
                
                ## System values
                raw_code = data[22]
                raw_cval = data[23]
                
                self.vals = np.array([self.s,self.remote,self.sig,self.dis,self.az,self.byte_num,
                         self.tnum,self.lat_off,self.lon_off,self.alt,
                         self.press,self.temp,self.RH,self.grnd_vel,self.course])
            except NameError:
                print NameError
        elif len(data) ==23:
            try:
                ## ms since booting ##
                self.ms = int(data[1])
                self.s = self.ms/1000
                ## remote number ##
                self.remote = int(data[2],16)
                ## RSSI (signal strength) ##
                self.sig = int(data[3])
                ## bytes in payload (17 now) ##
                self.byte_num = int(data[4])
                
                ## Sequence number(increments each transmission) ##
                raw_tnum = data[5]
                self.tnum = self.Transmission(raw_tnum)
                
                ## Lattitude Offset (deg) ##
                raw_lat_offset = list(reversed(data[6:8]))
                #self.lat_off = self.Lattitude_Offset(raw_lat_offset)
                self.lat_off =40.015;
                
                ## Longitude Offset (deg) ##
                raw_lon_offset = list(reversed(data[8:10]))
                #self.lon_off = -self.Longitude_Offset(raw_lon_offset)
                self.lon_off = -105.257;
               
                ## Altitude (m above Sea Level) ##
                raw_alt = list(reversed(data[10:12]))
                self.alt = self.Altitude(raw_alt)
                
                ## Pressure (Pa) ##
                raw_press = list(reversed(data[12:14]))
                self.press = self.Pressure_Offset(raw_press)
                
                ## Temperature (degrees C)
                raw_temp = list(reversed(data[14:16]))
                self.temp = self.Temperature(raw_temp)
                
                ## Humidity (percentage)
                raw_hum = list(reversed(data[16:18]))
                self.RH = self.Humidity(raw_hum)
                
                ## Ground Velocity (m/s) ##
                raw_grnd_vel = data[18]
                self.grnd_vel = self.Ground_Velocity(raw_grnd_vel)    
                
                ## Course Heading (degrees) ##
                raw_course = data[19]
                self.course = self.Course_Heading(raw_course)
                
                ## System values
                raw_code = data[20]
                raw_cval = data[21]
                
                self.vals = np.array([self.s,self.remote,self.sig,self.byte_num,
                         self.tnum,self.lat_off,self.lon_off,self.alt,
                         self.press,self.temp,self.RH,self.grnd_vel,self.course])
            except NameError:
                print NameError
        
        system_vals = self.System(self.remote,raw_code,raw_cval)
        self.vals = np.append(self.vals,system_vals)
        
        try:
            gps = data[25][1:]
            self.vals = np.append(self.vals,gps)
        except IndexError:
            pass
        
        self.vals = np.around(self.vals,decimals=6)
        print self.vals
        return self.vals
    
    def createCSVFile(self,num,t):
        self.files[num]=self.pathcsv+t+'_csvrem'+str(num)+'.csv'
        f = open(self.files[num],'a')
        f.writelines(self.header)
        f.close()
        
    def createJSONFile(self,num,t):
        self.jfiles[num]=self.pathjs+'live_data'+'.json'
        #self.jfiles[num]=self.pathjs+'geojson_'+t+'.txt'          
            
    def write_CSV(self,arr,t):
        ## Will detect remote number of incoming data and save it to corresponding 
        ## file. If no file exists for that remote, it calls createFile, which
        ## will create a file for that remote.
        remote = self.remote
        if remote == 3:
            try:
                f = open(self.files[remote],'a')
                f.write(','.join(str(x) for x in arr)+'\n')
                f.close()
            except KeyError:
                self.createCSVFile(remote,t)
                f = open(self.files[remote],'a')
                f.write(','.join(str(x) for x in arr)+'\n')
                f.close()
            except NameError:
                print "Error in saving to CSV file"
        else:
            return
            
    def write_JSON(self,arr,t):
        remote = self.remote
        try:
            #j = open(self.jfiles[remote],'w')
            st = (self.grnd_vel,self.sysg[remote][3],self.lon_off,self.course,self.lat_off,self.alt,self.RH,self.press,self.temp)
            payload = {"B": [{"location": {"lat":40.015, "lon":-105.257},"course":0, "id":1}]}
            #payload = {"geometry": {"type": "Point","coordinates": [self.lon_off,self.lat_off ]}, "type": "Feature", "properties": {"jsonString": '{"acgndspd": %s, "acvolt": %s, "lon": %s, "relAlt": 0, "acheading": %s, "time": "20170518-15:12:09", "lat": %s, "alt": %s, "RH": %s, "pres": %s, "DEG": %s}' %st}}
            #json.dump(payload,j)
            return json.dumps(payload)
            #j.close()
        except KeyError:
            #self.createJSONFile(remote,t)
            #j = open(self.jfiles[remote],'w')
            payload = {"B": [{"location": {"lon":40.015, "lat":-105.257},"course":0, "id":1}]}
            #payload = {"geometry": {"type": "Point","coordinates": [self.lon_off,self.lat_off ]}, "type": "Feature", "properties": {"jsonString": '{"acgndspd": %s, "acvolt": %s, "lon": %s, "relAlt": 0, "acheading": %s, "time": "20170518-15:12:09", "lat": %s, "alt": %s, "RH": %s, "pres": %s, "DEG": %s}' %st}}
            #json.dump(payload,j)
            return json.dumps(payload)
            #return json.dumps({"geometry": {"type": "Point","coordinates": [self.lon_off,self.lat_off ]}, "type": "Feature", "properties": {"jsonString": {"acgndspd": self.grnd_vel, "acvolt": self.sysg[remote][3], "lon": self.lon_off, "relAlt": 0, "acheading": self.course, "time": "20170518-15:12:09", "lat": self.lat_off, "alt": self.alt, "RH": self.RH, "pres": self.press, "DEG": self.temp}}},j)
            #j.close()
        except NameError:
            print "Error in saving to JSON file"
            
            
    def CalcData(self,sercxn):
        ## Loop that takes in serial data and calculates values from hex. To exit
        ## loop, press Ctrl-C
    
		ts = self.Timestamp()
		#outfile = open(self.timeStamped(self.pathcsv,"rawdata.txt"),'a')
		
		raw = sercxn.readline()
		if raw[0]=='{':
			#outfile.writelines(raw)
			vals = raw.split()
			out = self.raw2vals(vals)
			#self.write_CSV(out,ts)
			data = self.write_JSON(out,ts)
			
		elif raw[0]=='[':
			#outfile.writelines(raw)
			try:
				vals.append(re.split('\s|,',re.sub('[[\]]','',raw)))
			except NameError:
				pass
			
			data = []
			
		else:
			#print raw
			#print raw
			data = []
		
		return data
					
		

#                try: 
#                    out = self.raw2vals(vals) 
#                    self.write_CSV(out,ts)
#                    self.write_JSON(out,ts)
#                    
#                except UnboundLocalError:
#                    pass
                    
        # except KeyboardInterrupt:
            # sercxn.close()
            # outfile.close()
            # print 'Keyboard Interrupt, Exiting Program'   



def main():
    ds = DataStream()
    ser = serial.Serial()
    ser.port = 'COM3'
    try:
        ser.open()
    except serial.SerialException:
        ser.close()
        ser.open()
    ds.CalcData(ser)                

if __name__=="__main__":
    main()



