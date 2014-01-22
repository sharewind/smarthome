"""

"""

import logging
import tornado.escape
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid

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

def message_handler(message):
	logging.info("receive message %s", message)

class WebSocketClient:

	def __init__(self, pi_id, url, callback=None, connect_timeout=None):
		self.pi_id = pi_id
		self.url = url
		self.message_handler = callback
		self.connect_timeout = connect_timeout
		self.ws = None
		self.init_websocket()

	def init_websocket(self):
		def callback(ws):
			logging.info("connectd success! %s", ws.result())
			self.ws = ws.result()
			self.ws.on_message = message_handler
			self.ws.write_message("client say hi")
		self.ws = tornado.websocket.websocket_connect(self.url, callback=callback)  

	def send_message(self, message):
		logging.info("client send message %s", message)
		self.ws.write_message(message)

client = None

def main():
	tornado.options.parse_command_line()
	app = Application()
	app.listen(options.port)

	pi_id = 113696732
	url = "ws://go123.us/smartsocket?pi_id=" + str(pi_id)
	logging.info("connect to %s ....", url)
	client = WebSocketClient(pi_id, url, message_handler)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
