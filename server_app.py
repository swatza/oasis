#!/usr/env/python
import Data_Stream as ds
from tornado import websocket, web, ioloop
import json
import time
import sys
import threading
import serial

cl = []
msg_cl = []
shutdown_event = threading.Event()

class IndexHandler(web.RequestHandler):
	def get(self):
		self.render("test_index.html")

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
		if message == "Start_Stream":
			#add this client to receive data updates
			msg_cl.append(self)
			print 'Added client to streaming list'
		elif message == "Stop_Stream":
			#remove this client from receiving data updates
			msg_cl.remove(self) 
			print 'Removed client from streaming list'
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
	def __init__(self):
		threading.Thread.__init__(self)
		self.ds_obj = ds.DataStream()
		self.ser = serial.Serial()
		self.ser.port = '/dev/ttyS3' #might change this? 
		try:
			self.ser.open()
		except serial.SerialException:
				self.ser.close()
				self.ser.open()
		print 'Started Publishing Thread'
		
	#Change this loop
	def run(self):
		p1 = 0
		while not shutdown_event.is_set():
			p1 += 1
			if p1 > 10:
				p1 = 0
			p2 = 10 - p1
			data = {"AC": [{"C":p1, "S":p2},{"C":7, "S":3},{"C":5, "S":5}]}
			data_2 = self.ds_obj.CalcData(self.ser)
			#data = {"C": p1, "S": p2}
			#data = {"P1": p1, "P2": p2}
			if data_2: 
				#data = json.dumps(data_2)
				print 'This is gonna be the json string'
				print data_2
				if msg_cl:
					for c in msg_cl:
						c.write_message(data_2)
						print 'Sent Message'
			time.sleep(1)
		print 'Stopping Publishing Thread'
			
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

if __name__ == '__main__':
	app.listen(8888)
	#start the publishing thread
	publishingTask = PublishingThread()
	publishingTask.start()
	#start the IO loop for server side
	serverTask = ServerThread()
	serverTask.start()
	
	while threading.active_count() > 1:
		try:
			print 'Running with %s Clients' % len(cl)
			time.sleep(1)
		except (KeyboardInterrupt, SystemExit):
			shutdown_event.set()
			serverTask.stop()
	sys.exit()
