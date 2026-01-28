import pysonnet as son
import paho.mqtt.client as mqtt
import threading as t
from random import randint

#use latest version of api
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("test.mosquitto.org", 1883, 60)
client.subscribe("pysonnet")
client_id = randint(0x0, 0xFFFFFFFF).to_bytes(4, "big")

sharedObjects = son.SharedObjects()
sharedObjects.send = lambda payload: client.publish("pysonnet", client_id+payload)

def on_recv(client, userdata, msg):
    if not msg.payload.startswith(client_id):
        print(f"Received message: {msg.payload}")
        sharedObjects.on_receive_callback(son.take(4, msg.payload)[1])
client.on_message = on_recv
t.Thread(target=client.loop_forever, daemon=True).start()

class Position():
    def __init__(self):
        self.x = 0
        self.y = 0

other_positions = []
def append_other_position(pos):
    print(f"Appending other position: x={pos.x}, y={pos.y}")
    other_positions.append(pos)

SharedPosition = sharedObjects.create("position", Position, 
    son.Fields.int("x"),
    son.Fields.int("y"),
    spawn_callback=append_other_position
)

position = SharedPosition()
position.x = 67
position.y = 41

while 1:
    cmd = input("Enter command (set x y / show / exit): ")
    if cmd.startswith("set"):
        _, x, y = cmd.split()
        position.x = int(x)
        position.y = int(y)
        sharedObjects.send_updates()
    elif cmd == "show":
        print("database: ", sharedObjects.object_database)
        print(f"Local Position: x={position.x}, y={position.y}")
        for i, pos in enumerate(other_positions):
            print(f"Other Position {i}: x={pos.x}, y={pos.y}")
    elif cmd == "exit":
        break