"""

"""

import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/bind", WeiXinBindHandler),
            (r"/wx", WeiXinHandler),
            (r"/smartsocket", PiSocketHandlerHandler),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):
		token = 'guzhen'
		signature = self.get_argument('signature', None)
		timestamp = self.get_argument('timestamp', None)
		nonce = self.get_argument('nonce', None)
		echostr = self.get_argument('echostr', None)
		logging.info(token) 
		logging.info( signature )
		logging.info( timestamp )
		logging.info( nonce )
		logging.info( echostr)
		tmpList = [token, timestamp, nonce]
		tmpList.sort()
		tmpstr = "%s%s%s" % tuple(tmpList)
		hashstr = hashlib.sha1(tmpstr).hexdigest()
		logging.info( hashstr)
		if hashstr == signature:
			self.finish(echostr) 
		else:
			self.finish('None')

	def post(self):
		msg = self.parse_msg()
		logging.info( msg)
		#设置返回数据模板	
		#纯文本格式
		textTpl = """<xml>
		<ToUserName><![CDATA[%s]]></ToUserName>
		<FromUserName><![CDATA[%s]]></FromUserName>
		<CreateTime>%s</CreateTime>
		<MsgType><![CDATA[%s]]></MsgType>
		<Content><![CDATA[%s]]></Content>
		<FuncFlag>0</FuncFlag>
		</xml>"""
		#图文格式
		pictextTpl = """<xml>
		<ToUserName><![CDATA[%s]]></ToUserName>
		<FromUserName><![CDATA[%s]]></FromUserName>
		<CreateTime>%s</CreateTime>
		<MsgType><![CDATA[news]]></MsgType>
		<ArticleCount>1</ArticleCount>
		<Articles>
		<item>
		<Title><![CDATA[%s]]></Title>
		<Description><![CDATA[%s]]></Description>
		<PicUrl><![CDATA[%s]]></PicUrl>
		<Url><![CDATA[%s]]></Url>
		</item>
		</Articles>
		<FuncFlag>1</FuncFlag>
		</xml> """
		#判断Message类型，如果等于"Event"，表明是一个新关注用户
		if msg["MsgType"] == "event":
			if msg["Event"] == "subscribe":
				# self.bind()
				logging.info('text')
				echostr = textTpl % (
					msg['FromUserName'], msg['ToUserName'], str(int(time.time())), msg['MsgType'],
					u"欢迎关注！")
			else:
				# self.unbind()
				echostr = None
		else:
			logging.info('pictext')
			echostr = pictextTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), ' ', ' ', ' ', ' ')

		logging.info(echestr)
		self.finish(echostr) 

	def parse_msg(self):
		"""
		这里是用来解析微信Server Post过来的XML数据的，取出各字段对应的值，以备后面的代码调用，也可用lxml等模块。
		"""
		recvmsg = self.request.body
		logging.info( recvmsg)
		root = ET.fromstring(recvmsg)
		logging.info( root)
		msg = {}
		for child in root:
			logging.info( child)
			msg[child.tag] = child.text
		return msg

	def bind(self, pid, sn):

		return

	def unbind(self, pid):

		return


class PiSocketHandlerHandler(tornado.websocket.WebSocketHandler):
	pi_clients = dict()
	clients_pi = dict()
	pi_wx_dict = dict()
	wx_pi_dict = dict()
	#cache = []
	#cache_size = 200

	def allow_draft76(self):
		# for iOS 5.0 Safari
		return True
	
	def open(self):
		pi_id = self.get_argument("pi_id",None)
		logging.info("open client pi_id %s", pi_id)
		if not pi_id:
			logging.error("Error no pi_id header set")
			return 
		PiSocketHandlerHandler.pi_clients[pi_id] = self
		PiSocketHandlerHandler.clients_pi[self] = pi_id
		self.write_message("welcome to smart service!")

	def on_close(self):
		pi_id = self.get_argument("pi_id",None)
		logging.info("close client pi_id %s", pi_id)
		if not pi_id:
			logging.error("Error no pi_id header set")
			return 
		del PiSocketHandlerHandler.pi_clients[pi_id]
		del PiSocketHandlerHandler.pi_wx_dict[pi_id]

	@classmethod
	def bind_wx(cls, wx_id, pi_id):
		if (not wx_id) or (not pi_id):
			logging.error("Error bind pi client! wx_id=%s, pi_id=%s", wx_id, pi_id)
			return 
		if not PiSocketHandlerHandler.pi_clients.get(pi_id):
			logging.error("Error bind pi client not connected! wx_id=%s, pi_id=%s", wx_id, pi_id)
			return 

		if cls.wx_pi_dict.get(wx_id):
			logging.error("bind wx_id repeat! wx_id=%s, pi_id=%s", wx_id, pi_id)
			return
		if cls.pi_wx_dict.get(pi_id):
			logging.error("bind pi_id repeat! wx_id=%s, pi_id=%s", wx_id, pi_id)
			return

		cls.wx_pi_dict[wx_id] = pi_id
		cls.pi_wx_dict[pi_id] = wx_id
		

#    @classmethod
#    def update_cache(cls, chat):
#        cls.cache.append(chat)
#        if len(cls.cache) > cls.cache_size:
#            cls.cache = cls.cache[-cls.cache_size:]

	@classmethod
	def send_message(cls, wx_id, message):
		logging.info("sending message to wx_id=%s, message=%s", wx_id, message)
		
		pi_id = cls.wx_pi_dict.get(wx_id)
		client = cls.pi_clients.get(pi_id)
		if not cls.wx_pi_dict.get(wx_id) or not client:
			logging.error("Error pi client not connect")
			return

		try:
			client.write_message(message)
		except:
			logging.error("Error sending message", exc_info=True)

	def on_message(self, message):
		pi_id = self.get_argument("pi_id",None)
		logging.info("got message client pi_id=%s,message=%s", pi_id, message)
		if not pi_id:
			logging.error("Error no pi_id header set")
			return 
		
		if not PiSocketHandlerHandler.pi_clients.get(pi_id):
			logging.error("on_message client not regiester")
			return 

		if not PiSocketHandlerHandler.pi_wx_dict.get(pi_id):
			logging.error("on_message not bind wx")
			return
		
        #parsed = tornado.escape.json_decode(message)
        #chat = {
        #    "id": str(uuid.uuid4()),
        #    "body": parsed["body"],
        #    }
        #chat["html"] = tornado.escape.to_basestring(
        #    self.render_string("message.html", message=chat))

        #PiSocketHandlerHandler.update_cache(chat)
        #PiSocketHandlerHandler.send_updates(chat)

class WeiXinBindHandler(tornado.web.RequestHandler):
    def get(self):
		wx_id = "185980656"
		pi_id = "113696732"
		PiSocketHandlerHandler.bind_wx(wx_id, pi_id)
		PiSocketHandlerHandler.send_message(wx_id, "hello")
		self.write("bind ok")

class WeiXinHandler(tornado.web.RequestHandler):
    def get(self):
		wx_id = "185980656"
		pi_id = "113696732"
		PiSocketHandlerHandler.send_message(wx_id, "hello")
		self.write("send message ok")


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.autoreload.start(io_loop=None, check_time=500)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
