import threading as t
import socket as s

"""
==================
| SCRITTO A MANO |
==================
"""

class SocketServer:
    def __init__(self, address, port, timeout=1):
        self.connection_threads = list()
        self.connections = list()
        self.on_connect = None
        self.on_receive = None
        self.socket = s.socket(s.AF_INET)
        self.socket.bind((address, port))
        self.socket.listen()
        self.timeout = timeout
        self.socket.settimeout(timeout)

        self.kill = 0

    def handle_receiving(self, conn, addr):
        while 1:
            try:
                data = conn.recv(4096)
                if self.on_receive:
                    self.on_receive(conn=conn, data=data, addr=addr)
            except s.timeout:
                if self.kill:
                    return

    def handle_connections(self):
        while 1:
            try:
                c, a = self.socket.accept()
                self.connections.append((c, a))
                if self.on_connect:
                    self.on_connect(conn=c, addr=a)
                c.settimeout(self.timeout)
                thread = t.Thread(target=self.handle_receiving, args=[c, a], daemon=True)
                thread.start()
                self.connection_threads.append(
                    thread
                )
            except s.timeout:
                if self.kill:
                    return
    
    def loop_forever(self):
        thread = t.Thread(target=self.handle_connections, daemon=True)
        thread.start()
        return thread

class SocketClient():
    def __init__(self, addr, port, timeout=1):
        self.timeout = timeout
        self.addr = addr
        self.port = port
        self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((addr, port))
        self.on_receive = None
        self.thread = t.Thread(target=self.handle_receiving, daemon=True)
        self.thread.start()

    def send(self, data: bytes):
        self.socket.sendall(data)

    def handle_receiving(self):
        while 1:
            try:
                data = self.socket.recv(4096)
                if self.on_receive:
                    self.on_receive(conn=self.socket, data=data)
            except s.timeout:
                ...

def main():
    def echo(conn, data, addr):
        conn.send(b"Echoing: " + data)

    def greet(conn, addr):
        conn.send(b"Thanks for connecting\n")

    sh = SocketServer("127.0.0.1", 7878)
    sh.on_connect = greet
    sh.on_receive = echo
    sh.loop_forever()

    while 1:
        ...

if __name__ == "__main__":
    main()
