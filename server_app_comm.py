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
        self.render("comm_aware_vis.html")

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
        #TODO! Look at the weather version to see how we fixed things
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
        #TODO!: NEED TO STILL INITIALIZE THESE
        lastTime = time.time() #size of frequency sets
        dTime = time.time() #size of frequency sets
        while not shutdown_event.is_set():
            #need to get the dT
            nowTime = time.time()
            #for i in range(0,len(lastTime)):
            #	dTime[i] = nowTime - lastTime[i]
            dTime = nowTime - lastTime

            if (dTime >= 1):
                json_data = ProcessFrequencySet(self.FrequencyQues)
                if json_data: #always true with new setup
                    if msg_cl:
                        for c in msg_cl:
                            c.write_message(json_data)
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
    pass

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
    #TODO! Update these parts
    subNM = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_NETWORK_MANAGER_STATUS,PyPacket.PacketID(PyPacket.PacketPlatform.GROUND_CONTROL_STATION,00).getBytes(),ports[0],'localhost',1)
    #For Aircraft State
    subAS = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_AUTOPILOT_PIXHAWK,PyPacket.PacketID(PyPacket.PacketPlatform.AIRCRAFT,10).getBytes(),ports[1],'localhost',1)
    #For RF Data Msg1
    subRF = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_RF_DATA_MSG,PyPacket.PacketID(PyPacket.PacketPlatform.AIRCRAFT,10).getBytes(),ports[2],'localhost',1)
    #For RF PL Map
    subMP = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_RF_PL_MAP_MSG,PyPacket.PacketID(PyPacket.PacketPlatform.AIRCRAFT,10).getBytes(),ports[3],'localhost',1)

    StreamReaderThreadList = []
    srt1 = Server_Reader.StreamReaderThread(subNM,QueList[0],shutdown_event)
    StreamReaderThreadList.append(srt1)
    srt2 = Server_Reader.StreamReaderThread(subAS,QueList[1],shutdown_event)
    StreamReaderThreadList.append(srt2)
    srt3 = Server_Reader.StreamReaderThread(subRF,QueList[2],shutdown_event)
    StreamReaderThreadList.append(srt3)
    srt4 = Server_Reader.StreamReaderThread(subMP,QueList[3],shutdown_event)
    StreamReaderThreadList.append(srt4)

    #loop through the stream readers and start each of them
    srt1.start()
    srt2.start()
    srt3.start()
    srt4.start()

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