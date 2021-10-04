import time
import socket
import sys

s = socket.socket()
s.connect(('', 7777))

for f_str in ('out.txt', 'out6.txt'):
    with open(f_str, 'rb') as f:
        for line in f:
            time.sleep(0.01)
            s.send(line)
            print(line.decode())

s.close()
