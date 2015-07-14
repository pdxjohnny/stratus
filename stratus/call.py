import sys
import time
import uuid

import stratus

__server_process__ = False
__client_conn__ = []

PROMPT = ":\r"

def print_recv(arg):
    print arg

class callme(stratus.service):
    """docstring for callme"""
    def __init__(self):
        super(callme, self).__init__()
        self.called = 0
        self.myid = str(uuid.uuid4())[:4]

    def a_method(self, one, two, three=False):
        return self.myid + " " + str(one) + " " + str(two) + " " + str(three)


def start():
    global __server_process__
    __server_process__ = stratus.server()
    __server_process__.start()
    sys.stdout.write("Server listening\r\n")

def connect(**kwargs):
    global __client_conn__
    client = callme()
    client.connect(**kwargs)
    client.recv = print_recv
    __client_conn__.append(client)
    return client

def main():
    start()
    time.sleep(0.2)
    first = connect(name="John Andersen")
    second = connect(name="Rylin Smith")
    first.call("a_method", 5, 6, three=8)
    first.call("a_method", 1, 2)
    first.call("a_method", 9, 7, three=True)
    first.call("a_method", "hello", "world")
    while True:
        sys.stdout.write(PROMPT)
        data = sys.stdin.readline()
        if len(data) > 1:
            data = data[:-1]
            if data == "exit":
                return 0
            if data.startswith("info"):
                data = data[5:]
                __client_conn__[-1].info(data)
            else:
                __client_conn__[-1].send(data)
    return

if __name__ == '__main__':
    main()
