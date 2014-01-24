# coding=utf-8
"""

"""
from tornado.concurrent import TracebackFuture
import logging
import collections
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.gen
import os.path
import uuid
import tornado.autoreload
import hashlib
import xml.etree.ElementTree as ET
import urllib2
import json
import time
import redis
import random

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
cache = redis.Redis(host='107.170.255.136', port=6379, db=0)
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

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/bind", WeiXinBindHandler),
            (r"/wx", WeiXinHandler),
            (r"/smartsocket", PiSocketHandler),
        ]
        settings = dict(
            # cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
        	static_path=os.path.join(os.path.dirname(__file__), "static"),
            # xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):

	

	def get(self):
		token = 'guzhen'
		signature = self.get_argument('signature', None)
		timestamp = self.get_argument('timestamp', None)
		nonce = self.get_argument('nonce', None)
		response = self.get_argument('response', None)
		# logging.info(token) 
		# logging.info( signature )
		# logging.info( timestamp )
		# logging.info( nonce )
		# logging.info( response)
		tmpList = [token, timestamp, nonce]
		tmpList.sort()
		tmpstr = "%s%s%s" % tuple(tmpList)
		hashstr = hashlib.sha1(tmpstr).hexdigest()
		# logging.info( hashstr)
		if hashstr == signature:
			self.finish(response) 
		else:
			self.finish('验证失败')

	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def post(self):
		msg = self.parse_msg()
		response = None
		logging.info( msg)
		#设置返回数据模板	
		#纯文本格式
	        
		if msg["MsgType"] == "event":
			response = self.process_event(msg["Event"], msg)
		elif msg["MsgType"] == "text":
			response = yield self.text(msg['Content'].strip(), msg)
		elif msg["MsgType"] == "image":
			response = self.image(msg, 'image')
		else:
			response = None
		
		try:
			#wx_id = msg['FromUserName']
			#content = msg['Content'].strip()
			#response = yield self.send_message(wx_id,content,'xx')
			logging.info("post_response %s", response)
			# result = self.send_message(msg['FromUserName'], msg)
			# logging.info(result)
			self.finish(response) 
		except Exception,e:
			logging.error(e)
			self.finish("")
			
			

	@tornado.gen.coroutine
	def send_message(self, wx_id, msg, action, async=False, callback=None):
		logging.info("wx_handler_send_message=%s",msg)
		result = None
		if async:
			PiSocketHandler.send_message(wx_id, msg)
			raise tornado.gen.Return("receive success")

		try:
			client = PiSocketHandler.get_client(wx_id) 
			if client is None:
				logging.info("client is None")				
				raise tornado.gen.Return("no client connected")
			client.my_write_message(msg)
			logging.info("client %s", client)
			logging.info("before read message .............")
			client_res = yield tornado.gen.Task(client.read_message)
			logging.info("xxx%s",client_res)
			logging.info("xxx%s",client_res.result())

			if client_res.exception() is not None:
				logging.error("client_error %s", str(client_res.exception()))
				result = 'fail, try again'
			else:
				jsonstr = client_res.result()
				pi_id = cache.get('wx:' + wx_id)
				logging.info(jsonstr)
				result = self.parse_json(wx_id, pi_id, jsonstr)
		except:
			logging.debug("error occuar ", exc_info=True)
		raise tornado.gen.Return(result)
		

	def roll(self, content):
		temp = content.split(' ')
		if content == 'roll':
			content = str(random.randint(1, 100))
		elif len(temp) == 2:
			if temp[1].isdigit() and int(temp[1]) > 0:
				content = str(random.randint(1, int(temp[1])))
		elif len(temp) == 3:
			if temp[1].isdigit() and int(temp[1]) > 0 and temp[2].isdigit() and temp[1] <= temp[2]:
				content = str(random.randint(int(temp[1]), int(temp[2])))
		return content

	def process_event(self, event, msg):
		if msg["Event"] == "subscribe":
			# self.bind()
			help = self.help()
			return textTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), 'text', "欢迎关注！\n" + help)
		else:
			# self.unbind()
			response = None

	@tornado.gen.coroutine
	def text(self, content, msg):
		logging.info("enter text process content=%s msg=%s",content,msg)

		if content == 'list':
			content = self.pi_id_list()

		elif content =='airlist':
			content = yield self.airlist(msg, content)

		elif content.startswith('airbind'):
			content = yield self.airbind(msg, content)

		elif content == 'env':
			content = yield self.env(msg, content)
			logging.info("after env inoke...")

		elif content == 'photo':
			url = yield self.send_message(msg['FromUserName'], content, 'photo_reply', False, msg['MsgId'])
			content = pictextTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), 'photo', 'this is a photo', url, url)
			raise tornado.gen.Return(content)

		elif content == 'video':
			wx_id = msg['FromUserName']
			pi_id = cache.get('wx:' + wx_id)
			if pi_id is None:
				content = "设备未连接"
			else:
				content = "监控地址(请点击) http://www.go123.us/monitor/stream-example.html?id=" + str(pi_id); 
		elif content.startswith('roll'):
			content = self.roll(content)

		elif content == 'open':
			content = self.open(msg, content)

		elif content == 'close':
			content = self.close(msg, content)

		elif content == 'help':
			content = self.help()

		elif content == 'unbind':
			content = self.unbind(msg['FromUserName'])

		elif content.startswith('bind'):
			pi_id = content[4:]
			logging.info('pi_id:' + pi_id)
			content = self.bind(msg['FromUserName'], pi_id)

		logging.info("content = %s", content)
		# result = self.send_message(msg['FromUserName'], msg)
		# logging.info(result)
		# content = content
		response = textTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), 'text', content)
		logging.info("ending process_text ...%s", response)
		raise tornado.gen.Return(response)

	def image(self, msg, content):
		self.send_message(msg['FromUserName'], msg['PicUrl'], content + '_reply', False, msg['MsgId'])
		return pictextTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), '自动回复', 'pic', msg['PicUrl'], msg['PicUrl'])

	@tornado.gen.coroutine
	def airlist(self, msg, content):
		result = yield self.send_message(msg['FromUserName'], content, content + '_reply', False, msg['MsgId'])
		raise tornado.gen.Return(result)

	@tornado.gen.coroutine
	def airbind(self, msg, content):
		try:
			index = int(content[7:])
			wx_id = msg['FromUserName']
			pi_id = cache.get('wx:' + wx_id)
			term = cache.lindex('pi:' + pi_id + ':airlist', index - 1)
			if not term:
				result = 'term:' + str(index) + ' is not exist'
			else:
				result = yield self.send_message(msg['FromUserName'], 'airbind:' + term, 'airbind_reply', False, msg['MsgId'])
		except:
			logging.error('index is not int', exc_info=True)
			result = "please input int"
		logging.info('airbind:result:' + result)
		raise tornado.gen.Return(result)

	@tornado.gen.coroutine
	def env(self, msg, content):
		logging.info("enter env process ...")
		result = yield self.send_message(msg['FromUserName'], content, content + '_reply', False, msg['MsgId'])
		logging.info("after env process reading ...")
		raise tornado.gen.Return(result)

	def help(self):
		return """list获取设备ID列表
bind+设备ID 绑定设备
(eg. bind123)
unbind 设备解绑
open 开灯
close 关灯
photo 远程照片
video 返回视频监控地址
airlist 设备可连接终端列表
airbind+终端编号
(eg. airbind1)
env 环境数据
直接发送照片"""

	@tornado.gen.coroutine
	def video(self, msg, content):
		result = yield self.send_message(msg['FromUserName'], content, content + '_reply', False, msg['MsgId'])
		raise tornado.gen.Return(result)

	def open(self, msg, content):
		self.send_message(msg['FromUserName'], content, content + '_reply', True)
		return 'open complete'

	def close(self, msg, content):
		self.send_message(msg['FromUserName'], content, content + '_reply', True)
		return 'close complete'

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

	def parse_json(self, wx_id, pi_id, msg):
		jsonmsg = json.loads(msg)
		if jsonmsg['status']:
			if 'photo_reply' == jsonmsg['action']:
				return jsonmsg['data'][0]['big_url']

			elif 'open_reply' == jsonmsg['action']:
				return jsonmsg['data']

			elif 'close_reply' == jsonmsg['action']:
				return jsonmsg['data']

			elif 'env_reply' == jsonmsg['action']:
				temperature = jsonmsg['data'][0]['temperature']
				humidity = jsonmsg['data'][0]['humidity']
				content = '温度：' + str(temperature) + '°C\n' + '湿度：' + str(humidity) + '%'
				return content

			elif 'airlist_reply' == jsonmsg['action']:
				cache.delete('pi:' + pi_id + ':airlist')
				airlist = ''
				list_index = 0
				for data in jsonmsg['data']:
					list_index = list_index + 1
					one = str(list_index) + '.:' + data['servicename'] + '_' + data['ip'] + ':' + str(data['port'])
					airlist = airlist + one + '\n'
					cache.rpush('pi:' + pi_id + ':airlist', json.dumps(data))
				return airlist

			elif 'airbind_reply' == jsonmsg['action']:
				return jsonmsg['data']

			elif 'image_reply' == jsonmsg['action']:
				return jsonmsg['data']

		else:
			return 'failed'
			
			

	def bind(self, wxid, piid):
		
		success,msg = PiSocketHandler.bind_wx(wxid, piid)
		if success:
			msg = 'bind ok' + msg
		else:
			msg = 'bind fail' + msg
		return msg

	def unbind(self, wxid):
		success,msg = PiSocketHandler.unbind_wx(wxid)
		if success:
			msg = 'unbind ok' + msg
		else:
			msg = 'unbind fail' + msg
		return msg

	def pi_id_list(self):
		msg = 'list is null'
		pi_list = cache.smembers('pi_list')
		if pi_list:
			msg = ''
			for pi in pi_list:
				if pi:
					msg = msg + pi + '\n'
		return msg


class PiSocketHandler(tornado.websocket.WebSocketHandler):
	pi_clients = dict()
	clients_pi = dict()
	pi_wx_dict = dict()
	wx_pi_dict = dict()
	#cache = []
	#cache_size = 200

	def __init__(self, application, request, **kwargs):
		self.read_future = None
		self.read_queue = collections.deque()
		self.ioloop = tornado.ioloop.IOLoop.instance()
		tornado.websocket.WebSocketHandler.__init__(self, application, request,**kwargs)

	def allow_draft76(self):
		# for iOS 5.0 Safari
		return True
	
	def open(self):
		pi_id = self.get_argument("pi_id",None)
		logging.info("open client pi_id %s", pi_id)
		if not pi_id:
			logging.error("Error no pi_id header set")
			return 
		PiSocketHandler.pi_clients[pi_id] = self
		PiSocketHandler.clients_pi[self] = pi_id
		cache.sadd('pi_list', pi_id)
		self.write_message("welcome")

	def on_close(self):
		pi_id = self.get_argument("pi_id",None)
		logging.info("close client pi_id %s", pi_id)
		if not pi_id:
			logging.error("Error no pi_id header set")
			return 
		del PiSocketHandler.pi_clients[pi_id]
		# del PiSocketHandler.pi_wx_dict[pi_id]
		# cache.delete('pi:' + pi_id)
		cache.srem('pi_list', pi_id)

	@classmethod
	def bind_wx(cls, wx_id, pi_id):
		if (not wx_id) or (not pi_id):
			logging.error("Error bind pi client! wx_id=%s, pi_id=%s", wx_id, pi_id)
			return False, '参数不全'
		elif not PiSocketHandler.pi_clients.get(pi_id):
			logging.error("Error bind pi client not connected! wx_id=%s, pi_id=%s", wx_id, pi_id)
			return False, '设备' + pi_id + '未连接或不存在'

		
		# if cls.pi_wx_dict.get(pi_id):
		elif cache.get('pi:' + pi_id):
			logging.error("bind pi_id repeat! wx_id=%s, pi_id=%s", wx_id, pi_id)
			return False, '设备' + pi_id + '已被绑定'
		# if cls.wx_pi_dict.get(wx_id):
		elif cache.get('wx:' + wx_id):
			old_pi_id = cache.get('wx:' + wx_id)
			cache.delete('pi:' + old_pi_id)
			logging.info("bind wx_id repeat! wx_id=%s, pi_id=%s", wx_id, pi_id)
			msg = '微信重新绑定' + pi_id
		else:
			msg = '绑定成功'
		# cls.wx_pi_dict[wx_id] = pi_id
		# cls.pi_wx_dict[pi_id] = wx_id
		cache.set('wx:' + wx_id, pi_id)
		cache.set('pi:' + pi_id, wx_id)

		return True, msg

	@classmethod
	def unbind_wx(cls, wx_id):
		if not wx_id:
			logging.error("Error unbind pi client! wx_id=%s", wx_id)
			return False, '参数不全'

		elif not cache.get('wx:' + wx_id):
			logging.error("Error unbind pi client not binded! wx_id=%s", wx_id)
			return False, '微信' + wx_id + '未绑定'

		elif cache.get('wx:' + wx_id):
			msg = '解绑成功'
			pi_id = cache.get('wx:' + wx_id)
			cache.delete('wx:' + wx_id)
			cache.delete('pi:' + pi_id)

			return True, msg
		

#    @classmethod
#    def update_cache(cls, chat):
#        cls.cache.append(chat)
#        if len(cls.cache) > cls.cache_size:
#            cls.cache = cls.cache[-cls.cache_size:]

	@classmethod
	def send_message(cls, wx_id, message):
		logging.info("sending message to wx_id=%s, message=%s", wx_id, message)
		
		pi_id = cache.get("wx:" + wx_id)
		client = cls.pi_clients.get(pi_id)
		if not cache.get("wx:" + wx_id) or not client:
			logging.error("Error pi client not connect")
			return

		try:
			client.write_message(message)
		except Exception,e:
			logging.error("Error sending message %s",str(e))
	
	@classmethod
	def get_client(cls, wx_id):
		logging.info("get_client wx_id=%s", wx_id)
		pi_id = cache.get("wx:" + wx_id)
		client = cls.pi_clients.get(pi_id)
		return client

	def my_write_message(self, message):
		logging.info("my_send_message %s", message)
		try:
			self.write_message(message)
		except Exception,e:
			logging.error("Error sending message %s",str(e))

	def read_message(self, callback=None):
		logging.info("my_read_message_from_client waitting.....")

		#assert self.read_future is None
		future = TracebackFuture()
		#if self.read_queue:
		#	future.set_result(self.read_queue.popleft())
		#else:
		self.read_future = future

		logging.info("222222my_read_message_from_client waitting.....")
		if callback is not None:
			logging.info("add_callbak on read_message")
			self.ioloop.add_future(future, callback)
		logging.info("333333my_read_message_from_client waitting.....")
		return future

	def on_message(self, message):
		pi_id = self.get_argument("pi_id",None)
		logging.info("on_message client pi_id=%s,message=%s", pi_id, message)
		if "hi" == message:
			return
		if self.read_future is not None:
			self.read_future.set_result(message)
			self.read_future = None
		#else:
			#self.read_queue.append(message)

class WeiXinBindHandler(tornado.web.RequestHandler):
    def get(self):
		wx_id = "185980656"
		pi_id = "113696732"
		PiSocketHandler.bind_wx(wx_id, pi_id)
		PiSocketHandler.send_message(wx_id, "hello")
		self.write("bind ok")

class WeiXinHandler(tornado.web.RequestHandler):
    def get(self):
		wx_id = "185980656"
		pi_id = "113696732"
		PiSocketHandler.send_message(wx_id, "hello")
		self.write("send message ok")


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.autoreload.start(io_loop=None, check_time=500)
    logging.info("start app....")
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
