import time
import socket
import sys
import os

s = socket.socket()
s.connect(('', 7777))

dir_name = sys.argv[1]
files = os.listdir(dir_name)

for name in files:
    with open(dir_name + '/' + name, 'rb') as f:
        for line in f:
            time.sleep(0.1)
            s.send(line)
            print(line.decode())

s.close()
