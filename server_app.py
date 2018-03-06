#!/usr/env/python
#import Data_Stream as ds
from tornado import websocket, web, ioloop
import json
import time
import sys
import threading
#import serial

cl = []
msg_cl = []
shutdown_event = threading.Event()

class IndexHandler(web.RequestHandler):
	def get(self):
		#self.render("test_index.html")
		self.render("pf_vis.html")

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
		print 'Started Publishing Thread'
		
	#Change this loop
	def run(self):
		tnum = 3;
		lat0 =40.0071697
		lon0 =-105.2649012
		lat1 =39.956742
		lon1 =-105.166978
		lat2 =40.0405096
		lon2 =-105.2110949
		lat3 =39.9950224
		lon3 =-105.1599398
		latA =40.0008086
		lonA =-105.217618
		latB =39.9743796
		lonB =-105.2673482
		latC =40.040606
		lonC =-105.273153
		#data = {"AC": [{"C":p1, "S":p2},{"C":7, "S":3},{"C":5, "S":5}]}
		data = {"TargetNumber": tnum} 
		data1 = {"Target": [{"location": {"lat": lat1, "lon":lon1}},{"location": {"lat": lat2, "lon":lon2}},{"location": {"lat": lat3, "lon":lon3}}]}
		data2 = {"GCS": {"location": {"lat": lat0, "lon":lon0}}}
		data3 = {"ParticleSet": [{"avgParticle": {"location": {"lat": latA, "lon":lonA}}},{"avgParticle": {"location": {"lat": latB, "lon":lonB}}},{"avgParticle": {"location": {"lat": latC, "lon":lonC}}}]}
		for d in (data1,data2, data3):
			data.update(d)
		#d4 = dict(data.items() + data2.items() + data3.items())
		while not shutdown_event.is_set():
			if data: 
				#data = json.dumps(data_2)
				data_out = json.dumps(data)
				#print(data_out)
				#print(data['TargetNumber'])
				if msg_cl:
					for c in msg_cl:
						c.write_message(data_out)
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
