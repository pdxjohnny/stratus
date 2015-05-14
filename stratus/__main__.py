"""
Stratus

Facilitates connections



"""

import sys
import time
import stratus
import argparse

ARG_PARSER = False
PROMPT = ":\r"

def print_recv(data):
    sys.stdout.write(data["from"] + ": " + str(data["data"]) + "\r\n")
    sys.stdout.write(PROMPT)

def start(args):
    server_process = stratus.server()
    server_process.start(**args)
    sys.stdout.write("Server listening\r\n")
    while True:
        time.sleep(300)

def connect(args):
    client_conn = stratus.client(**args)
    client_conn.recv = print_recv
    client_conn.connect()
    while True:
        sys.stdout.write(PROMPT)
        data = sys.stdin.readline()
        if len(data) > 1:
            data = data[:-1]
            if data == "exit":
                return 0
            else:
                client_conn.send(data)

def arg_setup():
    global ARG_PARSER
    ARG_PARSER = argparse.ArgumentParser(description=stratus.__description__)
    ARG_PARSER.add_argument("action", type=unicode, \
        help="Start server or connect to server (start, connect)")
    ARG_PARSER.add_argument("--host", "-a", type=unicode, \
        help="Address to connect to or host server on")
    ARG_PARSER.add_argument("--port", "-p", type=int, \
        help="Port to host or connect to stratus server")
    ARG_PARSER.add_argument("--name", "-n", type=unicode, \
        help="Name to identify client by other than hostname")
    ARG_PARSER.add_argument("--version", "-v", action="version", \
        version=u"stratus " + unicode(stratus.__version__) )
    initial = vars(ARG_PARSER.parse_args())
    used = {}
    for arg in initial:
        if initial[arg]:
            used[arg] = initial[arg]
    return used

def main():
    print (stratus.__logo__)
    args = arg_setup()
    if args["action"].lower() == "start":
        action = start
    elif args["action"].lower() == "connect":
        action = connect
    del args["action"]
    action(args)
    return 0

if __name__ == "__main__":
    main()
