# recv_data = False
# # Get the info
# try:
#     recv_data = self.form_data(request['data'])
# except KeyError as e:
#     pass
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

import constants
import errors

from tornado import websocket, web, ioloop
import uuid
import json

websocket_clients = {}
stratus_clients = {}

def stratus_recv(data):
    websocket_clients[data["__name__"]].write_message(data)

class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def on_message(self, message):
        stratus_clients[self.client_name].send(message)

    def open(self):
        self.client_name = str(uuid.uuid4())
        self.application.node_status(self.client_name, \
            conn=self, ip=self.request.remote_ip)
        print self.request

    def on_close(self):
        if self.client_name in websocket_clients:
            del websocket_clients[self.client_name]
        if self.client_name in stratus_clients:
            stratus_clients[self.client_name].disconnect()
            del stratus_clients[self.client_name]

class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()
        id = self.get_argument("id")
        value = self.get_argument("value")
        data = {"id": id, "value" : value}
        data = json.dumps(data)
        for client_name in stratus_clients:
            stratus_clients[client_name].recv(data)

    @web.asynchronous
    def post(self):
        pass

class server(web.Application):
    """docstring for handler"""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.node_timeout(1, constants.TIME_OUT)
        # Server process
        self.process = False
        self.conns = {}
        # Clients that have datetime objects in them
        self.clients = {}
        # Clients that don't have datetime objects in them
        self.clients = {}
        # For sending messages
        self.data = {}
        self.auth = False
        self.onconnect = False
        self.ondisconnect = False
        self.client_change = False
        # Loops through the array of callable nodes
        self.rotate_call = 0

    def log(self, message):
        del message

    def date_handler(self, obj):
        return obj.isoformat() if hasattr(obj, 'isoformat') else obj

    def post_ping(self, request):
        # Update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        recv_message = self.message(request["variables"]["name"], recv_data)
        self.add_message(recv_message)
        thread.start_new_thread(self.send_messages, (recv_message["to"], ))
        # Get messages for sender
        return self.get_messages(request)

    def post_call(self, request):
        # Update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        service_name = recv_data.get("service", True)
        # Distribute the load
        call_node = self.call_node(service_name)
        # If there are service nodes to call
        if call_node:
            # Send that call out to the node
            recv_data["to"] = call_node
            recv_message = self.message(request["variables"]["name"], recv_data)
        else:
            no_service = "No service named \"{}\"".format(service_name)
            new_message = {
                "to": request["variables"]["name"],
                "call/failed": no_service,
            }
            recv_message = self.message("__stratus__", new_message)
        # If the service is being sent its own request then
        if request["variables"]["name"] in recv_message["seen"] \
            and request["variables"]["name"] == recv_message["to"]:
            recv_message["seen"].remove(request["variables"]["name"])
        # Attach the return key to the message
        if "return_key" in recv_data:
            recv_message["return_key"] = recv_data["return_key"]
        # Add the message to be set out
        self.log("ADDING CALL MESSAGE")
        self.log(recv_message)
        self.add_message(recv_message)
        # If there is a node to call send it the call request
        if call_node:
            thread.start_new_thread(self.send_messages, (call_node, ))
        # Get messages for sender
        return self.get_messages(request)

    def post_call_return(self, request):
        # Update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        self.log("SERVER RECEVED CALL RETURN")
        # Send that call out to the node
        recv_message = self.message(request["variables"]["name"], recv_data)
        # If the service is being sent its own request then
        if request["variables"]["name"] in recv_message["seen"] \
            and request["variables"]["name"] == recv_message["to"]:
            recv_message["seen"].remove(request["variables"]["name"])
        if "return_key" in recv_data:
            recv_message["return_key"] = recv_data["return_key"]
        self.add_message(recv_message)
        self.log("MESSAGES" + recv_data["to"])
        self.log(json.dumps(self.data[recv_data["to"]], indent=4, sort_keys=True))
        thread.start_new_thread(self.send_messages, (recv_data["to"], ))
        # Get messages for sender
        return self.get_messages(request)

    def post_call_failed(self, request):
        # Update the status of the node
        self.node_status(request["variables"]["name"], update=True, \
            ip=request["socket"])
        # Add message to be sent out
        recv_data = self.form_data(request['data'])
        # Send that call out to the node
        recv_message = self.message(request["variables"]["name"], recv_data)
        # If the service is being sent its own request then
        if request["variables"]["name"] in recv_message["seen"] \
            and request["variables"]["name"] == recv_message["to"]:
            recv_message["seen"].remove(request["variables"]["name"])
        if "return_key" in recv_data:
            recv_message["return_key"] = recv_data["return_key"]
        self.add_message(recv_message)
        self.log("MESSAGES" + recv_data["to"])
        self.log(json.dumps(self.data[recv_data["to"]], indent=4, sort_keys=True))
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

    def get_disconnect(self, request):
        self.node_status(request["variables"]["name"], disconnect=True)
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
        output = json.dumps(self.clients, default=self.date_handler)
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        return self.end_response(headers, output)

    def start(self, host="0.0.0.0", port=constants.PORT, key=False, crt=False, threading=True, **kwargs):
        websocket_handler = [
            (r'/stratus_ws', SocketHandler),
        ]
        super(server, self).__init__(websocket_handler)
        self.listen(port)
        if threading:
            thread.start_new_thread(ioloop.IOLoop.instance().start, ())
        else:
            ioloop.IOLoop.instance().start()

    def call_node(self, service_type=True):
        res = False
        services = [name for name in self.clients \
            if "service" in self.clients[name] \
            and self.clients[name]["service"] == service_type]
        self.log("DETRIMINING NODE TO CALL")
        self.log(service_type)
        self.log(self.rotate_call)
        self.log(services)
        self.rotate_call += 1
        # Set back to zero once we have called on all nodes
        if self.rotate_call >= len(services):
            self.rotate_call = 0
        if len(services) > 0:
            res = services[self.rotate_call]
        self.log(res)
        return res

    def update_status(self):
        while True:
            try:
                for node in self.clients:
                    self.node_status(node)
                time.sleep(self.timeout_seconds)
            except RuntimeError, error:
                # Dictionary size change is ok
                pass

    def node_status(self, node_name, update=False, conn=False, \
        info=False, ip=False, disconnect=False):
        # Create node
        if not node_name in self.clients and not disconnect:
            self.clients[node_name] = self.node(node_name)
            if self.onconnect:
                self.onconnect(self.clients[node_name])
        # Info
        if info:
            info = self.json(info)
            if info:
                self.clients[node_name].update(info)
        # Get client ip address
        if ip:
            self.clients[node_name]["ip"] = ip
        # Offline
        else:
            if disconnect:
                self.clients[node_name]["online"] = False
                if self.ondisconnect:
                    self.ondisconnect(self.clients[node_name])
                del self.clients[node_name]
                if node_name in self.conns:
                    del self.conns[node_name]
        # Connect recv socket
        if conn:
            self.conns[node_name] = conn
        # If there is a function that needs to be called when a client changes
        if self.client_change:
            self.client_change(self.clients)

    def node(self, name):
        return {
            "name": name
        }

    def message(self, sent_by, data):
        # print data
        # Copy data and add to it
        new_message = copy.deepcopy(data)
        # Create a list of clients that have seen the message
        new_message["seen"] = [sent_by]
        # To defaults to sending to constants.ALL_CLIENTS
        if not "to" in new_message:
            new_message["to"] = constants.ALL_CLIENTS
        # If the message is being set to itself then don't add it to seen list
        if sent_by == new_message["to"]:
            new_message["seen"].remove(sent_by)
        # Add the sender to the message
        new_message["from"] = sent_by
        return new_message

    def add_message(self, add):
        if not add["to"] in self.data:
            self.data[add["to"]] = []
        self.data[add["to"]].append(add)

    def send_to(self, node_name, data):
        if node_name in self.conns:
            try:
                self.log("SENDING " + str(len(data)) + " TO " + node_name)
                self.conns[node_name].sendall(data)
                return True
            except:
                self.log("SENT FAILED " + node_name)
                del self.conns[node_name]
        return False

    def send_messages(self, to):
        clients = []
        if to == constants.ALL_CLIENTS:
            clients = list(self.conns.keys())
        else:
            clients = [to]
        for client_name in clients:
            thread.start_new_thread(self.send_message, (client_name, ))

    def send_message(self, to):
        # Get messages for to
        send_data = self.messages(to)
        output = json.dumps(send_data)
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        success = self.send_to(to, self.end_response(headers, output) )
        # Client did not get message wait for reconnect or ping
        if not success:
            for message in send_data:
                message["seen"] = []
                self.add_message(message)

    def messages(self, to):
        new_messages = []
        to_and_all = [to, constants.ALL_CLIENTS]
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
                        # If all clients have seen or the one its to has seen
                        if len(self.data[name]) and \
                            (len(self.data[name][item]["seen"]) >= len(self.clients) or \
                                self.data[name][item]["to"] in self.data[name][item]["seen"]):
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

def main():
    test = server()
    test.start(port=9000, threading=False)
    while True:
        time.sleep(300)

if __name__ == '__main__':
    main()
