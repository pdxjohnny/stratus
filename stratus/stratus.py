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

VERSION = "0.0.1"


class server(SimpleHTTPSServer.handler):
    """docstring for handler"""
    def __init__( self ):
        super(server, self).__init__()
        self.conns = {}
        self.data = {}
        self.actions = [
            ( 'post', '/ping/:name', self.post_ping ),
            ( 'get', '/ping/:name', self.get_ping )
            ]
    
    def log(self, message):
        print message

    def get_ping( self, request ):
        output = json.dumps(request['variables'])
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        return self.end_response( headers, output )

    def post_ping( self, request ):
        output = self.form_data(request['data'])
        output = json.dumps( output )
        headers = self.create_header()
        headers["Content-Type"] = "application/json"
        return self.end_response( headers, output )

    def post_response( self, request ):
        headers = self.create_header()
        headers = self.add_header( headers, ( "Content-Type", "application/octet-stream") )
        return self.end_response( headers, request['post']['file_name'] )
        
    def get_post( self, request ):
        output = json.dumps(request['variables'])
        headers = self.create_header()
        headers = self.add_header( headers, ( "Content-Type", "application/json") )
        return self.end_response( headers, output )

    def get_file( self, request ):
        return self.serve_page( request["page"] )

    def start_server(self, address="0.0.0.0", port=5678, key=False, crt=False):
        server_process = SimpleHTTPSServer.server( ( address, port ), self, \
            bind_and_activate=False, threading=True, \
            key=key, crt=crt )
        return thread.start_new_thread( server_process.serve_forever, () )


class client(object):
    """docstring for client"""
    def __init__(self, addr="localhost", port=5678, protocol="http", \
        name=socket.gethostname(), update=1):
        super(client, self).__init__()
        self.addr = addr
        self.port = port
        self.protocol = protocol
        self.name = name
        self.update = update
        self.recv_data = []

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
            return json.loads(res)["OK"]
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
        return thread.start_new_thread( self.main, () )

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
        return self.post( url, {"to": to, "data": data} )

def main():
    address = "0.0.0.0"

    port = 80
    if len( sys.argv ) > 1:
        port = int ( sys.argv[1] )

    stratus_server = server()
    stratus_server.start_server()

    stratus_client = client()
    # stratus_client.connect()
    print stratus_client.send("hello there")
    raw_input("Return Key to exit\n")


if __name__ == '__main__':
    main()
