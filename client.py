# -*- coding: utf-8 -*-
"""

"""

import logging
import tornado.escape
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid
import json
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

	@classmethod
	def list_airplay(cls):
		logging.info("airplay start discover")
		cls.server_list = {} 
		def on_discovered(index, fullname, host, port, txtRecord):
			item = {'index':index,'fullname':fullname,'host':host,'port':port, 'txtRecord':txtRecord}
			logging.info("airplay discoverd fullname %s, %s", fullname, fullname.decode('utf8'))
			logging.info("airplay discoverd %s", item)
			cls.server_list[index] = item	
		
		def on_lost(index, name, regtype, domain):
			logging.info("airplay on_list")
			
	
		regtype = '_airplay._tcp'
		cls.mdns.discover(regtype, on_discovered, on_lost)
		cls.ioloop.add_timeout(cls.ioloop.time() + 5, cls.end_discover)

	@classmethod
	def end_discover(cls):
		logging.info("airplay end_discover")
		logging.info("airplay discoverd list %s", cls.server_list)
		
		try:
			#regtype = '_airplay._tcp'
			regtype = '_airplay._tcp'
			cls.mdns.end_discovery(regtype)
			content = json.dumps(cls.server_list)
			get_client().send_message(content)
			cls.server_list = {}
		except Exception,e:
			logging.error("airplay end_discovery error %s", e)


def my_on_message(message):
	logging.info("on message processing .....")
	if "welcome" == message:
		logging.info("server respone welcome!")
		#Airplay.list_airplay()
		return
	elif "airplay_list" == message:
		Airplay.list_airplay()
		#client.send_message("my airplay server")
		return
	else:
		logging.warn("unregonize message=%s", message)
		return

client = None
def get_client():
	global client
	if client is None:
		pi_id = 113696732
		url = "ws://go123.us/smartsocket?pi_id=" + str(pi_id)
		client = WebSocketClient(pi_id, url,my_on_message) 
	return client
	

def main():
	tornado.options.parse_command_line()
	app = Application()
	app.listen(options.port)

	get_client()
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
