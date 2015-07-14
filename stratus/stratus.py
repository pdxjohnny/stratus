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
import multiprocessing
import SimpleHTTPSServer

import sockhttp

__version__ = "0.0.29"
__description__ = "Connection facilitator"
__logo__ = """
 ___  ____  ____    __   ____  __  __  ___
/ __)(_  _)(  _ \  /__\ (_  _)(  )(  )/ __)
\__ \  )(   )   / /(__)\  )(   )(__)( \__ \\
(___/ (__) (_)\_)(__)(__)(__) (______)(___/
"""
PORT = 5678
TIME_OUT = 20
ALL_CLIENTS = "__all__"
CONNECTION_REFUSED = "Connection Refused"

class server(SimpleHTTPSServer.handler):
    """docstring for handler"""
    def __init__(self):
        super(server, self).__init__()
        self.node_timeout(1, TIME_OUT)
        self.conns = {}
        # Clients that have datetime objects in them
        self.clientsd = {}
        # Clients that don't have datetime objects in them
        self.clients = {}
        # For sending messages
        self.data = {}
        self.auth = False
        self.onconnect = False
        self.disconnect = False
        self.client_change = False
        # Loops through the array of callable nodes
        self.rotate_call = 0
        self.actions = [
            ('post', '/info/:name', self.post_info, self.authenticate),
            ('post', '/ping/:name', self.post_ping, self.authenticate),
            ('post', '/call/:name', self.post_call, self.authenticate),
            ('post', '/call_return/:name', self.post_call_return, self.authenticate),
            ('get', '/ping/:name', self.get_ping, self.authenticate),
            ('get', '/connect/:name', self.get_connect, self.authenticate),
            ('get', '/messages/:name', self.get_messages, self.authenticate),
            ('get', '/connected', self.get_connected, self.authenticate),
            ('get', '/:page', self.get_connected, self.authenticate)
            ]

    def log(self, message):
        del message

    def date_handler(self, obj):
        return obj.isoformat() if hasattr(obj, 'isoformat') else obj

    def authenticate(self, request ):
        if not self.auth:
            return True
        authorized, response = self.basic_auth(request)
        if not authorized:
            return response
        username, password = response
        if self.auth(username, password):
            return True
        return SimpleHTTPSServer.SEND_BASIC_AUTH

    def post_ping(self, request):
        # Update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        recv_data = self.message(request["variables"]["name"], \
            recv_data["data"], recv_data["to"])
        self.add_message(recv_data)
        thread.start_new_thread(self.send_messages, (recv_data["to"], ))
        # Get messages for sender
        return self.get_messages(request)

    def post_call(self, request):
        # Update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        # print "SERVER RECEVED CALL"
        # print recv_data["call"]
        service_name = recv_data.get("service", True)
        # Distribute the load
        call_node = self.call_node(service_name)
        # If there are service nodes to call
        if call_node:
            # Send that call out to the node
            recv_message = self.message(request["variables"]["name"], \
                recv_data["call"], call_node, name="call")
            # If the service is being sent its own request then
            if request["variables"]["name"] in recv_message["seen"] \
                and request["variables"]["name"] == recv_message["to"]:
                recv_message["seen"].remove(request["variables"]["name"])
            if "return_key" in recv_data:
                recv_message["return_key"] = recv_data["return_key"]
            # print "ADDING MESSAGE"
            # print recv_message
            self.add_message(recv_message)
            thread.start_new_thread(self.send_messages, (call_node, ))
        # Get messages for sender
        return self.get_messages(request)

    def post_call_return(self, request):
        # Update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        # print "SERVER RECEVED CALL RETURN"
        # Send that call out to the node
        recv_message = self.message(request["variables"]["name"], \
            recv_data["call_return"], recv_data["to"], name="call_return")
        # If the service is being sent its own request then
        if request["variables"]["name"] in recv_message["seen"] \
            and request["variables"]["name"] == recv_message["to"]:
            recv_message["seen"].remove(request["variables"]["name"])
        if "return_key" in recv_data:
            recv_message["return_key"] = recv_data["return_key"]
        # print recv_message["call_return"]
        # print recv_message
        self.add_message(recv_message)
        # print hex(id(self.data))
        # print json.dumps(self.data, indent=4, sort_keys=True)
        # print "MESSAGES", recv_data["to"]
        # print json.dumps(self.messages(recv_data["to"]), indent=4, sort_keys=True)
        thread.start_new_thread(self.send_messages, (recv_data["to"], ))
        # Get messages for sender
        return self.get_messages(request)

    def post_info(self, request):
        # Get the info
        recv_data = self.form_data(request['data'])
        # Add the info to the node and update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            info=recv_data["info"], ip=request["socket"])
        # Get messages for sender
        return self.get_messages(request)

    def get_ping(self, request):
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Get messages for sender
        return self.get_messages(request)

    def get_connect(self, request):
        self.node_status(request["variables"]["name"], update=True, \
            conn=request["socket"], ip=request["socket"])
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
        output = json.dumps(self.clientsd, default=self.date_handler)
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        return self.end_response(headers, output)

    def start(self, host="0.0.0.0", port=PORT, key=False, crt=False, **kwargs):
        thread.start_new_thread(self.update_status, ())
        server_process = SimpleHTTPSServer.server((host, port), self, \
            bind_and_activate=False, threading=True, \
            key=key, crt=crt)
        return thread.start_new_thread(server_process.serve_forever, ())

    def call_node(self, service_type=True):
        res = False
        services = [name for name in self.clientsd \
            if "service" in self.clientsd[name] \
            and self.clientsd[name]["service"] == service_type]
        # print "DETRIMINING NODE TO CALL"
        # print service_type
        # print self.rotate_call, services
        self.rotate_call += 1
        # Set back to zero once we have called on all nodes
        if self.rotate_call >= len(services):
            self.rotate_call = 0
        if len(services) > 0:
            res = services[self.rotate_call]
        return res

    def update_status(self):
        while True:
            try:
                for node in self.clientsd:
                    self.node_status(node)
                time.sleep(self.timeout_seconds)
            except RuntimeError, error:
                # Dictionary size change is ok
                pass

    def node_status(self, node_name, update=False, conn=False, \
        info=False, ip=False):
        curr_time = datetime.datetime.now()
        # Create node
        if not node_name in self.clientsd:
            self.clientsd[node_name] = self.node(node_name, curr_time)
            if self.onconnect:
                self.onconnect(self.clientsd[node_name])
        # Update time
        elif update:
            self.clientsd[node_name]["last_update"] = curr_time
            self.clientsd[node_name]["online"] = True
        # Info
        if info:
            info = self.json(info)
            if info:
                self.clientsd[node_name].update(info)
        # Get client ip address
        if ip:
            self.clientsd[node_name]["ip"] = ip.getpeername()[0]
        # Offline
        else:
            if curr_time - self.timeout > \
                self.clientsd[node_name]["last_update"]:
                self.clientsd[node_name]["online"] = False
                if self.disconnect:
                    self.disconnect(self.clientsd[node_name])
                del self.clientsd[node_name]
                if node_name in self.conns:
                    del self.conns[node_name]
        # Connect recv socket
        if conn:
            self.conns[node_name] = conn
        # Stringify the datetimes
        self.clients = json.loads(json.dumps(self.clientsd, \
            default=self.date_handler))
        # If there is a function that needs to be called when a client changes
        if self.client_change:
            self.client_change(self.clients)

    def node(self, name, curr_time=False):
        # Don't have to call datetime.datetime.now() is provided
        if not curr_time:
            curr_time = datetime.datetime.now()
        return {
            "name": name,
            "last_update": curr_time,
            "online": True
        }

    def message(self, sent_by, data, to=ALL_CLIENTS, name="data"):
        return {
            "to": to,
            "from": sent_by,
            name: data,
            "seen": [sent_by]
        }

    def add_message(self, add):
        if not add["to"] in self.data:
            self.data[add["to"]] = []
        self.data[add["to"]].append(add)

    def send_to(self, node_name, data):
        if node_name in self.conns:
            try:
                return self.conns[node_name].sendall(data)
            except:
                del self.conns[node_name]
        return False

    def send_messages(self, to):
        clientsd = []
        if to == ALL_CLIENTS:
            clientsd = list(self.conns.keys())
        else:
            clientsd = [to]
        for client_name in clientsd:
            thread.start_new_thread(self.send_message, (client_name, ))

    def send_message(self, to):
        # Get messages for to
        send_data = self.messages(to)
        output = json.dumps(send_data)
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        # print "SENDING", len(send_data)
        self.send_to(to, self.end_response(headers, output) )
        # print "SENT"

    def messages(self, to):
        new_messages = []
        to_and_all = [to, ALL_CLIENTS]
        for name in to_and_all:
            if name in self.data:
                for item in self.data[name]:
                    # Check to see if everyone has seen this message
                    if not to in item["seen"]:
                        # Add to array of seen
                        item["seen"].append(to)
                        # Send the message without the seen array
                        append = copy.deepcopy(item)
                        del append["seen"]
                        new_messages.append(append)
                for item in xrange(0, len(self.data[name])):
                    try:
                        if len(self.data[name]) and \
                            len(self.data[name][item]["seen"]) >= len(self.clientsd):
                            del self.data[name][item]
                    except IndexError as error:
                        pass
        return new_messages

    def node_timeout(self, loop=False, delta=False):
        if loop:
            self.timeout_seconds = loop
            self.timeout = datetime.timedelta(seconds=loop)
        if delta:
            self.timeout = datetime.timedelta(seconds=delta)
        return self.timeout

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

class call_result(object):
    """
    Shares a bool between processes
    """
    def __init__(self, initval=None):
        self.initval = initval
        self.value = initval

    def __call__(self, *args, **kwargs):
        return self.result(*args, **kwargs)

    def result(self, value=None):
        if value is not None:
            self.value = value
        while self.value is self.initval:
            pass
        return self.value

class client(server):
    """docstring for client"""
    def __init__(self):
        super(client, self).__init__()
        self.host = "localhost"
        self.port = PORT
        self.ssl = False
        self.name = socket.gethostname()
        self.username = False
        self.password = False
        self.update = TIME_OUT - 5
        self.recv = False
        self.connect_fail = False
        self.crt = False
        self.results = {}

    def log(self, message):
        del message

    def http_conncet(self):
        """
        Connects to the server with tcp http connections.
        """
        self.headers = {"Connection": "keep-alive"}
        if self.username and self.password:
            encoded = base64.b64encode(self.username + ':' + self.password)
            self.headers["Authorization"] = "Basic " + encoded
        try:
            self.ping_conn = self.httplib_conn()
            self.send_conn = self.httplib_conn()
            self.recv_conn = sockhttp.conn(self.host, self.port, \
                headers=self.headers, ssl=self.ssl, crt=self.crt)
            self.recv_connect()
        except socket.error as error:
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
            res = json.loads(res)
            # print "RECIVED", len(res)
            if len(res) > 0 and hasattr(self.recv, '__call__'):
                for item in xrange(0, len(res)):
                    data = res[item]
                    data["__name__"] = self.name
                    self.call_recv(data)
            return True
        except (ValueError, KeyError):
            return False

    def call_recv(self, data):
        if "data" in data:
            as_json = self.json(data["data"])
            if as_json:
                data["data"] = as_json
            thread.start_new_thread(self.recv, (data, ))
        elif "call_return" in data:
            as_json = self.json(data["call_return"])
            if as_json:
                data["call_return"] = as_json
            if data["call_return"] == "false":
                data["call_return"] = False
            # Call and send back result
            if "return_key" in data and data["return_key"] in self.results:
                self.results[data["return_key"]](data["call_return"])
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
            self.log(CONNECTION_REFUSED)
            if hasattr(self.connect_fail, '__call__'):
                self.connect_fail()
        else:
            raise

    def get(self, url, http_conn):
        """
        Requests the page and returns data
        """
        res = ""
        try:
            url = urllib.quote(url, safe='')
            http_conn.request("GET", "/" + url, headers=self.headers)
            res = http_conn.getresponse()
            res = res.read()
        except (httplib.BadStatusLine, httplib.CannotSendRequest), error:
            self.log("Reconecting")
            self.http_conncet()
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
        except (httplib.BadStatusLine, httplib.CannotSendRequest), error:
            if reconnect:
                self.log("Reconecting")
                self.http_conncet()
                self.post(url, data, reconnect=False)
        except socket.error as error:
            self._connection_failed(error)
        return res

    def connect(self, host="localhost", port=PORT, ssl=False, \
        name=socket.gethostname(), update=TIME_OUT, crt=False, \
        username=False, password=False, **kwargs):
        """
        Starts main
        """
        self.host = host
        self.port = port
        self.ssl = ssl
        self.name = name
        self.username = username
        self.password = password
        self.update = update
        self.crt = crt
        self.http_conncet()
        return thread.start_new_thread(self.main, ())

    def main(self):
        """
        Continues to ping
        """
        while True:
            self.ping()
            time.sleep(self.update)
        return 0

    def recv_connect(self):
        """
        Connects a socket that the server can push to.
        """
        url = "/connect/" + self.name
        res = self.recv_conn.get(url)
        self.return_status(res)
        thread.start_new_thread(self.listen, () )

    def listen(self):
        while True:
            res = self.recv_conn.recv()
            if len(res):
                thread.start_new_thread(self.return_status, (res, ))

    def ping(self):
        """
        Tells the server its still here and asks for instructions
        """
        url = "ping/" + self.name
        res = self.get(url, self.ping_conn)
        return self.return_status(res)

    def send(self, data, to=ALL_CLIENTS):
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

    def info(self, data):
        """
        Queues data for sending
        """
        url = "info/" + self.name
        if type(data) != str and type(data) != unicode:
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

class service(client):
    """
    Services connect to the stratus server
    and clients can call their methods
    """
    def __init__(self):
        super(service, self).__init__()
        self.service_name = True

    def call_recv(self, data, *args, **kwargs):
        super(service, self).call_recv(data, *args, **kwargs)
        if "call" in data:
            as_json = self.json(data["call"])
            if as_json:
                data["call"] = as_json
            # Call and send back result
            thread.start_new_thread(self.call_method, (data, ))

    def call_method(self, data):
        send_to = data["from"]
        return_key = data["return_key"]
        call_data = data["call"]
        # print "CALLING METHOD"
        # print send_to, call_data
        res = False
        # Get the function
        found_method = getattr(self, call_data["name"])
        # Call the function
        res = found_method(*call_data["args"], **call_data["kwargs"])
        return self.call_return(res, send_to, return_key)

    def call_return(self, data, to, return_key):
        """
        Returns the result of a call back to caller
        """
        url = "call_return/" + self.name
        # print "CLIENT SENDING CALL RETURN"
        # print self.name, to, data
        try:
            data = json.dumps(data)
        except:
            pass
        res = {
            "to": to,
            "return_key": return_key,
            "call_return": data
        }
        res = self.post(url, res)
        return self.return_status(res)

    def connect(self, *args, **kwargs):
        super(service, self).connect(*args, **kwargs)
        if "service" in kwargs:
            self.service(kwargs["service"])
        self.service(self.service_name)

    def service(self, service_name):
        self.service_name = service_name
        # Tell the server that this is a service
        self.info({"service": self.service_name})


class stratus(service):
    """
    Fault tollerent server and service
    Will connet to master and continue to chose
    next master if master goes down
    """
    def __init__(self):
        super(stratus, self).__init__()
        self.args = []
        self.kwargs = {}
        self.cluster = {}
        self.master = []
        self.onconnect = self.update_master
        self.disconnect = self.update_master
        self.connect_fail = self.check_master

    def start(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.connect(*args, **kwargs)

    def update_master(self, new_node, cluster=False):
        if cluster:
            self.cluster = cluster
        else:
            self.cluster = self.connected()
        self.master = [name for name in self.cluster]

    def check_master(self):
        self.log("Choseing master")
        self.log(self.master)
        if len(self.master) < 1 or self.master[0] == self.name:
            self.log("I am master")
            # self.name = "__stratus_master__"
            self.kwargs["name"] = self.name
            super(stratus, self).start(*self.args, **self.kwargs)
            self.cluster[self.name] = self.kwargs
            self.update_master(self.kwargs, self.cluster)
        self.log("Connecting to new master")
        self.log(self.master)
        self.connect(**self.cluster[self.master[0]])
        if len(self.master) > 0:
            self.master.pop(0)

    def log(self, message):
        del message
        return

def print_recv(data):
    print(data)

def main():
    address = "0.0.0.0"

    port = PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    stratus_server = server()
    stratus_server.start(port=port)

    stratus_client_one = client(name="one")
    stratus_client_two = client(name="two")
    stratus_client_one.recv = print_recv
    stratus_client_two.recv = print_recv
    stratus_client_one.connect()
    stratus_client_two.connect()

    while True:
        data = raw_input("Send data: ")
        if len(data) > 0:
            data = {
                "payload": data
            }
            stratus_client_one.send(data)
        pass


if __name__ == '__main__':
    main()
