#! /usr/bin/python
import socket
import json
import urllib
import ssl
import Cookie
import argparse
import thread
import os
import sys
import urllib
import urllib2
import traceback
import mimetypes
import datetime
import time
import SimpleHTTPSServer
import copy

VERSION = "0.0.2"
PORT = 5678


class server(SimpleHTTPSServer.handler):
    """docstring for handler"""
    def __init__(self):
        super(server, self).__init__()
        self.node_timeout(1, 60)
        self.conns = {}
        self.data = {}
        self.online = 0
        self.actions = [
            ('post', '/ping/:name', self.post_ping),
            ('get', '/ping/:name', self.get_ping),
            ('get', '/messages/:name', self.get_messages),
            ('get', '/connected', self.get_connected)
            ]

    def log(self, message):
        del message

    def date_handler(self, obj):
        return obj.isoformat() if hasattr(obj, 'isoformat') else obj

    def post_ping(self, request):
        self.node_status(request["variables"]["name"], update=True)
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        recv_data = self.message(request["variables"]["name"], \
            recv_data["data"], recv_data["to"])
        self.add_message(recv_data)
        # Get messages for sender
        return self.get_messages(request)

    def get_ping(self, request):
        self.node_status(request["variables"]["name"], update=True)
        # Get messages for sender
        return self.get_messages(request)

    def get_messages(self, request):
        # Get messages for sender
        send_data = self.messages(request["variables"]["name"])
        output = json.dumps(send_data)
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        return self.end_response(headers, output)

    def get_connected(self, request):
        output = json.dumps(self.conns, default=self.date_handler)
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        return self.end_response(headers, output)

    def start_server(self, address="0.0.0.0", port=PORT, key=False, crt=False):
        thread.start_new_thread(self.update_status, ())
        server_process = SimpleHTTPSServer.server((address, port), self, \
            bind_and_activate=False, threading=True, \
            key=key, crt=crt)
        return thread.start_new_thread(server_process.serve_forever, ())

    def update_status(self):
        while True:
            for node in self.conns:
                self.node_status(node)
            time.sleep(self.timeout_seconds)

    def node_status(self, node_name, update=False):
        curr_time = datetime.datetime.now()
        if not node_name in self.conns:
            self.conns[node_name] = self.node(node_name, curr_time)
            self.online += 1
        elif update:
            self.conns[node_name]["last_update"] = curr_time
            self.conns[node_name]["online"] = True
            if not self.conns[node_name]["online"]:
                self.online += 1
        else:
            if curr_time - self.timeout > \
                self.conns[node_name]["last_update"]:
                self.conns[node_name]["online"] = False
                self.online -= 1

    def node(self, name, curr_time=False):
        # Don't have to call datetime.datetime.now() is provided
        if not curr_time:
            curr_time = datetime.datetime.now()
        return {
            "name": name,
            "last_update": curr_time,
            "online": True
        }

    def message(self, sent_by, data, to="all"):
        return {
            "to": to,
            "data": data,
            "seen": [sent_by]
        }

    def add_message(self, add):
        if not add["to"] in self.data:
            self.data[add["to"]] = []
        self.data[add["to"]].append(add)

    def messages(self, to):
        new_messages = []
        if to in self.data:
            for item in xrange(0, len(self.data[to])):
                # Check to see if everyone has seen this message
                if len(self.data[to][item]["seen"]) >= self.online:
                    del self.data[to][item]
                elif not to in self.data[to][item]["seen"]:
                    # Add to array of seen
                    self.data[to][item]["seen"].append(to)
                    # Send the message without the seen array
                    append = copy.deepcopy(self.data[to][item])
                    del append["seen"]
                    new_messages.append(append)
        return new_messages

    def node_timeout(self, loop=False, delta=False):
        if loop:
            self.timeout_seconds = loop
            self.timeout = datetime.timedelta(seconds=loop)
        if delta:
            self.timeout = datetime.timedelta(seconds=delta)
        return self.timeout


class client(object):
    """docstring for client"""
    def __init__(self, addr="localhost", port=PORT, protocol="http", \
        name=socket.gethostname(), update=1, recv=False):
        super(client, self).__init__()
        self.addr = addr
        self.port = port
        self.protocol = protocol
        self.name = name
        self.update = update
        self.recv = recv

    def host(self):
        """
        Formats host url string
        """
        values = (self.protocol, self.addr, self.port,)
        url = "%s://%s:%s/" % values
        return url

    def return_status(self, res):
        """
        Returns True if OK property of returned json
        is true.
        """
        try:
            res = json.loads(res)
            if len(res) > 0 and self.recv:
                for item in xrange(0, len(res)):
                    self.recv(res[item])
            return True
        except (ValueError, KeyError):
            return False

    def _get(self, url):
        """
        Requests the page and returns data
        """
        res = urllib2.urlopen(url)
        res = res.read()
        return res

    def get(self, url):
        """
        Requests the page and returns data
        """
        url = self.host() + url
        return self._get(url)

    def _post(self, url, data):
        """
        Requests the page and returns data
        """
        data = urllib.urlencode(data, True).replace("+", "%20")
        req = urllib2.Request(url, data)
        res = urllib2.urlopen(req)
        res = res.read()
        return res

    def post(self, url, data):
        """
        Requests the page and returns data
        """
        url = self.host() + url
        return self._post(url, data)

    def ping(self):
        """
        Tells the server its still here and asks for instructions
        """
        url = "ping/" + self.name
        res = self.get(url)
        return self.return_status(res)

    def connect(self):
        """
        Starts main
        """
        return thread.start_new_thread(self.main, ())

    def connected(self):
        """
        Gets others connected
        """
        url = "connected"
        res = self.get(url)
        return json.loads(res)

    def main(self):
        """
        Continues to ping
        """
        while True:
            self.ping()
            time.sleep(self.update)
        return 0

    def send(self, data, to="all"):
        """
        Queues data for sending
        """
        url = "ping/" + self.name
        if type(data) != str and type(data) != unicode:
            data = json.dumps(data)
        res = self.post(url, {"to": to, "data": data})
        return self.return_status(res)

def print_recv(data):
    print data

def main():
    address = "0.0.0.0"

    port = 80
    if len(sys.argv) > 1:
        port = int (sys.argv[1])

    stratus_server = server()
    stratus_server.start_server()

    stratus_client_two = client(name="two")
    stratus_client_two.connect()
    stratus_client_two.recv = print_recv

    stratus_client_one = client(name="one")
    stratus_client_one.connect()
    print stratus_client_one.send("hello there", "two")

    raw_input("Return Key to exit\n")


if __name__ == '__main__':
    main()
