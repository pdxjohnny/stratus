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

    def recv_call(self, data):
        self.log("CALL RECV")
        self.log(data)
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
        self.log("CLIENT SENDING CALL RETURN")
        self.log(data)
        self.post({
            "action": "call_return",
            "to": to,
            "return_key": return_key,
            "data": data,
        })

    def call_failed(self, data, to, return_key):
        """
        Returns the result of a call back to caller
        """
        self.log("CLIENT SENDING CALL FAILED")
        self.log(data)
        self.post({
            "action": "call_failed",
            "to": to,
            "return_key": return_key,
            "data": data,
        })

    def connect(self, *args, **kwargs):
        super(service, self).connect(*args, **kwargs)
        if "service" in kwargs:
            self.service(kwargs["service"])
        self.service(self.service_name)

    def service(self, service_name):
        self.service_name = service_name
        # Tell the server that this is a service
        self.info({
            "service": self.service_name,
        })

    def my_name(self):
        return self.service_name

def main():
    test = service()
    test.connect(host="localhost", port=1234)
    raw_input()

if __name__ == '__main__':
    main()
