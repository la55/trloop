import socket 
import time

s = socket.socket()
s.bind(('', 7777))     
s.listen(1) 
print('Listen...')


def create_socket():
    print('Wait for accept...')
    conn, addr = s.accept()
    print('Accepted')
    while True:
        data = conn.recv(1024)
        print(data)
        if not data:
            break
    print('Disconnected...')
    create_socket()

create_socket()

