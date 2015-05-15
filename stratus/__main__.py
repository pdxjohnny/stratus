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
AUTH_USER = False
AUTH_PASS = False

def print_recv(data):
    sys.stdout.write(data["from"] + ": " + str(data["data"]) + "\r\n")
    sys.stdout.write(PROMPT)

def auth(username, password):
    if username == AUTH_USER and password == AUTH_PASS:
        return True
    return False

def start(args):
    server_process = stratus.server()
    if "username" in args and "password" in args:
        global AUTH_USER
        global AUTH_PASS
        AUTH_USER = args["username"]
        AUTH_PASS = args["password"]
        del args["username"]
        del args["password"]
        server_process.auth = auth
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
        help="Address of host server")
    ARG_PARSER.add_argument("--port", type=int, \
        help="Port to host or connect to stratus server")
    ARG_PARSER.add_argument("--key", type=unicode, \
        help="Key file to use")
    ARG_PARSER.add_argument("--crt", type=unicode, \
        help="Cert file to use")
    ARG_PARSER.add_argument("--name", "-n", type=unicode, \
        help="Name to identify client by other than hostname")
    ARG_PARSER.add_argument("--username", "-u", type=unicode, \
        help="Username to connect to stratus server")
    ARG_PARSER.add_argument("--password", "-p", type=unicode, \
        help="Password to connect to stratus server")
    ARG_PARSER.add_argument("--ssl", action='store_true', default=False, \
        help="Connect to the server with ssl")
    ARG_PARSER.add_argument("--version", "-v", action="version", \
        version=u"stratus " + unicode(stratus.__version__) )
    initial = vars(ARG_PARSER.parse_args())
    args = {}
    for arg in initial:
        if initial[arg]:
            args[arg] = initial[arg]
    return args

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
