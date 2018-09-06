import time
import socket

s = socket.socket()
s.connect(('127.0.0.1', 6100))

with open('out3.txt', 'rb') as f:
    for line in f:
        time.sleep(0.05)
        s.send(line)
        print(line)

s.close()
