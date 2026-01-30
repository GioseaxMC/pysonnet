import pysonnet as son
import paho.mqtt.client as mqtt
import threading as t
from random import randint

#use latest version of api
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, clean_session=True)
client.connect("test.mosquitto.org", 1883, 60)
client.subscribe("pysonnet")
client_id = randint(0x0, 0xFFFFFFFF).to_bytes(4, "little")

sharedObjects = son.SharedObjects()
sharedObjects.send = lambda payload: client.publish("pysonnet", client_id+payload)

def on_recv(client, userdata, msg):
    if not msg.payload.startswith(client_id):
        # print(f"Received message: {msg.payload}")
        sharedObjects.on_receive_callback(son.take(4, msg.payload)[1])
client.on_message = on_recv
t.Thread(target=client.loop_forever, daemon=True).start()

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

    if not c.get_frames() % 3:
        sharedObjects.send_updates()
