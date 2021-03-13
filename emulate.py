import time
import socket
import sys

s = socket.socket()
s.connect(('', 6100))

for f_str in ('out.txt', 'out2.txt'):
    with open(f_str, 'rb') as f:
        for line in f:
            time.sleep(0.03)
            s.send(line)
            print(line.decode())

s.close()
