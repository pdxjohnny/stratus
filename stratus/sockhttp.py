import ssl as ssllib
import socket

class conn(object):
    """docstring for conn"""
    def __init__(self, host, port, headers={}, ssl=False, crt=None):
        super(conn, self).__init__()
        self.host = host
        self.port = port
        self.headers = headers
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if ssl:
            self.socket = ssllib.wrap_socket(self.socket)
        self.socket.connect((self.host, self.port))

    def get( self, url ):
        headers = ""
        for line in self.headers:
            headers += line + ': ' + self.headers[line] + "\r\n"
        self.socket.sendall('GET %s HTTP/1.1\r\n%s\r\n\r\n' % (url, headers, ))
        data = self._recv(self.socket)
        res = "\n\n".join(data.split("\n\n")[1:])
        # Dont return the newlines
        return res[1:]

    def recv( self ):
        while True:
            data = self._recv(self.socket)
            if data:
                res = "\n\n".join(data.split("\n\n")[1:])
                # Dont return the newlines
                return res[1:]

    def _recv( self, sock ):
        data = sock.recv(4048).strip()
        # Check of a Content-Length, if there is one
        # then data is being uploaded
        content_length = False
        for line in data.split('\n'):
            if 'Content-Length' in line:
                content_length = int(line.split(' ')[-1])
        # If theres a Content-Length he now there is
        # a body that is seperated from the headers
        if content_length:
            # Receve until we have all the headers
            # we know we have then wehn we reach the
            # body delim, '\n\n'
            headers, header_text = self.get_headers( data )
            # Parse the headers so he can use them
            feild_delim = False
            if 'Content-Type' in headers and 'boundary=' in headers['Content-Type']:
                feild_delim = headers['Content-Type'].split('boundary=')[-1]
            # The post_data will be what ever is after the header_text
            post_data = data[ len( header_text ) : ]
            # Remove the header to data break, we will add it back later
            if post_data.find('\n\n') != -1:
                post_data = "\n" + '\n\n'.join(data.split('\n\n')[1:])
            # Sometimes feild_delim messes up Content-Length so recive
            # until the last is found otherwise recive the size
            if feild_delim:
                post_data += self._recvall( sock, content_length - len(post_data), feild_delim + '--\n' )
            else:
                post_data += self._recvall( sock, content_length - len(post_data) )
            # Merge the headers with the posted data
            data = header_text + "\n\n" + post_data
        if len(data) < 1:
            return False
        return data

    def get_headers( self, data ):
        headers_as_object = {}
        headers = data
        if data.find('\n\n') != -1:
            headers = data.split('\n\n')[0]
        for line in headers.split('\n'):
            if line.find(': ') != -1:
                headers_as_object[ line.split(': ')[0] ] = ': '.join(line.split(': ')[1:])
        return headers_as_object, headers

    def _recvall( self, sock, n, end_on = False ):
        data = ''
        while len(data) < n:
            if end_on and data[ -len(end_on): ] == end_on:
                break
            data += sock.recv(n - len(data))
        return data

def main():
    test = conn("localhost", 5678)
    print test.get("/connect/test")
    print test.recv()

if __name__ == '__main__':
    main()