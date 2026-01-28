from random import randint
import struct
# per field ids are useless till i implement single field change tracking, for speed purposes i wont right now

def take(n: int, b: bytes):
    return b[:n] , b[n:]

class Fields:
    class Field:
        def __init__(self, name):
            self.name = name
            self.value = None
            self.id: int = -1
        
        def __set__(self, value):
            # send to change buffer
            # print(f"Setting {self.name} to {value}")
            self.value = value

        def __get__(self):
            # print(f"Getting {self.name} value")
            return self.value

    def int(_name):
        class Int(Fields.Field):
            def __init__(self):
                super().__init__(_name)

            def struct_type(self):
                return "I"
        return Int

    def float(_name):
        class Float(Fields.Field):
            def __init__(self):
                super().__init__(_name)

            def struct_type(self):
                return "f"
        return Float

class SharedObjects:
    def __init__(self):
        # list of shared instances
        self.object_database = dict()
        # list of class creators, in the sense of shared version of classes (SharedPerson)
        self.shared_classes = dict()
        # change database
        self.changed = set()
        # name to id

    def send(self, data: bytes):
        raise NotImplementedError("Network communication not implemented, replace this function with a callback:\n\tsharedObjects.send = callback_function")

    def on_receive_callback(self, data: bytes): # not sure yet
        print(f"ON RECEIVE CALLBACK")
        # "Network communication, put this function into your handler and feed it the bytes"
        while len(data):
            type, data = take(1, data)
            print(f"Received message of type and data is: {data}")
            if type == b"c":
                print("Received creation")
                description, data = take(4+64, data)
                created_id, name_and_signature = struct.unpack("<I64s", description) #returns int and bytes
                if created_id in self.object_database:
                    return # already exists
                name, signature = name_and_signature.decode().strip("\x00").split("|", 1)
                print(name, signature)

                if name not in self.shared_classes:
                    raise ValueError(f"Received creation for unknown shared class: {name}") # :)
                
                print(self.shared_classes[name])
                instance = self.shared_classes[name](__id = created_id)
                self.shared_classes[name]._spawn_callback(instance)
                self.object_database[created_id] = instance

                if signature != instance.struct_signature():
                    raise ValueError(f"Received creation for shared class {name} with invalid signature\n\t<{signature}> != <{instance.struct_signature()}>\n\t<{len(signature)}> != <{len(instance.struct_signature())}>")

                #load fields:
                size = struct.calcsize(signature)
                description, data = take(size, data)
                field_values = struct.unpack("<"+signature, description)
                for field, value in zip(instance._fields, field_values):
                    field.value = value

            elif type == b"u":
                description, data = take(4, data)
                update_id, = struct.unpack("<I", description)

                if not update_id in self.object_database:
                    data = b"" # unknown object, discard rest of data, will lose some updates
                    self.send(b"?" + struct.pack("<I", update_id))
                    return

                instance = self.object_database[update_id]
                
                # there will be collisions if both sides change the same field
                # TODO: implement conflict resolution and ownership
                size = struct.calcsize(instance.struct_signature())
                description, data = take(size, data)
                field_values = struct.unpack("<"+instance.struct_signature(), description) # updates can be batched, so data may not be over
                for field, value in zip(instance._fields, field_values):
                    field.value = value

            elif type == b"?":
                description, data = take(4, data)
                asked_id, = struct.unpack("<I", description)
                self.send_creation(self.object_database[asked_id], self.object_database[asked_id]._shared_class_name)
            else:
                ...

    def send_creation(self, instance, instance_name): # announce to the network the object now exists
        fields_format = instance.struct_signature()
        data = struct.pack(
            "=cI64s"+fields_format,
            b"c",
            instance.id,
            (instance_name + "|" + fields_format).encode(),
            *(f.value for f in instance._fields)
        )
        self.send(data)

    def send_updates(self):
        data = b""
        for instance in self.changed:
            data += struct.pack(
                "=cI"+instance.struct_signature(),
                b"u",
                instance.id,
                *(f.value for f in instance._fields)
            )
        self.changed.clear()
        self.send(data)

    def create(outer_self, shared_class_name, parent_class, *fields, spawn_callback=None):
        class Shared(parent_class):
            def __init__(self, *args, **kwargs):
                __id = kwargs.get("__id", -1)
                if "__id" in kwargs:
                    del kwargs["__id"]

                super().__setattr__("_fields", list(f() for f in fields))
                for f in self._fields: #fields id will act like hosts inside a network, can have at most 255 fields
                    super().__setattr__(f.name, f)

                super().__init__(*args, **kwargs)
                super().__setattr__("_spawn_callback", spawn_callback)
                super().__setattr__("_shared_class_name", shared_class_name)

                if __id == -1: #created locally
                    self.set_id()
                    outer_self.send_creation(self, shared_class_name)
                    outer_self.shared_classes[shared_class_name] = Shared
                else: # created remotely
                    self.set_id(__id)

            def _spawn_callback(self):
                if spawn_callback:
                    spawn_callback(self)
            
            def set_id(self, id = 0):
                while not id or id in outer_self.object_database:
                    id = randint(0, 2**32) & 0xFF_FF_FF_00
                
                outer_self.object_database[id] = self
                super().__setattr__("id", id)
                for field in self._fields:
                    id += 1
                    field.id = id

            def __getattribute__(self, name):
                attr = super().__getattribute__(name)
                if isinstance(attr, Fields.Field):
                    return attr.__get__()
                return attr

            def __setattr__(self, name, value):
                attr = super().__getattribute__(name)
                if isinstance(attr, Fields.Field):
                    attr.__set__(value)

                    # TODO: implement proper change tracking
                    # for now use the object id, change tracking for now is just dumping the whole struct into the network
                    # potentially i could even not track changes at all and just track which struct has changed with a flag, or add the struct to a list (which would be faster)
                    # then i could just send the whole struct every time, we'll see
                    outer_self.changed.add(self) # append only a reference to the instance
                else:
                    super().__setattr__(name, value)

            def struct_signature(self):
                return "".join(f.struct_type() for f in self._fields)

        outer_self.shared_classes[shared_class_name] = Shared
        return Shared

def main():
    class Person:
        def __init__(self):
            self.height = 67.69
            self.age = 30

    sharedObjects = SharedObjects()
    sharedObjects.send = lambda data: print(f"Sending data: {data}")

    SharedPerson = sharedObjects.create("person", Person, 
        Fields.Float("height"),
        Fields.Int("age")
    )

    shared_person = SharedPerson()

    shared_person.height = 180.5
    shared_person.age = 30

    data = {
        "height": shared_person.height,
        "age": shared_person.age
    }

    sharedObjects.send_updates()

if __name__ == "__main__":
    main()