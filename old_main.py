from tornado.ioloop import IOLoop
from tornado import gen
from tornado.websocket import WebSocketHandler
import tornado.httpserver
import tornado.web
import socket
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

connections = set() #set of websocket "clients"


def time_to_int(res):
    try:
        res_time, micro = res.split(',')
    except:
        return 0
    try:
        mins, secs = res_time.split(':')
    except:
        return int(res_time) * 1000 + int(micro)
    return int(mins) * 60000 + int(secs) * 1000 + int(micro)


def int_to_time(res_to_int):
    m = res_to_int / 60000
    secs = res_to_int % 60000
    s = secs / 1000
    h = secs % 1000
    if int(m) == 0:
        return '%d,%0.3d' % (s, h)
    else:
        return '%d:%0.2d,%0.3d' % (m, s, h)


def get_lap_time(prev_res,res):
    int_prev_res = time_to_int(prev_res)
    int_res = time_to_int(res)
    return int_to_time(int_res - int_prev_res)


@gen.coroutine
def getData():
    # In real world data comes from socket
    #
    s = socket.socket()
    s.bind(('', 6100))
    print('binded')
    s.listen(1)
    print('listened')
    conn, addr = s.accept()
    print('accepted')

    prev_res = 0 
    prev_2_res = 0 
    prev_4_res = 0 
    prev_8_res = 0 
    while True:
        yield gen.sleep(0.0001)  #this prevent blocking and allow other client to connect
        data = conn.recv(1024)
        if not data:
            break
        l_data = data.decode().split('|')

        if len(l_data) > 5:
            bib = l_data[4].strip()
            pulse = int(l_data[3].strip())
            try:
                res = '{}{}'.format(l_data[5].strip(), l_data[6].strip())
            except:
                res = l_data[5].strip()
            res = res.replace('\x04', '').replace('.', ',')
            if int(bib) == 0:
                bib = pulse
                res = 'start'
                pulse = 0

            if pulse == 0:
                prev_res = 0 
                prev_2_res = 0 
                prev_4_res = 0 
                prev_8_res = 0 
            lap = get_lap_time(prev_res, res)
            prev_res = res
            if divmod(pulse, 2)[1] == 0:
                lap2 = get_lap_time(prev_2_res, res)
                prev_2_res = res
            if divmod(pulse, 4)[1] == 0:
                lap4 = get_lap_time(prev_4_res, res)
                prev_4_res = res
            if divmod(pulse, 8)[1] == 0:
                lap8 = get_lap_time(prev_8_res, res)
                prev_8_res = res
            results = {'res': res, 'bib': bib, 'pulse': pulse, 'lap': lap, 'lap2': lap2, 'lap4': lap4, 'lap8': lap8}
            m_dict = { 'action': 'result', 'result': results }
            msg = json.dumps(m_dict)
            [con.write_message(msg) for con in connections]



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
    IOLoop.current().spawn_callback(getData)
    IOLoop.instance().start()
