# coding=utf-8
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

	def post(self):
		msg = self.parse_msg()
		response = None
		logging.info( msg)
		#设置返回数据模板	
		#纯文本格式
		


		#判断Message类型，如果等于"Event"，表明是一个新关注用户
		if msg["MsgType"] == "event":
			response = self.event(msg["Event"], msg)
			

		elif msg["MsgType"] == "text":
			response = self.text(msg['Content'].strip(), msg)

		elif msg["MsgType"] == "image":
			response = self.image(msg)

		logging.info(response)
		# result = self.send_message(msg['FromUserName'], msg)
		# logging.info(result)
		self.finish(response) 

	def send_message(self, wx_id, msg):
		PiSocketHandler.send_message(wx_id, msg)
		pi_id = cache.get('wx:' + wx_id)
		if pi_id:
			for i in range(0, 10):
				logging.info(i)
				msg = cache.get('pi_msg:' + pi_id)
				if msg:
					cache.delete('pi_msg:' + pi_id)
					msg = self.parse_json(wx_id, pi_id, msg)
					logging.info('msg:')
					logging.info(msg)
					return msg
				else:
					time.sleep(0.5)
			return 'fetch fail'
		return 'no msg'


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

	def event(self, event, msg):
		if msg["Event"] == "subscribe":
			# self.bind()
			help = self.help()
			return textTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), 'text', "欢迎关注！\n" + help)
		else:
			# self.unbind()
			response = None

	def text(self, content, msg):

		if content == 'list':
			content = self.pi_id_list()

		elif content =='airlist':
			content = self.airlist(msg, content)

		elif content.startswith('airbind'):
			content = self.airbind(msg, content)

		elif content == 'env':
			content = self.env(msg, content)

		elif content == 'photo':
			url = self.send_message(msg['FromUserName'], content)
			return pictextTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), 'photo', 'this is a photo', url, url)

		elif content.startswith('roll'):
			content = self.roll(content)

		elif content == 'open':
			content = self.open(msg)

		elif content == 'close':
			content = self.close(msg)

		elif content == 'help':
			content = self.help()

		elif content == 'unbind':
			content = self.unbind(msg['FromUserName'])

		elif content.startswith('bind'):
			pi_id = content[4:]
			logging.info('pi_id:' + pi_id)
			content = self.bind(msg['FromUserName'], pi_id)

		logging.info("content:" + content)
		# result = self.send_message(msg['FromUserName'], msg)
		# logging.info(result)
		# content = content
		response = textTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), 'text', content)
		return response

	def image(self, msg):
		self.send_message(msg['FromUserName'], msg['PicUrl'])
		return pictextTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())), '自动回复', 'pic', msg['PicUrl'], msg['PicUrl'])

	def airlist(self, msg, content):
		return self.send_message(msg['FromUserName'], content)

	def airbind(self, msg, content):
		try:
			index = int(content[7:])
			wx_id = msg['FromUserName']
			pi_id = cache.get('wx:' + wx_id)
			term = cache.lindex('pi:' + pi_id + ':airlist', index - 1)
			if not term:
				result = 'term:' + str(index) + ' is not exist'
			else:
				result = self.send_message(msg['FromUserName'], 'airbind:' + term)
		except:
			logging.error('index is not int', exc_info=True)
			result = "please input int"
		logging.info('airbind:result:' + result)
		return result
		

	def env(self, msg, content):
		return self.send_message(msg['FromUserName'], content)

	def help(self):
		return 'list获取设备ID列表\nbind+设备ID绑定设备\nunbind\nopen\nphoto\nroll\nairlist\nenv'

	def open(self, msg):
		return self.send_message(msg['FromUserName'], 'open')

	def close(self, msg):
		return self.send_message(msg['FromUserName'], 'close')

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
				content = '温度：' + str(temperature) + '\n' + '湿度：' + str(humidity) + '%'
				return 

			elif 'airlist_reply' == jsonmsg['action']:
				cache.delete('pi:' + pi_id + ':airlist')
				airlist = ''
				for data in jsonmsg['data']:
					one = str(data['index']) + ':' + data['servicename'] + ':' + data['ip'] + ':' + str(data['port'])
					airlist = airlist + one + '\n'
					cache.rpush('pi:' + pi_id + ':airlist',data)
				return airlist

			elif 'airbind_reply' == jsonmsg['action']:
				return jsonmsg['data']

			elif 'image_reply' == jsonmsg['action']:
				return jsonmsg['data']

			elif 'photo_reply' == jsonmsg['action']:
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
		except:
			logging.error("Error sending message", exc_info=True)

	def on_message(self, message):
		pi_id = self.get_argument("pi_id",None)
		logging.info("got message client pi_id=%s,message=%s", pi_id, message)

		if not pi_id:
			logging.error("Error no pi_id header set")
			return 
		
		elif message == 'hi':
			self.write_message('welcome')
			return

		elif not PiSocketHandler.pi_clients.get(pi_id):
			logging.error("on_message client not regiester")
			return 

		elif not cache.get('pi:' + pi_id):
			logging.error("on_message not bind wx")
			return

		else:
			logging.info('msg:' + message)
			# if message == 'success' or message == 'failed' or message.startswith('http'):
			try:
				jsonmsg = json.loads(message)
				cache.setex("pi_msg:" + pi_id, 15, message)
				return
			except:
				logging.error('message is not json', exc_info=True)
		
        #parsed = tornado.escape.json_decode(message)
        #chat = {
        #    "id": str(uuid.uuid4()),
        #    "body": parsed["body"],
        #    }
        #chat["html"] = tornado.escape.to_basestring(
        #    self.render_string("message.html", message=chat))

        #PiSocketHandler.update_cache(chat)
        #PiSocketHandler.send_updates(chat)

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
