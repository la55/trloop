from tornado.ioloop import IOLoop
from tornado import gen
from tornado.websocket import WebSocketHandler
import tornado.httpserver
import tornado.web
import socket
import json
import os
import re
import queue
import time

q = queue.Queue()

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

connections = set() #set of websocket "clients"

s = socket.socket()
s.bind(('', 6100))
print('binded')
s.listen(1)
print('listened')

#@gen.coroutine
def getData(q):
    conn, addr = s.accept()
    print('accepted')

    pattern_data = '\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\.\:\| ]*'
    pattern_res = '\d\d?:\d\d\.\d\d\d|\d\d?\.\d\d\d' 
    key = 'default'
    while True:
        #yield gen.sleep(0.000001)  #this prevent blocking and allow other client to connect
        data = conn.recv(1024)
        if not data:
            break
        try:
            to_print = re.findall(pattern_res, data.decode())
            if len(to_print) > 0:
                print(data)
            data = re.findall(pattern_data, data.decode())
        except:
            data = []
        for p_data in data:
            try:
                res = re.findall(pattern_res, p_data)[0]
                res = res.replace('.', ',')
            except:
                res = 'nothing'
            if res:
                l_data = p_data.split('|')
                ab = l_data[0].strip()
                cd = l_data[1].strip()
                ee = l_data[2].strip()
                bib = l_data[4].strip()
                pulse = l_data[3].strip()
                if bib == '0':
                    pulse = 0
                    key = '{}-{}-{}-{}'.format(res, ab, cd, ee)
                    res = 'start'
                results = {'key': key, 'res': res, 'bib': bib, 'pulse': pulse}
                m_dict = { 'action': 'result', 'result': results }
                q.put(m_dict)

    getData(q)

def sendToAll(q):
    while True:
        while not q.empty():
            m_dict = q.get()
            msg = json.dumps(m_dict)
            print(connections)
            print(msg)
            [con.write_message(msg) for con in connections]
        time.sleep(0.5)

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
        self.render("index.html")
       
 
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
    ws_app = Application()
    server = tornado.httpserver.HTTPServer(ws_app)
    server.listen(8080)
    #IOLoop.current().spawn_callback(getData)

    from threading import Thread
    workers = [
        Thread(target=getData, args=(q,)),
        Thread(target=sendToAll, args=(q,)),
    ]
    for w in workers:
        w.daemon = True
        w.start()
    IOLoop.current().start()
