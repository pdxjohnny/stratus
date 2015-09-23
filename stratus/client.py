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
import datetime
import traceback
import mimetypes
import multiprocessing
import SimpleHTTPSServer

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
        self.update = constants.TIME_OUT - 5
        self.recv = False
        self.connect_fail = False
        self.crt = False
        self.ping_conn = False
        self.send_conn = False
        self.results = {}

    def http_conncet(self, recv_listen=True):
        """
        Connects to the server with tcp http connections.
        """
        self.log("http_conncet")
        self.headers = {"Connection": "keep-alive"}
        if self.username and self.password:
            encoded = base64.b64encode(self.username + ':' + self.password)
            self.headers["Authorization"] = "Basic " + encoded
        try:
            self.recv_connect(recv_listen=recv_listen)
            self.ping_conn = self.httplib_conn()
            self.send_conn = self.httplib_conn()
        except socket.error as error:
            self.log("http_conncet, failed")
            self._connection_failed(error)
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
                    data = res[item]
                    data["__name__"] = self.name
                    self.call_recv(data)
            return True
        except (ValueError, KeyError):
            return False

    def call_recv(self, data):
        if "data" in data and hasattr(self.recv, '__call__'):
            as_json = self.json(data["data"])
            if as_json:
                data["data"] = as_json
            thread.start_new_thread(self.recv, (data, ))
        elif "call/return" in data or "call/failed" in data:
            if "call/return" in data:
                message_type = "call/return"
            elif "call/failed" in data:
                message_type = "call/failed"
            as_json = self.json(data[message_type])
            if as_json:
                data[message_type] = as_json
            if data[message_type] == "false":
                data[message_type] = False
            # Call and send back result
            if "return_key" in data and data["return_key"] in self.results:
                if "call/return" == message_type:
                    self.results[data["return_key"]](data[message_type])
                elif "call/failed" == message_type:
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
        res = ""
        try:
            connection = self.httplib_conn()
            url = urllib.quote(url, safe='')
            headers = self.headers.copy()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            # So we don't urlencode twice
            if reconnect:
                data = urllib.urlencode(data, True).replace("+", "%20")
            connection.request("POST", "/" + url, data, headers)
            res = connection.getresponse()
            res = res.read()
        except (httplib.BadStatusLine, httplib.CannotSendRequest) as error:
            if reconnect:
                self.log("Reconecting")
                self.http_conncet(recv_listen=False)
                res = self.post(url, data, reconnect=False)
        except socket.error as error:
            self._connection_failed(error)
            return False
        return res

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
        self.log("Connecting to {0}:{1}".format(self.host, self.port))
        self.http_conncet()
        if start_main:
            return thread.start_new_thread(self.main, ())
        return True

    def main(self):
        """
        Continues to ping
        """
        self.running = True
        while self.running:
            self.ping()
            time.sleep(self.update)
        return 0

    def recv_connect(self, recv_listen=True):
        """
        Connects a socket that the server can push to.
        """
        self.recv_conn = sockhttp.conn(self.host, self.port, \
            headers=self.headers, ssl=self.ssl, crt=self.crt)
        url = "/connect/" + self.name
        res = self.recv_conn.get(url)
        res = self.return_status(res)
        if recv_listen:
            thread.start_new_thread(self.listen, () )
        return res

    def listen(self):
        self.running = True
        while self.running:
            try:
                res = self.recv_conn.recv()
                if len(res):
                    thread.start_new_thread(self.return_status, (res, ))
            except errors.RecvDisconnected as error:
                self.log("RecvDisconnected, Reconecting")
                time.sleep(constants.BIND_TIME)
                self.http_conncet(recv_listen=False)

    def ping(self):
        """
        Tells the server its still here and asks for instructions
        """
        url = "ping/" + self.name
        res = self.get(url, self.ping_conn)
        return self.return_status(res)

    def disconnect(self):
        """
        Tells the server we are disconnecting
        """
        url = "disconnect/" + self.name
        self.running = False
        res = self.get(url, self.send_conn)
        return self.return_status(res)

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
