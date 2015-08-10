"""
Stratus

Facilitates connections



"""

import sys
import time
import json
import argparse
import subprocess

import stratus
import service
import client
import server
import constants

PROMPT = ":\r"
AUTH_USER = False
AUTH_PASS = False
__server_process__ = False
__client_conn__ = False

def print_disconnect(client):
    print("LOG {} disconnected".format(client["name"]))

def print_recv(data):
    sys.stdout.write(data["from"] + ": " + str(data["data"]) + "\r\n")
    sys.stdout.write(PROMPT)

def shell(data):
    sys.stdout.write(data["from"] + ": " + data["data"] + "\r\n")
    output = subprocess.check_output(data["data"], shell=True)
    sys.stdout.write(output + "\r\n")
    sys.stdout.write(PROMPT)
    __client_conn__.send(output, to=data["from"])

def auth(username, password):
    if username == AUTH_USER and password == AUTH_PASS:
        return True
    return False

def master(args):
    global __server_process__
    __server_process__ = stratus.stratus()
    if "username" in args and "password" in args:
        global AUTH_USER
        global AUTH_PASS
        AUTH_USER = args["username"]
        AUTH_PASS = args["password"]
        del args["username"]
        del args["password"]
        __server_process__.auth = auth
    __server_process__.ondisconnect = print_disconnect
    __server_process__.start(**args)
    __server_process__.recv = getattr(sys.modules[__name__], args["recv"])
    while True:
        sys.stdout.write(PROMPT)
        data = sys.stdin.readline()
        if len(data) > 1:
            data = data[:-1]
            if data == "exit":
                __server_process__.stop()
                sys.exit(0)
            if data.startswith("info"):
                data = data[5:]
                __server_process__.info(data)
            else:
                __server_process__.send(data)

def start(args):
    global __server_process__
    del args["recv"]
    __server_process__ = server.server()
    if "username" in args and "password" in args:
        global AUTH_USER
        global AUTH_PASS
        AUTH_USER = args["username"]
        AUTH_PASS = args["password"]
        del args["username"]
        del args["password"]
        __server_process__.auth = auth
    __server_process__.ondisconnect = print_disconnect
    __server_process__.start(**args)
    sys.stdout.write("Server listening\r\n")
    while True:
        time.sleep(300)

def connect(args):
    global __client_conn__
    recv_function = args["recv"]
    del args["recv"]
    __client_conn__ = client.client()
    __client_conn__.connect(**args)
    __client_conn__.recv = getattr(sys.modules[__name__], recv_function)
    while True:
        sys.stdout.write(PROMPT)
        data = sys.stdin.readline()
        if len(data) > 1:
            data = data[:-1]
            if data == "exit":
                sys.exit(0)
            if data.startswith("info"):
                data = data[5:]
                __client_conn__.info(data)
            else:
                __client_conn__.send(data)

def arg_setup():
    arg_parser = argparse.ArgumentParser(description=constants.__description__)
    arg_parser.add_argument("action", type=unicode, \
        help="Start server or connect to server (start, connect, master)")
    arg_parser.add_argument("--host", "-a", type=unicode, \
        help="Address of host server")
    arg_parser.add_argument("--port", type=int, \
        help="Port to host or connect to stratus server")
    arg_parser.add_argument("--key", type=unicode, \
        help="Key file to use")
    arg_parser.add_argument("--crt", type=unicode, \
        help="Cert file to use")
    arg_parser.add_argument("--name", "-n", type=unicode, \
        help="Name to identify client by other than hostname")
    arg_parser.add_argument("--username", "-u", type=unicode, \
        help="Username to connect to stratus server")
    arg_parser.add_argument("--password", "-p", type=unicode, \
        help="Password to connect to stratus server")
    arg_parser.add_argument("--ssl", action='store_true', default=False, \
        help="Connect to the server with ssl")
    arg_parser.add_argument("--recv", "-r", type=unicode, \
        default="print_recv", \
        help="Function to exicute on recive data (print_recv, shell)")
    arg_parser.add_argument("--version", "-v", action="version", \
        version=u"stratus " + unicode(constants.__version__) )
    initial = vars(arg_parser.parse_args())
    args = {}
    for arg in initial:
        if initial[arg]:
            args[arg] = initial[arg]
    return args

def main():
    print (constants.__logo__)
    args = arg_setup()
    # Get the action
    action = getattr(sys.modules[__name__], args["action"])
    del args["action"]
    action(args)
    return 0

if __name__ == '__main__':
    main()
