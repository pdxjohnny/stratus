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
import client

class service(client.client):
    """
    Services connect to the stratus server
    and clients can call their methods
    """
    def __init__(self):
        super(service, self).__init__()
        self.service_name = True

    def call_recv(self, data, *args, **kwargs):
        super(service, self).call_recv(data, *args, **kwargs)
        self.log("CALL RECV")
        self.log(data)
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
        res = False
        try:
            # Get the function
            found_method = getattr(self, call_data["name"])
            # Call the function
            res = found_method(*call_data["args"], **call_data["kwargs"])
            return self.call_return(res, send_to, return_key)
        except Exception as error:
            stack_track = str(error) + constants.DOUBLE_LINE_BREAK + traceback.format_exc()
            return self.call_failed(stack_track, send_to, return_key)

    def call_return(self, data, to, return_key):
        """
        Returns the result of a call back to caller
        """
        url = "call/return/" + self.name
        # self.log("CLIENT SENDING CALL RETURN")
        # self.log(data)
        try:
            data = json.dumps(data)
        except:
            pass
        res = {
            "to": to,
            "return_key": return_key,
            "call/return": data
        }
        res = self.post(url, res)
        return self.return_status(res)

    def call_failed(self, data, to, return_key):
        """
        Returns the result of a call back to caller
        """
        url = "call/failed/" + self.name
        # self.log("CLIENT SENDING CALL FAILED")
        # self.log(data)
        try:
            data = json.dumps(data)
        except:
            pass
        res = {
            "to": to,
            "return_key": return_key,
            "call/failed": data
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
