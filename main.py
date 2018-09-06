from tornado.ioloop import IOLoop
from tornado import gen
from tornado.websocket import WebSocketHandler
import tornado.httpserver
import tornado.web
from tornado.options import options, define
import socket
import json
import os
import re
import queue
import time

define("host", default="localhost", help="app host", type=str)
define("port", default=3000, help="app port", type=int)

q = queue.Queue()

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

connections = set() #set of websocket "clients"

pattern_data = re.compile(b'\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\.\:\| ]*')
pattern_res = re.compile('\d\d?:\d\d\.\d\d\d|\d\d?\.\d\d\d')
key = 'default'

s = socket.socket()
s.bind(('', 6100))
print('binded')
s.listen(1)
print('listened')

def getData():
    conn, addr = s.accept()
    print('accepted')

    while True:
        data = conn.recv(1024)
        if not data:
            break
        for match in pattern_data.finditer(data):
            p_data = match.group().decode()
            res_match = pattern_res.search(p_data)
            if res_match:
                res = res_match.group().replace('.', ',')
                ab, cd, ee, pulse, bib, *xx = p_data.split('|')
                if bib.strip() == '0':
                    pulse = 0
                    key = '{}-{}-{}-{}'.format(res, ab, cd, ee)
                    res = 'start'
                results = {'key': key, 'res': res, 'bib': bib, 'pulse': pulse}
                m_dict = { 'action': 'result', 'result': results }
                q.put(m_dict)
                print("Thread 1: pull data from socket: {} - {}".format(pulse, res))

    getData()

#@gen.coroutine
def sendToAll():
    while True:
        if len(connections) > 0:
            while not q.empty():
                m_dict = q.get()
                msg = json.dumps(m_dict)
                [(con.write_message(msg), print("Thread 2: push to web: {}".format(con))) for con in connections]
        #yield gen.sleep(0.01)  #this prevent blocking and allow other client to connect
        time.sleep(0.01)


class WebSocketHandler(WebSocketHandler):

    # accept all cross-origin traffic
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in connections:
            connections.add(self)

    def on_message(self, message):
        pass #not used

    def on_close(self):
        connections.remove(self)
 

class IndexPageHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("index.html",
            server_url=options.host,
            server_port=options.port
        )
       
 
class Application(tornado.web.Application):

    def __init__(self):
        settings = {
            'template_path': 'templates',
            "static_path": os.path.join(BASE_DIR, 'static'),
        }

        handlers = [
            (r'/', IndexPageHandler),
            (r'/socket', WebSocketHandler),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': settings['static_path']}),
        ]
        tornado.web.Application.__init__(self, handlers, **settings)
 
 
if __name__ == '__main__':
    options.parse_command_line()
    ws_app = Application()
    server = tornado.httpserver.HTTPServer(ws_app)
    server.listen(options.port)
    #IOLoop.current().spawn_callback(getData)

    from threading import Thread
    workers = [
        Thread(target=getData),
        Thread(target=sendToAll),
    ]
    for w in workers:
        w.daemon = True
        w.start()
    IOLoop.instance().start()
