'''
server_reader.py
Author: Spencer Watza


The server reader is responsible for reading in messages from a variety of data streams either using PyPacket or IRISS Packet, adding them to different message queues. 

For example, reading in multiple aircraft states and then adding them to a single que for that type of information? Parse the json here (using google protobuf to json for simplicity? or manually?)
'''

#IMPORTS
import sys
import time
import json
import threading
import Queue
import socket
import select

#PyUAS Lib
sys.path.insert(0,'../PyUAS') #get the path to the PyUAS Folder
sys.path.insert(0,'../PyUAS/protobuf') #get the path to the protobuf format
import Subscriber
import PyPacket
import PyPackets_pb2
#External Libs
from google.protobuf import json_format

#CONSTANTS
RECV_BUFF = 8192


def verifyPacketType(datatypeMsg,datatypeWeWant):
	if datatypeMsg == datatypeWeWant:
		return True
	else:
		return False

'''
StreamReaderThread is a IO based thread to handle a single incoming data type of interest from multiple sources. 
datatype = PyPacket.DataType
Sources =  "A specific ID for now"
'''
class StreamReaderThread(threading.Thread):
	def __init__(self, mysubscriber, myQue, shutdown_event): #we need to hand it a queue we built for it in the main area; 
		#setup the threading init
		threading.Thread.__init__(self)
		
		#Set the shutdown event trigger
		self.shutdown = shutdown_event
		self.NM_PORT = 16000 #hardcoded for now
		
		self.PORT = mysubscriber.PORT
		self.IP = mysubscriber.IP
		self.MyQueue = myQue
		
		#Create the subscriber information to send to the Network Manager
		self.sub = mysubscriber
		self.DataType = mysubscriber.TYPE
			
		#go ahead and build the subscriber message
		pkt_id = PyPacket.PacketID(PyPacket.PacketPlatform.SERVER_STATION,00)
		self.pkt = PyPacket.PyPacket()
		self.pkt.setDataType(PyPacket.PacketDataType.PKT_NODE_HEARTBEAT)
		self.pkt.setID(pkt_id.getBytes())
		
		self.submsg = PyPackets_pb2.NodeHeartBeat()
		self.submsg.ID = str(self.pkt.getID())
		#add each o fhte subscribers (FIX)
		new = self.submsg.sub.add()
		new.id = str(mysubscriber.ID)
		new.datatype = str(mysubscriber.TYPE)
		new.port = self.PORT
		new.address = self.IP 
		new.msgfreq = mysubscriber.FREQ
		
	def run(self):
		#Initialize the socket for reading in 
		socketIn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Could put a socket for each ID; however that could get out of hand with the number of sockets?
		socketIn.setblocking(0)
		socketIn.bind(('',self.PORT))
		#Initialize the socket for outgoing sublist message at regular frequency
		socketOut = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		socketOut.setblocking(0)
		
		#Frequency for subscriber messages (every 5s or 10s?)
		sub_rate_msg = 10; #in secs
		last_time = time.time()
		while not self.shutdown.is_set():
			#Loop through readable sockets?
			readable, writable, exceptional = select.select([socketIn],[socketOut],[socketIn]) #is this the right way?? 
			for s in readable:
				#Get data from socket
				dataPkt, address = s.recvfrom(RECV_BUFF)
				print >>sys.stderr, 'recieved "%s" from %s' %(len(dataPkt), address)
				#Assign datapkt as an object
				newPkt = PyPacket.PyPacket()
				newPkt.setPacket(dataPkt)
				#Verify the packet is correct type (unlikely)
				if(verifyPacketType(newPkt.getDataType(),self.DataType)):
					#yes it is the datatype we want / convert to dictionary (pre-json)
					pktData = newPkt.getData()
					#convert to protobuf type
					datastr = str(pktData)
					msg, thisType = PyPacket.TypeDictionaryDispatch[str(self.DataType)]()
					msg.ParseFromString(datastr)
					#convert to json string
					json_string = json_format.MessageToJson(msg)
					#convert back to dictionary
					dictOut = json.loads(json_string)
					#put into que
					self.MyQueue.put([dictOut,thisType]) #could put a time stamp with the dictionary for easy comparison
					print 'loaded message into que'
				#End verified loop
			#end readable
			for s in writable:
				#if it is time to send out the subscriber message
				delta_time = time.time() - last_time
				if (delta_time >= sub_rate_msg):
					#increment certain parts of msg
					self.submsg.packetNum += 1
					self.submsg.time = time.time()
					#store into the packet
					datastr = self.submsg.SerializeToString()
					self.pkt.setData(datastr)
					strOut = self.pkt.getPacket()
					#self.pkt.clearData()
					#write message out
					s.sendto(strOut,('localhost',self.NM_PORT)) #send the message to the local network manager
					last_time = time.time()
			#End SELECT LOOPS
		#End While Loop
		print 'Closing Sockets on a Server Reader'
		socketIn.close()
		socketOut.close()
		