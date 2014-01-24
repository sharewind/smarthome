# -*- coding: utf-8 -*-
import logging
import socket
import tornado.escape
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import commands
import uuid
import airplay
import json
import datetime
import time
import redis
import sys
from mdns_util import MDNS

from tornado.options import define, options

define("port", default=4444, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/status", StatusHandler),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class StatusHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("welcome to smart client status!")

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("welcome to smart client!")


class WebSocketClient:

	def __init__(self, pi_id, url, on_message=None, connect_timeout=None):
		self.pi_id = pi_id
		self.url = url
		self.on_message = on_message
		self.connect_timeout = connect_timeout
		self.ws = None
		self.init_websocket()
		self.ioloop = tornado.ioloop.IOLoop.instance()

	def message_handler(self, message):
		logging.info("receive message=%s", message)
		try:
			if message is None:
				self.on_close()
			else:
				self.on_message(message)
		except Exception,e:
			logging.error("on_message error %s", e)

	def on_close(self):
		logging.info("close websocket connection!")
		self.ws = None
		self.ioloop.add_timeout(self.ioloop.time() + 5, self.init_websocket)

	def init_websocket(self):
		logging.info("connect to %s ....", self.url)
		def callback(result):
			if result.exception() is not None:
				logging.error("connect error %s", result.exception())
				self.on_close()
				return 

			logging.info("connectd success! %s", result.result())
			self.ws = result.result()
			self.ws.on_message = self.message_handler
			self.send_message("hi")
		self.ws = tornado.websocket.websocket_connect(self.url, callback=callback)  

	def send_message(self, message):
		logging.info("client send message %s", message)
		if self.ws is None:
			self.init_websocket()
		try:	
			self.ws.write_message(message)
		except Exception,e:
			logging.error("send message error=%s",e)


class Airplay(object):
	ioloop = tornado.ioloop.IOLoop.instance()
	mdns = MDNS(ioloop)
	#mdns.register('My HTTP Service', '_http._tcp', 8080)
	server_list = set()
	is_airplay = False

	@classmethod
	def list_airplay(cls):
		if cls.is_airplay == True:
		    return 
		else:
		    cls.is_airplay = True

		logging.info("airplay start discover")
		cls.server_list = {} 
		def on_discovered(index, servicename, fullname, host, port, txtRecord):
			try:
				if isinstance(servicename, unicode):
					servicename = servicename.encode('utf-8')
					logging.info(servicename)
				ip = socket.gethostbyname(host)
			except Exception,e:
				pass
			item = {'index':index, 'servicename':servicename,'fullname':fullname,'host':host,'port':port,'ip':ip,'txtRecord':txtRecord}
			logging.info("airplay discoverd %s=%s", servicename, item)
			cls.server_list[fullname] = item	
		
		def on_lost(index, name, regtype, domain):
			logging.info("airplay on_list")
			
	
		regtype = '_airplay._tcp'
		cls.mdns.discover(regtype, on_discovered, on_lost)
		cls.ioloop.add_timeout(cls.ioloop.time() + 3, cls.end_discover)

	@classmethod
	def end_discover(cls):
		logging.info("airplay end_discover")
		logging.info("airplay discoverd list %s", cls.server_list)
		
		try:
			#regtype = '_airplay._tcp'
			regtype = '_airplay._tcp'
			cls.mdns.end_discovery(regtype)

			response = None
			if len(cls.server_list) > 0: 
				air_list = []
				for key,value in cls.server_list.items():
					air_list.append(value)
				response = {
					'status':True,
					'code':0,
					'data':air_list,
					'action':'airlist_reply',
				}
			else:
				response = {'status':False, 'code':-1, 'data':None, 'action':'airlist_reply', 'desc':u'未发现airplay设备'}
			logging.info("airlist response=%s",response)
			message = json.dumps(response)
			client.send_message(message)
			cls.server_list = {}
			cls.is_airplay = False
		except Exception,e:
			logging.error("airplay end_discovery error %s", e)


def my_on_message(message):
	logging.info("on message processing .....")

	global airplay_host
	global airplay_port

	try:
		if "welcome" == message:
			#Airplay.list_airplay()
			logging.info("server respone welcome!")
			return

		elif 'airlist' == message:
			Airplay.list_airplay()
			return

		elif "open" == message:
			return

		elif "close" == message:
			return

		elif message.startswith('airbind'):
			logging.info("%s",message[8:])
			try:
			    target = json.loads(message[8:])
			    airplay_host = target["ip"]
			    airplay_port = target["port"] 
			    logging.info('airbind=host:port %s:%s', airplay_host, airplay_port)
			    response = {'status':True, 'code':0, 'action':'airbind_reply','data':'airbind on ' + target['servicename']+ ' success'}
			    client.send_message(json.dumps(response))
			except Exception,e:
				logging.error("airbind error %s",e)
				response = {'status':False, 'code':-1, 'action':'airbind_reply','desc':'airbind on error:' + str(e)}
				client.send_message(json.dumps(response))
			return
			
		#send photo
		elif "photo" == message:
			name = datetime.datetime.now().strftime('%y-%m-%d-%H:%M:%S')
			path = '/root/pi/take_photo/' + name + '.jpg'
			status, msg = commands.getstatusoutput('./take.sh ' + 'photo ' + datetime.datetime.now().strftime('%y-%m-%d-%H:%M:%S'))
			# send
			image = open(path, mode='rb')
			airplay.upload_image(image.read(), sendCallback)

		#take photo
		elif message.startswith('http://'):
			logging.info('display image url=%s on host:port_%s:%s_', message, airplay_host, airplay_port)
			airplay.display_image(message, str(airplay_host), str(airplay_port))
			response = {'status':True, 'code':0, 'action':'image_reply','data':'success'}
			client.send_message(json.dumps(response))

		#send temperature humidity
		elif "env" == message:
			r = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
			t = r.get('temperature')
			h = r.get('humidity')
			ret = {}
			ret['status'] = True
			ret['action'] = "env_reply"
			ret['code'] = 0
			data = []
			data1 = {}
			data1['temperature'] = t
			data1['humidity'] = h
			data.append(data1)
			ret['data'] = data
			client.send_message(json.dumps(ret))

		else:
			logging.warn("unregonize message=%s", message)
			return
	except Exception,e:
		logging.error("process message error %s",e)

client = None
airplay_host = None
airplay_port = None

def get_client(pi_id):
	global client
	if client is None:
		if pi_id is None:
			pi_id = 113696732
		url = "ws://go123.us/smartsocket?pi_id=" + str(pi_id)
		client = WebSocketClient(pi_id, url,my_on_message) 
	return client
	

def sendCallback(msg):
	dict = eval(msg)
        ret = {
        	'status':True,
		'code':0,
        	'action': "photo_reply"
	}
        data = []
        data1 = {}
        data1['big_url'] = dict['big_url']
        data.append(data1)
	ret['data'] = data
	client.send_message(json.dumps(ret))

def main():
	tornado.options.parse_command_line()
	app = Application()
	app.listen(options.port)

	pi_id = None
	if(len(sys.argv) > 1):
		pi_id = sys.argv[1]	
	get_client(pi_id)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
