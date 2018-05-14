#!/usr/env/python
#import Data_Stream as ds
from tornado import websocket, web, ioloop
import json
import time
import sys
import threading
import Queue
#import paramiko not installed yet

from multiprocessing import Process, Lock, Queue
#import serial

sys.path.insert(0,'../PyUAS') #get the path to the PyUAS Folder
sys.path.insert(0,'../PyUAS/protobuf') #get the path to the protobuf format
import Subscriber
import PyPacket
import Server_Reader
import PyPackets_pb2
#External Libs
from google.protobuf import json_format
#import Server_Reader

cl = []
msg_cl = []
shutdown_event = threading.Event()

class IndexHandler(web.RequestHandler):
    def get(self):
        #self.render("test_index.html")
        self.render("weather_vis.html")

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl:
            cl.append(self)
            print 'Client Connected'

    def on_close(self):
        if self in cl:
            cl.remove(self)    
            msg_cl.remove(self)
            print 'Client Disconnected'

    '''
    StartSaving:
    StopSaving:
    System_Checkout
    Start_Mission, .... 
    Stop_Mission
    '''

    def on_message(self, message):
        command = message.split(",")[0]
        if command == "Start_Stream":
            #add this client to receive data updates
            msg_cl.append(self)
            print 'Added client to streaming list'
        elif command == "Stop_Stream":
            #remove this client from receiving data updates
            msg_cl.remove(self) 
            print 'Removed client from streaming list'
        elif command == "StartSaving":
            #Start saving data to a log file
            setLoggingMode = 1;
        elif command == "StopSaving":
            #Stop saving data to a log file
            setLoggingMode = 0;
        elif command == "System_Checkout":
            #Start A System Checkout
            SystemCheckout();
        elif command == "Start_Mission":
            #Start the Mission
            startMission(message)
        elif command == "Stop_Mission":
            #Stop the mission
            stopMission()
        else:
            #Not implemented or incorrect message
            print("Message not understood:" + message)


class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        pass

    @web.asynchronous
    def post(self):
        pass
        
class ServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        print 'Started Server Thread'
        self.io_loop = ioloop.IOLoop.current()
        
    def run(self):
        self.io_loop.start()
        
    def stop(self):
        print 'Stopping Server Thread'
        self.io_loop.stop()
        print 'Closing IO Loop'
        self.io_loop.close()

class PublishingThread(threading.Thread):
    def __init__(self, ques):
        threading.Thread.__init__(self)
        print 'Started Publishing Thread'
        self.FrequencySets = [1] #list of frequencies
        self.FrequencyQues = ques #a list of que lists 

    #Change this loop
    def run(self):
        '''
        #Keep running until we want to shutdown
        while not shutdown_event.is_set():
            json_data = createTestJson()
            if json_data:
                #print json_data
                if msg_cl:
                    for c in msg_cl:
                        print('Sent Message')
                        c.write_message(json_data)
            time.sleep(.5) 
        '''
        
        #NEED TO STILL INITIALIZE THESE
        lastTime = time.time() #size of frequency sets
        dTime = time.time() #size of frequency sets
        while not shutdown_event.is_set():
            #need to get the dT
            nowTime = time.time()
            #for i in range(0,len(lastTime)):
            #    dTime[i] = nowTime - lastTime[i]
            dTime = nowTime - lastTime 
            
            if (dTime >= 1):
                json_data = ProcessFrequencySet(self.FrequencyQues)
                if json_data: #always true with new setup
                    if msg_cl:
                        for c in msg_cl:
                            c.write_message(json_data)
                            print json_data
                            print 'sent message'
                #Now update the last time this frequency set was handled
                lastTime = time.time()
        #End of while loop
        print 'Stopping Web Publishing Thread'

def SystemCheckout():
    #DO stuff here 
    pass

def startMission(mission_string):
    #Do stuff here
    pass
    stringList = mission_string.split(",") #Cmd, Username, Pwd, Mission, Time, Logger
    systemName = stringList[1]
    pwd = stringList[2]
    #ssh to the vehicle and perform the action
    ssh = paramiko.SSHClient()
    ssh.connect(server, username=systemName, password=pwd)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)
    #Need some try/exception lists for password etc
    #Might recommend making a function for just running a command given host and command

    #When finished
    ssh.close() #close the ssh connection
    
def stopMission():
    #Do stuff here
    pass

def run_cmd(host_ip, cmd_list):
    #do stuff here
    pass

def ProcessFrequencySet(QueList):
    #grab the top msg from each que in that frequency set
    outdata = {}
    for q in QueList:
        if not q.empty():
            #add logical check for getting no wait (future work)
            out= q.get() #pop off top msg
            #How do i check / verify that the time difference between each top msg in the que is not significant
            msg = out[0]
            thistype = out[1]
            outdata[thistype] = msg
    #parse the final dictionary into json
    return json.dumps(outdata)
    

def createTestJson():
    #Hard Code some json strings
    #Msg4 Aircraft State
    msg4 = PyPackets_pb2.AircraftPixhawkState()
    msg4.packetNum = 1;
    msg4.ID = "Test"
    msg4.time = time.time()
    msg4.LLA_Pos.x = 40.014984
    msg4.LLA_Pos.y = -105.270546
    msg4.LLA_Pos.z = 100 #AGL
    msg4.velocity.x = 10
    msg4.velocity.y = 0
    msg4.velocity.z = 0
    msg4.attitude.x = 0
    msg4.attitude.y = 0
    msg4.attitude.z = 0
    msg4.airspeed = 15
    msg4.mode = "IDK"
    msg4.batteryStatus.current = 10
    msg4.batteryStatus.voltage = 11.7
    msg4.currentWaypoint.LLA_Pos.x = 40.000267
    msg4.currentWaypoint.LLA_Pos.y = -105.100021
    msg4.currentWaypoint.LLA_Pos.z = 100
    #Msg3 NM Status
    msg3 = PyPackets_pb2.NMStatus()
    msg3.packetNum = 1
    msg3.ID = "Test"
    msg3.time = time.time()
    msg3.numberOfMsgs = 10
    msg3.avgTimeDelay = 5
    msg3.totalMsgsRcv = 100
    for i in range(3):
        new = msg3.subs.add()
        new.id = "sub"
        new.datatype = "AC10"
        new.port = 10000
        new.address = "192.158.10.101"
        new.msgfreq = 0.1

    msg3.messagesInQue = 12
    msg3.numberOfLocalSubscribers = 3
    msg3.numberOfGlobalSubscribers = 0
    #Msg2 RF Sensor
    msg2 = PyPackets_pb2.RF_Data_Msg()
    msg2.packetNum = 1
    msg2.ID = "test"
    msg2.time = time.time()
    msg2.lla.x = 40.1
    msg2.lla.y = 100.0
    msg2.lla.z = 90
    msg2.attitude.x = 0
    msg2.attitude.y = 0
    msg2.attitude.z = 0
    msg2.airspeed = 1
    for i in range(3):
        new = msg2.rfNode.add()
        new.chanID = "1"
        new.rssi = 10
        new.pl_msr = 5
        new.pl_error = 0
        new.xgridNum
    #Msg1 RF Map
    msg1 = PyPackets_pb2.RF_PL_Map_Msg()
    msg1.packetNum = 1
    msg1.ID = "test"
    msg1.time = time.time()
    msg1.gp_iteration_number = 1
    msg1.xGrids = 1
    msg1.yGrids = 1
    msg1.xSpacing = 1
    msg1.ySpacing = 1
    for i in range(4):
        new = msg1.cell.add()
        new.xgridNum = 10
        new.ygridNum = 15
        new.est_path_loss = 5
        new.path_loss_err = 1
        new.pred_path_loss = 2
    
    msg1.centerPoint.x = 40.389
    msg1.centerPoint.y = -105.39
    msg1.centerPoint.z = 0
    msg1.gp_learning_time = 10
    msg1.gp_prediction_time = 12
    msg1.bestLocation.LLA_Pos.x = 39.742043
    msg1.bestLocation.LLA_Pos.y = -104.991531
    msg1.bestLocation.LLA_Pos.z = 0
    msg1.bestLocation.cost = 100
    msg1.costFromA = 60
    msg1.costFromB = 40

    #Serialize and combine
    json_string = json_format.MessageToJson(msg1)
    dictOut = json.loads(json_string)
    json_string = json_format.MessageToJson(msg2)
    dictOut2 = json.loads(json_string)
    json_string = json_format.MessageToJson(msg3)
    dictOut3 = json.loads(json_string)
    json_string = json_format.MessageToJson(msg4)
    dictOut4 = json.loads(json_string)
    
    dictionaryNew = {}
    dictionaryNew['AircraftPixhawkState'] = dictOut4
    dictionaryNew['RF_PL_Map_Msg'] = dictOut
    dictionaryNew['RF_Data_Msg'] = dictOut2
    dictionaryNew['NMStatus'] = dictOut3
    return json.dumps(dictionaryNew)

app = web.Application([
    (r'/', IndexHandler),
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
    (r'/(favicon.ico)', web.StaticFileHandler, {'path': '../'}),
    (r'/(rest_api_example.png)', web.StaticFileHandler, {'path': './'}),
    (r'/js/(.*)',web.StaticFileHandler, {'path': './js/'}),
    (r'/css/(.*)',web.StaticFileHandler, {'path': './css/'}),
    (r'/images/(.*)',web.StaticFileHandler, {'path': './images/'}),
])


def WebReaderSide(l,QueList):
    #QueList = [Q1,Q2,Q3,Q4]
    #Create A set Number of Stream Reader Threads
    print 'Created WebReaderSide'
    #List of ports being used
    ports = [10000,10005,10010,10015]
    #Create all the subscribers
    #For Network Manager
    subNM = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_NETWORK_MANAGER_STATUS,PyPacket.PacketID(PyPacket.PacketPlatform.GROUND_CONTROL_STATION,00).getBytes(),ports[0],'localhost',1)
    #For Aircraft State
    subBS = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_BALLOON_SENSOR_SET,PyPacket.PacketID(PyPacket.PacketPlatform.AIRCRAFT,90).getBytes(),ports[1],'localhost',1)

    StreamReaderThreadList = []
    srt1 = Server_Reader.StreamReaderThread(subNM,QueList[0],shutdown_event)
    StreamReaderThreadList.append(srt1)
    srt2 = Server_Reader.StreamReaderThread(subBS,QueList[1],shutdown_event)
    StreamReaderThreadList.append(srt2)
    
    #loop through the stream readers and start each of them
    srt1.start()
    srt2.start()
    
    while threading.active_count() > 1:
        try:
            l.acquire()
            print 'Running with %s Readers' % len(StreamReaderThreadList)
            l.release()
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            shutdown_event.set()
    sys.exit()

def WebServerSide(l,QueList):
    l.acquire()
    print 'Created Web Server Side'
    l.release()
    app.listen(8888)
    #start the publishing thread
    publishingTask = PublishingThread(QueList)
    publishingTask.start()
    #start the IO loop for server side
    serverTask = ServerThread()
    serverTask.start()

    while threading.active_count() > 1:
        try:
            l.acquire()
            print 'Running with %s Clients' % len(cl)
            l.release()
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            shutdown_event.set()
            serverTask.stop()
    sys.exit()

if __name__ == '__main__':
    lock = Lock()
    #Generate teh Ques
    AllQueList = []
    for i in range(4):
        newQue = Queue()
        AllQueList.append(newQue)
    #Generate A bunch of things for the Reader Side
    pWS = Process(target=WebServerSide, args=(lock,AllQueList))
    pWR = Process(target=WebReaderSide, args=(lock,AllQueList))
    pWS.start()
    pWR.start()