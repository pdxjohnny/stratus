"""
Stratus

Facilitates connections



"""

import sys
import time
import stratus
import argparse
import subprocess

ARG_PARSER = False
PROMPT = ":\r"
AUTH_USER = False
AUTH_PASS = False
__server_process__ = False
__client_conn__ = False

def print_disconnect(client):
    print(client)

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

def start(args):
    global __server_process__
    del args["recv"]
    __server_process__ = stratus.server()
    if "username" in args and "password" in args:
        global AUTH_USER
        global AUTH_PASS
        AUTH_USER = args["username"]
        AUTH_PASS = args["password"]
        del args["username"]
        del args["password"]
        __server_process__.auth = auth
    __server_process__.disconnect = print_disconnect
    __server_process__.start(**args)
    sys.stdout.write("Server listening\r\n")
    while True:
        time.sleep(300)

def connect(args):
    global __client_conn__
    recv_function = args["recv"]
    del args["recv"]
    __client_conn__ = stratus.client(**args)
    __client_conn__.recv = getattr(sys.modules[__name__], recv_function)
    __client_conn__.connect()
    while True:
        sys.stdout.write(PROMPT)
        data = sys.stdin.readline()
        if len(data) > 1:
            data = data[:-1]
            if data == "exit":
                return 0
            else:
                __client_conn__.send(data)

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
    ARG_PARSER.add_argument("--recv", "-r", type=unicode, \
        default="print_recv", \
        help="Function to exicute on recive data (print_recv, shell)")
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
    # Get the action
    action = getattr(sys.modules[__name__], args["action"])
    del args["action"]
    action(args)
    return 0

if __name__ == '__main__':
    main()
