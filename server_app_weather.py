#!/usr/env/python
# import Data_Stream as ds
from tornado import websocket, web, ioloop
import json
import time
import sys
import threading
import Queue
# import paramiko not installed yet

from multiprocessing import Process, Lock, Queue

# import serial

sys.path.insert(0, '../PyUAS')  # get the path to the PyUAS Folder
sys.path.insert(0, '../PyUAS/protobuf')  # get the path to the protobuf format
import Subscriber
import PyPacket
import Server_Reader
import PyPackets_pb2
import PyPacketLogger
# External Libs
from google.protobuf import json_format

# import Server_Reader

cl = []
msg_cl = []
shutdown_event = threading.Event()
recording = False
thefilename = "base.text"

class IndexHandler(web.RequestHandler):
    def get(self):
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

    def on_message(self, message):
        command = message.split(",")[0]
        argument = message.split(",")[1]
        if command == "Start_Stream":
            # add this client to receive data updates
            msg_cl.append(self)
            print 'Added client to streaming list'
        elif command == "Stop_Stream":
            # remove this client from receiving data updates
            msg_cl.remove(self)
            print 'Removed client from streaming list'
        elif command == "StartSaving":
            # Start saving data to a log file
            recording = True
            thefilename = argument
        elif command == "StopSaving":
            # Stop saving data to a log file
            recording = False
        else:
            # Not implemented or incorrect message
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
        self.FrequencySets = [1]  # list of frequencies
        self.FrequencyQues = ques  # a list of que lists
        self.myrecordlog = None

    # Change this loop
    def run(self):
        # NEED TO STILL INITIALIZE THESE
        lastTime = time.time()  # size of frequency sets
        dTime = time.time()  # size of frequency sets
        lastRecordingStatus = recording
        while not shutdown_event.is_set():
            # need to get the dT
            nowTime = time.time()
            # for i in range(0,len(lastTime)):
            #	dTime[i] = nowTime - lastTime[i]
            dTime = nowTime - lastTime

            if lastRecordingStatus != recording:
                if recording:
                    self.startDataRecording(thefilename)
                else:
                    self.endDataRecording()

            if (dTime >= 1):
                json_data = ProcessFrequencySet(self.FrequencyQues)
                if json_data:  # always true with new setup
                    if msg_cl:
                        for c in msg_cl:
                            c.write_message(json_data)
                            if recording:
                                myrecordlog.write(json_data + '\n')
                                #write the json stuff to a file
                            print 'sent message'
                # Now update the last time this frequency set was handled
                lastTime = time.time()
        # End of while loop
        print 'Stopping Web Publishing Thread'

    def startDataRecording(self,filename):
        self.myrecordlog = open(filename, 'w')
        # we should look to see if this file already exists or something
        #also check if it is already open

    def endDataRecording(self):
        self.myrecordlog.flush()
        self.myrecordlog.close()

def ProcessFrequencySet(QueList):
    # grab the top msg from each que in that frequency set
    outdata = {}
    for q in QueList:
        if not q.empty():
            # add logical check for getting no wait (future work)
            out = q.get()  # pop off top msg
            # How do i check / verify that the time difference between each top msg in the que is not significant
            msg = out[0]
            thistype = out[1]
            outdata[thistype] = msg
    # parse the final dictionary into json
    return json.dumps(outdata)

app = web.Application([
    (r'/', IndexHandler),
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
    (r'/(favicon.ico)', web.StaticFileHandler, {'path': '../'}),
    (r'/(rest_api_example.png)', web.StaticFileHandler, {'path': './'}),
    (r'/js/(.*)', web.StaticFileHandler, {'path': './js/'}),
    (r'/css/(.*)', web.StaticFileHandler, {'path': './css/'}),
    (r'/images/(.*)', web.StaticFileHandler, {'path': './images/'}),
])

def WebReaderSide(l, QueList):
    # QueList = [Q1,Q2,Q3,Q4]
    # Create A set Number of Stream Reader Threads
    print 'Created WebReaderSide'
    # List of ports being used
    ports = [10000, 10005, 10010, 10015]
    # Create all the subscribers
    # For Network Manager
    subNM = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_NETWORK_MANAGER_STATUS,
                                  PyPacket.PacketID(PyPacket.PacketPlatform.GROUND_CONTROL_STATION, 00).getBytes(),
                                  ports[0], 'localhost', 1)
    # For Drifters
    subBS = Subscriber.Subscriber(PyPacket.PacketDataType.PKT_BALLOON_SENSOR_SET,
                                  PyPacket.PacketID(PyPacket.PacketPlatform.AIRCRAFT, 90).getBytes(), ports[1],
                                  'localhost', 1)

    #Add one for cars


    #Add one for etc

    StreamReaderThreadList = []
    srt1 = Server_Reader.StreamReaderThread(subNM, QueList[0], shutdown_event)
    StreamReaderThreadList.append(srt1)
    srt2 = Server_Reader.StreamReaderThread(subBS, QueList[1], shutdown_event)
    StreamReaderThreadList.append(srt2)

    # loop through the stream readers and start each of them
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


def WebServerSide(l, QueList):
    l.acquire()
    print 'Created Web Server Side'
    l.release()
    app.listen(8888)
    # start the publishing thread
    publishingTask = PublishingThread(QueList)
    publishingTask.start()
    # start the IO loop for server side
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
    # Generate teh Ques
    AllQueList = []
    for i in range(4):
        newQue = Queue()
        AllQueList.append(newQue)

    # Generate A bunch of things for the Reader Side
    pWS = Process(target=WebServerSide, args=(lock, AllQueList))
    pWR = Process(target=WebReaderSide, args=(lock, AllQueList))
    pWS.start()
    pWR.start()
    # Join the sub-processes together
    pWR.join()
    pWS.join()
