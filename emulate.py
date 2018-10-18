import time
import socket
import sys

s = socket.socket()
s.connect(('', 6100))

with open('out6.txt', 'rb') as f:
    for line in f:
        time.sleep(0.09)
        s.send(line)
        print(line.decode())

s.close()
