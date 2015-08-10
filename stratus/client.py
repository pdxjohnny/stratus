#! /usr/bin/python
import os
import re
import sys
import ssl
import json
import time
import uuid
import copy
import socket
import urllib
import Cookie
import thread
import urllib
import base64
import httplib
import argparse
import datetime
import traceback
import mimetypes
import websocket
import multiprocessing
import SimpleHTTPSServer
import logging
logger = logging.getLogger()
logger.disabled = True

import constants
import errors
import sockhttp
import server

class call_result(object):
    """
    Shares a bool between processes
    """
    def __init__(self, initval=None):
        self.initval = initval
        self.value = initval
        self.call_failed = False

    def __call__(self, *args, **kwargs):
        return self.result(*args, **kwargs)

    def result(self, value=None):
        if value is not None:
            self.value = value
        while self.value is self.initval:
            self.failed()
        return self.value

    def failed(self, value=None):
        if value is not None:
            self.call_failed = value
        elif self.call_failed is not False:
            error_string = self.call_failed
            error_trace = False
            if constants.DOUBLE_LINE_BREAK in error_string:
                error_trace = error_string.split(constants.DOUBLE_LINE_BREAK)[1]
                error_string = error_string.split(constants.DOUBLE_LINE_BREAK)[0]
            raise errors.ServiceCallFailed(error_string, error_trace)
        return self.call_failed

class client(server.server):
    """docstring for client"""
    def __init__(self):
        super(client, self).__init__()
        self.host = "localhost"
        self.port = constants.PORT
        self.ssl = False
        self.name = socket.gethostname()
        self.username = False
        self.password = False
        self.running = False
        self.update = constants.TIME_OUT - 5
        self.recv = False
        self.connect_fail = False
        self.crt = False
        self.ping_conn = False
        self.send_conn = False
        self.ws = False
        self.results = {}

    def log(self, message):
        print message

    def http_conncet(self, recv_listen=True):
        """
        Connects to the server with tcp http connections.
        """
        self.log("http_conncet")
        url = "ws://{}:{}/connect".format(self.host, self.port)
        self.ws = websocket.create_connection(url)
        return True

    def httplib_conn(self):
        values = (self.host, self.port, )
        host = "%s:%s" % values
        if self.ssl:
            return httplib.HTTPSConnection(host)
        else:
            return httplib.HTTPConnection(host)

    def return_status(self, res):
        """
        Returns True if there was a json to pass to recv.
        """
        try:
            self.log("RECEVED " + str(res))
            res = json.loads(res)
            if len(res) > 0:
                for item in xrange(0, len(res)):
                    self.call_recv(res[item])
            return True
        except (ValueError, KeyError):
            return False

    def call_recv(self, data):
        if "action" in data:
            try:
                method = getattr(self, "recv_{}".format(data["action"]))
                method(data)
            except Exception as error:
                self.log("ERROR in call_recv")
                self.log(error)

    def recv_name(self, data):
        if "__name__" in data:
            self.name = data["__name__"]
        self.log("Name changed to {}".format(self.name))

    def recv_send(self, data):
        if hasattr(self.recv, '__call__'):
            as_json = self.json(data["data"])
            if as_json:
                data["data"] = as_json
            thread.start_new_thread(self.recv, (data, ))

    def recv_call_return(self, data):
        as_json = self.json(data["data"])
        if as_json:
            data[message_type] = as_json
        if data[message_type] == "false":
            data[message_type] = False
        # Call and send back result
        if "return_key" in data and data["return_key"] in self.results:
            self.results[data["return_key"]](data[message_type])
            del self.results[data["return_key"]]

    def recv_call_failed(self, data):
        as_json = self.json(data["data"])
        if as_json:
            data[message_type] = as_json
        if data[message_type] == "false":
            data[message_type] = False
        # Call and send back result
        if "return_key" in data and data["return_key"] in self.results:
            self.results[data["return_key"]].failed(data[message_type])
            del self.results[data["return_key"]]

    def json(self, res):
        """
        Returns json if it can.
        """
        if isinstance(res, dict) or isinstance(res, list):
            return res
        try:
            res = json.loads(res)
            return res
        except (ValueError, KeyError):
            return False

    def _connection_failed(self, error):
        if "111" in str(error):
            self.log(constants.CONNECTION_REFUSED)
            if hasattr(self.connect_fail, '__call__'):
                self.connect_fail()
        else:
            raise

    def get(self, url, http_conn, reconnect=True):
        """
        Requests the page and returns data
        """
        res = ""
        try:
            if reconnect:
                url = urllib.quote(url, safe='')
            http_conn.request("GET", "/" + url, headers=self.headers)
            res = http_conn.getresponse()
            res = res.read()
        except (AttributeError, httplib.BadStatusLine, httplib.CannotSendRequest) as error:
            if reconnect:
                self.log("Reconecting")
                self.http_conncet(recv_listen=False)
                res = self.get(url, http_conn, reconnect=False)
                self.info(self.store_info, store=False)
        except socket.error as error:
            self._connection_failed(error)
        return res

    def post(self, url, data, reconnect=True):
        """
        Requests the page and returns data
        """
        if self.ws:
            self.ws.send(json.dumps(data))

    def connect(self, host="localhost", port=constants.PORT, ssl=False, \
        name=socket.gethostname(), update=constants.TIME_OUT, crt=False, \
        username=False, password=False, ip=False, start_main=True, **kwargs):
        """
        Starts main
        """
        # Connect to ip if specified
        if ip:
            host = ip
        self.host = host
        self.port = port
        self.ssl = ssl
        self.name = name
        self.username = username
        self.password = password
        self.update = update
        self.crt = crt
        # So that info can be sent to the server on reconnect
        self.store_info = {}
        self.log("Connecting to {}:{}".format(self.host, self.port))
        self.http_conncet()
        if start_main:
            return thread.start_new_thread(self.main, ())
        return True

    def ping(self):
        """
        Tells the server its still here and asks for instructions
        """
        url = "ping/" + self.name
        res = self.get(url, self.ping_conn)
        return self.return_status(res)

    def main(self):
        self.running = True
        while self.running:
            try:
                res = self.ws.recv()
                self.return_status(res)
            except Exception as error:
                self.log(error)
        self.ws = False

    def disconnect(self):
        """
        Tells the server we are disconnecting
        """
        try:
            self.ws.close()
        except Exception as error:
            pass

    def send(self, data, to=constants.ALL_CLIENTS):
        """
        Queues data for sending
        """
        url = "ping/" + self.name
        if type(data) != str and type(data) != unicode:
            data = json.dumps(data)
        res = self.post(url, {"to": to, "data": data})
        return self.return_status(res)

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def call(self, service, method, *args, **kwargs):
        """
        Calls a method on a node
        """
        url = "call/" + self.name
        call_args = {
            "name": method,
            "args": args,
            "kwargs": kwargs
        }
        if type(call_args) != str and type(call_args) != unicode:
            call_args = json.dumps(call_args)
        data = {
            "call": call_args,
            "service": service,
            # So we know where to return to
            "return_key": str(uuid.uuid4())
        }
        result_aysc = call_result()
        self.results[data["return_key"]] = result_aysc
        res = self.post(url, data)
        self.return_status(res)
        return result_aysc

    def info(self, data, store=True):
        """
        Queues data for sending
        """
        url = "info/" + self.name
        if isinstance(data, dict) or isinstance(data, list):
            if store:
                self.store_info.update(data)
            data = json.dumps(data)
        res = self.post(url, {"info": data})
        return self.return_status(res)

    def connected(self):
        """
        Gets others connected
        """
        url = "connected"
        res = self.get(url, self.send_conn)
        return self.json(res)

    def online(self):
        """
        Gets others online
        """
        connected = self.connected()
        online = {}
        if connected:
            for item in connected:
                if connected[item]["online"]:
                    online[item] = connected[item]
        return online

def main():
    test = client()
    test.connect(host="localhost", port=1234)
    raw_input()

if __name__ == '__main__':
    main()
