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
import random
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

class server(SimpleHTTPSServer.handler):
    """docstring for handler"""
    def __init__(self):
        super(server, self).__init__()
        self.node_timeout(1, constants.TIME_OUT)
        # Server process
        self.process = False
        self.conns = {}
        # Clients that have datetime objects in them
        self.clientsd = {}
        # Clients that don't have datetime objects in them
        self.clients = {}
        # For sending messages
        self.data = {}
        self.auth = False
        self.onconnect = False
        self.ondisconnect = False
        self.client_change = False
        self.actions = [
            ('post', '/info/:name', self.post_info, self.authenticate),
            ('post', '/ping/:name', self.post_ping, self.authenticate),
            ('post', '/call/return/:name', self.post_call_return, self.authenticate),
            ('post', '/call/failed/:name', self.post_call_failed, self.authenticate),
            ('post', '/call/:name', self.post_call, self.authenticate),
            ('get', '/ping/:name', self.get_ping, self.authenticate),
            ('get', '/connect/:name', self.get_connect, self.authenticate),
            ('get', '/disconnect/:name', self.get_disconnect, self.authenticate),
            ('get', '/messages/:name', self.get_messages, self.authenticate),
            ('get', '/connected', self.get_connected, self.authenticate),
            ('get', '/:page', self.get_connected, self.authenticate)
            ]

    def log(self, message):
        if 'STRATUS_LOG' in os.environ:
            print message
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
            no_service = "No service named \"{0}\"".format(service_name)
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
        output = json.dumps(self.clientsd, default=self.date_handler)
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        return self.end_response(headers, output)

    def start(self, host="0.0.0.0", port=constants.PORT, key=False, crt=False, threading=True, **kwargs):
        thread.start_new_thread(self.update_status, ())
        return super(server, self).start(host, port, key, crt, threading, **kwargs)

    def call_node(self, service_type=True):
        res = False
        services = [name for name in self.clientsd \
            if "service" in self.clientsd[name] \
            and self.clientsd[name]["service"] == service_type]
        self.log("DETRIMINING NODE TO CALL")
        self.log(service_type)
        self.log(services)
        # Call a random service
        if len(services) > 0:
            call_random = random.randint(0, len(services) - 1)
            self.log(call_random)
            res = services[call_random]
        self.log(res)
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
        info=False, ip=False, disconnect=False):
        curr_time = datetime.datetime.now()
        # Create node
        if not node_name in self.clientsd and not disconnect:
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
            if disconnect or curr_time - self.timeout > \
                self.clientsd[node_name]["last_update"]:
                self.clientsd[node_name]["online"] = False
                if self.ondisconnect:
                    self.ondisconnect(self.clientsd[node_name])
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
        clientsd = []
        if to == constants.ALL_CLIENTS:
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
                            (len(self.data[name][item]["seen"]) >= len(self.clientsd) or \
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
