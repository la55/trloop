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
from res_mod import Race, Start, Result



define("host", default="localhost", help="app host", type=str)
define("port", default=8080, help="app port", type=int)

dbconn = sqlite3.connect('db.sqlite3')
cursor = dbconn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS results (race TEXT, key TEXT, result TEXT, bib INTEGER, pulse INTEGER)''')
dbconn.commit()

q = queue.Queue()
q_res = queue.Queue()

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

connections = set() #set of websocket "clients"

pattern_data = re.compile(b'\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\. ]*\|[0-9\.\:\| ]*')
pattern_res = re.compile('\d\d?:\d\d\.\d\d\d|\d\d?\.\d\d\d')


s = socket.socket()
s.bind(('', 6100))
print('binded')
s.listen(1)
print('listened')
race = Race()
current_race = 'Backend Test'

def getData():
    conn, addr = s.accept()
    print('accepted')

    while True:
        data = conn.recv(1024)
        if not data:
            break
        for match in pattern_data.finditer(data):
            p_data = match.group().decode()
            if race.is_result(p_data):
                res = race.res_from_data(p_data)
                m_dict = { 'action': 'result', 'race': current_race, 'result': res._asdict() }
                q_res.put(res)
            else:
                st = race.start_from_data(p_data)
                m_dict = { 'action': 'start', 'start': st._asdict() }
            q.put(m_dict)

    getData()


def saveRes():
    dbconn = sqlite3.connect('db.sqlite3')
    cursor = dbconn.cursor()
    while True:
        while not q_res.empty():
            res = q_res.get()
            sql = '''INSERT INTO results VALUES ('{}', '{}', '{}', {}, {})
             '''.format(current_race, res.key, res.res, res.bib, res.pulse)
            print(sql)
            cursor.execute(sql)
            dbconn.commit()
        time.sleep(0.01)


def sendToAll():
    while True:
        if len(connections) > 0:
            while not q.empty():
                m_dict = q.get()
                msg = json.dumps(m_dict)
                print("Thread 2: push to web: ", msg)
                [con.write_message(msg) for con in connections]
        time.sleep(0.01)


class WebSocketHandler(WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        if self not in connections:
            connections.add(self)
        sql = '''SELECT DISTINCT race FROM results'''
        cursor.execute(sql)
        rows = cursor.fetchall()
        races = [row[0] for row in rows]
        msg = json.dumps({'action': 'open', 'races': races })
        [con.write_message(msg) for con in connections]

    def on_message(self, message):
        data = json.loads(message)
        print(data)
        if data['action'] == 'load_current':
            race = data['race']
            sql = '''SELECT * FROM results WHERE race='{}' ORDER BY key, pulse'''.format(race)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                race, key, time, bib, pulse = row
                if pulse == 1:
                    st = Start(key, '', bib, '', time)
                    m_dict = { 'action': 'start', 'start': st._asdict() }
                    q.put(m_dict)
                res = Result(key, 'A', bib, pulse, time)
                m_dict = { 'action': 'result', 'race': current_race, 'result': res._asdict() }
                q.put(m_dict)
        if data['action'] == 'change_current':
            global current_race
            current_race = data['current_race']
        if data['action'] == 'find_bib':
            try:
                bib = int(data['bib'])
            except:
                bib = 0
            race = data['race']
            sql = '''SELECT * FROM results WHERE bib={} AND race='{}' ORDER BY key, pulse'''.format(bib, race)
            cursor.execute(sql)
            rows = cursor.fetchall()
            results = [{ 'race': row[0], 'pulse': row[4], 'res': row[2] } for row in rows]
            msg = json.dumps({'action': 'find_bib', 'results': results })
            [con.write_message(msg) for con in connections]
        if data['action'] == 'edit_bib':
            bib = data['bib']
            key = data['key']
            sql = '''UPDATE results SET bib={} WHERE key="{}"'''.format(bib, key)
            row_count = cursor.execute(sql)
            dbconn.commit()
            msg = json.dumps({'action': 'edit_bib', 'bib': bib, 'key': key })
            [con.write_message(msg) for con in connections]

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
