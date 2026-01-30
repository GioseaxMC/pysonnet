import pysonnet as son
from server import SocketServer, SocketClient
from sys import argv
from random import randint

sharedObjects = son.SharedObjects()
PORT = int(argv[2])
if "server" in argv:
    sh = SocketServer("127.0.0.1", PORT)
    sh.on_connect = lambda conn, addr: print("Sigma balls")
    def rotate_message(data, addr, conn):
        for c, a in sh.connections:
            if conn != c:
                c.send(data)
    sh.on_receive = rotate_message
    sh.loop_forever()

sc = SocketClient("127.0.0.1", PORT)
def on_recv(conn, data):
    sharedObjects.on_receive_callback(data)
sc.on_receive = on_recv
sharedObjects.send = lambda payload: sc.send(payload)

class Square:
    def __init__(self):
        self.mine = 0
        self.sprite = c.sprite((c.rectangle(50,50,"red"), c.rectangle(50,50,"blue")), top_left=0)

    def update(self):
        self.sprite.frame = self.mine
        if self.mine:
            if c.mouse_down():
                self.x = c.mouse_position()[0]
                self.y = c.mouse_position()[1]
        self.sprite.slide_to(2, self.x, self.y)

squares = []
def on_spawn(pos):
    print("Cube joined")
    squares.append(pos)

SharedSquare = sharedObjects.create("square", Square, 
    son.Fields.int("x"),
    son.Fields.int("y"),
    spawn_callback=on_spawn
)

import pygame_canvas as c

c.window()

mine = SharedSquare()
mine.mine = 1
squares.append(mine)

while c.loop(60):
    for square in squares:
        square.update()

    c.debug_list(
        *[str(x) for x in sharedObjects.object_database],
        font = None,
        color = "black"
    )

    if not c.get_frames() % 1:
        sharedObjects.send_updates()
