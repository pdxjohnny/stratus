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
import helper

from tornado import websocket, web, ioloop
import uuid
import json

class Connected(web.RequestHandler):
    @web.asynchronous
    def get(self):
        """
        Sends the clients connected
        """
        clients = json.dumps(self.application.clients)
        self.finish(clients)

class Connect(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def on_message(self, message):
        """
        Calls a method in the server based on the string in method["action"]
        If the method is not found it calls server.send passing the message
        """
        # Load to dict if message is json string
        if not isinstance(message, dict):
            message = json.loads(message)
        # Create a message from self.client_name
        message = self.application.message(self.client_name, message)
        # Get the action to be preformed
        action = message.get("action", False)
        # If there is not a method for the action then just send it
        server_method = self.application.send
        # If there is an action to be done
        if action:
            # Try to call the server method named meassge["action"]
            try:
                # Get the server method from the server
                server_method = getattr(self.application, action)
            except Exception as error:
                pass
        # Call the server method
        server_method(message)

    def open(self):
        """
        Call the open server method
        """
        self.client_name = str(uuid.uuid4())
        message = {
            "action": "open",
            "websocket": self
        }
        self.on_message(message)

    def on_close(self):
        """
        Call the disconnect server method
        """
        message = {
            "action": "disconnect"
        }
        self.on_message(message)

class server(web.Application):
    """docstring for handler"""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        # Server process
        self.process = False
        self.conns = {}
        # Clients that have datetime objects in them
        self.clients = {}
        # For sending messages
        self.data = {}
        self.auth = False
        self.onconnect = False
        self.ondisconnect = False
        self.client_change = False
        self.messages_sent = 0
        # Loops through the array of callable nodes
        self.rotate_call = 0

    def log(self, message):
        del message

    def open(self, message):
        self.node_status(message["from"], conn=message["websocket"], \
            ip=message["websocket"].request.remote_ip)
        message = {
            "action": "name",
            "to": message["from"]
        }
        message = self.message(constants.SERVER_NAME, message)
        self.add_message(message)
        thread.start_new_thread(self.send_messages, (message["to"], ))

    def send(self, message):
        self.messages_sent += 1
        print self.messages_sent
        self.add_message(message)
        thread.start_new_thread(self.send_messages, (message["to"], ))

    def call(self, message):
        # The name of the service to call
        service_name = message.get("service", True)
        # Distribute the load
        call_node = self.call_node(service_name)
        # If there are service nodes to call
        if call_node:
            # Send that call out to the node
            message["to"] = call_node
        else:
            no_service = "No service named \"{}\"".format(service_name)
            new_message = {
                "to": message["from"],
                "call_failed": no_service
            }
            message = self.message(constants.SERVER_NAME, new_message)
        # Add the message to be set out
        self.add_message(message)
        # If there is a node to call send it the call message or send the caller
        # a failed to call message
        thread.start_new_thread(self.send_messages, (message["to"], ))

    def info(self, message):
        # Add the info to the client
        self.node_status(message["from"], info=message["info"])

    def disconnect(self, message):
        # Remove the client from the active connections
        self.node_status(message["from"], disconnect=True)

    def start(self, host="0.0.0.0", port=constants.PORT, key=False, crt=False, threading=True, **kwargs):
        websocket_handler = [
            (r'/connect', Connect),
            (r'/connected', Connected),
            (r'/', Connected)
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
        self.rotate_call += 1
        # Set back to zero once we have called on all nodes
        if self.rotate_call >= len(services):
            self.rotate_call = 0
        if len(services) > 0:
            res = services[self.rotate_call]
        self.log(res)
        return res

    def node_status(self, node_name, conn=False, \
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
            if disconnect and node_name in self.conns:
                try:
                    del self.clients[node_name]
                    if self.ondisconnect:
                        self.ondisconnect(self.clients[node_name])
                    if node_name in self.conns:
                        del self.conns[node_name]
                except Exception as error:
                    pass
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

    def message(self, sent_by, new_message):
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
                self.conns[node_name].write_message(data)
                return True
            except Exception as error:
                self.log("SENT FAILED " + node_name)
                self.log(error)
                self.node_status(node_name, disconnect=True)
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
        for message in send_data:
            message["__name__"] = to
        output = json.dumps(send_data)
        success = self.send_to(to, output)
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
    test.start(port=9000, threading=True)
    while True:
        time.sleep(300)

if __name__ == '__main__':
    main()
