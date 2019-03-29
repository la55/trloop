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
import sqlite3


define("host", default="localhost", help="app host", type=str)
define("port", default=8080, help="app port", type=int)

dbconn = sqlite3.connect('db.sqlite3')
cursor = dbconn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS results (key INTEGER, result TEXT, bib INTEGER, pulse INTEGER)''')
dbconn.commit()

q = queue.Queue()
q_res = queue.Queue()

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

connections = set() #set of websocket "clients"

pattern_data = re.compile(b'\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\.\:\| ]*')
pattern_res = re.compile('\d\d?:\d\d\.\d\d\d|\d\d?\.\d\d\d')
tmpst = 'default'

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
            print(p_data)
            res_match = pattern_res.search(p_data)
            if res_match:
                res = res_match.group().replace('.', ',')
                ab, cd, ee, pulse, bib, *xx = p_data.split('|')
                if len(xx) < 2:
                    ab, cd, ee, bib1, bib2, xx = p_data.split('|')
                    tmpst = time.time()
                    key1 = '{}-{}'.format(tmpst, bib1)
                    key2 = '{}-{}'.format(tmpst, bib2)
                    result1 = {'key': key1, 'res': 'A', 'bib': bib1, 'pulse': pulse}
                    result2 = {'key': key2, 'res': 'B', 'bib': bib2, 'pulse': pulse}
                    for result in [result1, result2]:
                        m_dict = { 'action': 'result', 'result': result }
                        q.put(m_dict)
                    continue
                key = '{}-{}'.format(tmpst, bib)
                result = {'key': key, 'res': res, 'bib': bib, 'pulse': pulse}
                m_dict = { 'action': 'result', 'result': result }
                q.put(m_dict)
                res_db = {'key': tmpst, 'res': res, 'bib': bib, 'pulse': pulse}
                res_dict = { 'action': 'result', 'result': res_db }
                q_res.put(res_dict)
                print("Thread 1: pull data from socket: {} - {}".format(pulse, res))

    getData()


def saveRes():
    dbconn = sqlite3.connect('db.sqlite3')
    cursor = dbconn.cursor()
    while True:
        while not q.empty():
            res = q_res.get()
            if res['action'] == 'result':
                key, res, bib, pulse = res['result'].values()
                print('Values: ', key, res, bib, pulse)
                sql = '''INSERT INTO results VALUES ({}, '{}', {}, {}) '''.format(key, res, bib, pulse)
                cursor.execute(sql)
                dbconn.commit()


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
        data = json.loads(message)
        print(data)
        if data['action'] == 'find_bib':
            try:
                bib = int(data['bib'])
            except:
                bib = 0
            sql = '''SELECT * FROM results WHERE bib={} ORDER BY key, pulse'''.format(bib)
            cursor.execute(sql)
            rows = cursor.fetchall()
            results = [{ 'pulse': row[3], 'res': row[1] } for row in rows]
            msg = json.dumps({'action': 'find_bib', 'results': results })
            [(con.write_message(msg), print("Find bib results: {}".format(bib))) for con in connections]
        if data['action'] == 'edit_bib':
            bib = data['bib']
            key = data['key'].split('-')[0]
            sql = '''UPDATE results SET bib={} WHERE key={}'''.format(bib, key)
            cursor.execute(sql)
            dbconn.commit()
            msg = json.dumps({'action': 'edit_bib', 'bib': bib, 'key': key })
            [(con.write_message(msg), print("Bib updated: {}".format(bib))) for con in connections]

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
        Thread(target=saveRes),
    ]
    for w in workers:
        w.daemon = True
        w.start()
    IOLoop.current().start()
