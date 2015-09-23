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
import service

class stratus(service.service):
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
        self.connect_fail = self.check_master

    def start(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.connect(*self.args, **self.kwargs)

    def stop(self):
        super(stratus, self).disconnect()
        return super(stratus, self).stop()

    def disconnect(self):
        return self.stop()

    def ping(self, *args, **kwargs):
        super(stratus, self).ping(*args, **kwargs)
        self.cluster = self.connected()
        if self.cluster:
            self.master = [name for name in self.cluster]

    def check_master(self):
        self.running = False
        self.log("Choseing master")
        self.log(self.master)
        if len(self.master) < 1 or self.master[0] == self.name:
            self.log("I am master")
            self.kwargs["name"] = self.name
            super(stratus, self).start(*self.args, **self.kwargs)
            self.cluster[self.name] = self.kwargs
            self.master = [name for name in self.cluster]
        # Give the new server time to bind
        time.sleep(constants.BIND_TIME)
        # Connect to the new master
        self.log("Connecting to new master")
        new_master = self.cluster[self.master[0]]
        # Don't take the new masters name
        new_master["name"] = self.name
        self.log(new_master)
        self.connect(start_main=False, **new_master)
        if len(self.master) > 0:
            self.master.pop(0)
