#
# Author: Gregory Fleischer (gfleischer@gmail.com)
#
# Copyright (c) 2012 Gregory Fleischer
#
# This file is part of WTFY.
#
# WTFY is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# WTFY is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WTFY.  If not, see <http://www.gnu.org/licenses/>.
#
import socket
import select
import errno
import struct
import time
import traceback
import sys
from urllib2 import urlparse
from OpenSSL import SSL
import re

NOLINGER = struct.pack('ii', 1, 0)

from HttpReader import HttpReader
from HttpWriter import HttpWriter
from ProxyTunnel import ProxyTunnel

class ProxyConnection():

    S_INITIAL = 0
    S_CONNECTED = 1
    S_NEED_CLIENT_CONNECTION = 2
    S_NEED_CLIENT_RESOLVE = 3
    S_CLIENT_CONNECTED = 4
    S_CLIENT_REQUEST_SENT = 5
    S_CLIENT_RESPONSE_READ = 6
    S_SERVER_REQUEST_READ = 7
    S_SERVER_RESPONSE_SENT = 8
    S_TUNNEL_ESTABLISHED = 9
    S_NEED_CONNECTION_CLOSE = 10
    S_CLOSED = 11
    S_CACHED_CLIENT_CONNECTION = 12

    def __init__(self, proxy_server, ssock, saddr, observer):
        self.proxy_server = proxy_server
        self.ssock = ssock
        self.saddr = saddr
        self.observer = observer

        self.csock = None
        self.csock_fileno = -1

        self.ssock_fileno = self.ssock.fileno()
        self.ssock.setblocking(0)
        self.ssock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        self.ssock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        self.connect_time = time.time()
        self.start_time = None
        self.server_state = self.S_CONNECTED
        self.client_state = self.S_INITIAL

        self.tunnel_request = False
        self.proxy_request = False

        self.re_ip_address = re.compile('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        
        self.quiet = False

        self.setup_object_state()

    def setup_object_state(self):

        self.server_http_reader = HttpReader(self.ssock)
        self.server_http_writer = None
        self.server_to_client = None

        self.client_http_reader = None
        self.client_http_writer = None
        self.client_to_server = None
        self.client_hostname = None
        self.client_ip_address = None
        self.client_port = None

    def close(self):
        self.close_client()
        self.close_server()

    def close_server(self):
        try:
            if self.ssock:
#                if self.use_ssl and not self.state == self.S_NEED_SSL_HANDSHAKE:
#                    ok = self.csock.shutdown()
                self.ssock.close()
                self.ssock = None
        except socket.error, e:
            if not self.quiet:
                sys.stderr.write('failed on server close: %s\n' % (e))

        self.server_state = self.S_CLOSED
        self.server_http_reader = None
        self.server_http_writer = None
        self.server_to_client = None

        if self.csock and self.client_ip_address:
            self.proxy_server.cache_client_socket((self.csock, self.client_hostname, self.client_ip_address, self.client_port))

        self.proxy_server = None

    def close_client(self):
        try:
            if self.csock:
                self.csock.close()
                self.csock = None
        except socket.error, e:
            if not self.quiet:
                sys.stderr.write('failed on client close: %s\n' % (e))

        self.client_state = self.S_CLOSED
        self.client_http_reader = None
        self.client_http_writer = None
        self.client_to_server = None
        self.client_hostname = None
        self.client_ip_address = None
        self.client_port = None

    def server_fileno(self):
        return self.ssock_fileno

    def client_fileno(self):
        if self.csock:
            try:
                return self.csock.fileno()
            except socket.error, e:
                return False
        else:
            return -1

    def is_server_connected(self):
        return self.ssock and self.server_state != self.S_CLOSED

    def is_server_readable(self):
        return self.ssock and (
            (self.server_state in (self.S_CONNECTED, self.S_SERVER_RESPONSE_SENT,))
            or
            (self.tunnel_request and self.server_state == self.S_TUNNEL_ESTABLISHED)
            )

    def is_server_writeable(self):
        return self.ssock and (
            (self.client_state in (self.S_CLIENT_RESPONSE_READ,) and self.server_state not in (self.S_SERVER_RESPONSE_SENT,))
            or
            (self.tunnel_request and self.client_state in (self.S_CLIENT_CONNECTED, self.S_TUNNEL_ESTABLISHED) and self.server_state not in (self.S_SERVER_RESPONSE_SENT,) and (None == self.client_to_server or self.client_to_server.need_write()))
            )

    def is_client_connected(self):
        try:
            return self.csock and self.client_state not in (self.S_INITIAL, self.S_NEED_CLIENT_CONNECTION, self.S_NEED_CLIENT_RESOLVE, self.S_CLOSED)
        except socket.error, e:
            return False

    def is_client_readable(self):
        return self.csock and (
            (self.client_state in (self.S_CLIENT_REQUEST_SENT,)) 
            or 
            (self.tunnel_request and self.client_state in (self.S_CLIENT_CONNECTED, self.S_TUNNEL_ESTABLISHED))
            )

    def is_client_writeable(self):
        return self.csock and (
            (self.client_state in (self.S_CLIENT_CONNECTED,) and self.server_state in (self.S_SERVER_REQUEST_READ,))
            or 
            (self.tunnel_request and self.client_state in (self.S_CLIENT_CONNECTED, self.S_TUNNEL_ESTABLISHED) and (None == self.server_to_client or self.server_to_client.need_write()))
            )

    def is_tunnel_established(self):
        return self.ssock and self.server_state == self.S_TUNNEL_ESTABLISHED

    def need_client_connection(self):
        return self.client_state in (self.S_NEED_CLIENT_CONNECTION,)

    def need_client_resolve(self):
        return self.client_state in (self.S_NEED_CLIENT_RESOLVE,)

    def need_client_close(self):
        return self.client_state == self.S_NEED_CONNECTION_CLOSE

    def need_server_close(self):
        return self.server_state == self.S_NEED_CONNECTION_CLOSE

    def elapsed_seconds(self, now):
        if self.start_time:
            return now - self.start_time
        elif self.connect_time:
            return now - self.connect_time
        else:
            return 0

    def connect_client(self):
        ok = False
        try:
            self.csock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.csock.setblocking(0)
            self.csock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
            self.csock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            self.csock.connect((self.client_ip_address, self.client_port))
            ok = True
        except socket.error, e:
            if e.errno == errno.EINPROGRESS:
                ok = True
            else:
                if not self.quiet:
                    sys.stderr.write('failed on connect [%s:%d]: %s\n' % (self.client_ip_address, self.client_port, e))
        if ok:
            self.client_state = self.S_CLIENT_CONNECTED

    def client_resolved(self, ip_address):
        self.client_ip_address = ip_address
        self.client_state = self.S_NEED_CLIENT_CONNECTION

    def calculate_target(self, target):
        self.proxy_target = target
        if ':' in self.proxy_target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 80 # TODO: fix assumption

        if self.client_hostname and self.client_hostname != host:
            self.close_client()
            
        self.client_hostname = host
        self.client_port = port
        if self.re_ip_address.match(host):
            self.client_ip_address = host
            cache_item = self.proxy_server.check_client_socket_cache(self.client_ip_address, self.client_port)
            if not cache_item:
                self.client_state = self.S_NEED_CLIENT_CONNECTION
            else:
                print('cached!', cache_item)
                self.client_state = self.S_CACHED_CLIENT_CONNECTION
                self.csock = cache_item[0]
        else:
            cache_item = self.proxy_server.check_client_socket_cache(self.client_hostname, self.client_port)
            if cache_item:
                print('cached!', cache_item)
                self.client_state = self.S_CACHED_CLIENT_CONNECTION
                self.csock = cache_item[0]
                self.client_ip_address = cache_item[1]
            else:
                ip_address = self.proxy_server.resolve_host(host)
                if not ip_address:
                    # need to resolve
                    self.client_state = self.S_NEED_CLIENT_RESOLVE
                else:
                    self.client_ip_address = ip_address
                    self.client_state = self.S_NEED_CLIENT_CONNECTION

    def read_server(self):
        finished, fatal_error = True, False
        if not self.server_http_reader.headers_available():
            finished, fatal_error = self.server_http_reader.read_request_headers()
            if finished and not fatal_error:
                method, resource, version, headers = self.server_http_reader.extract_request_headers()
                if 'CONNECT' == method:
                    # need to establish tunnel
                    self.tunnel_request = True
                    if ':' not in resource:
                        # TODO: need to teardown and fail 
                        pass
                    else:
                        self.calculate_target(resource)
                else:
                    # proxy request
                    self.proxy_request = True
                    splitted = urlparse.urlsplit(resource)
                    if splitted.netloc:
                        self.calculate_target(splitted.netloc)
                    else:
                        host = headers['host']
                        if not host:
                            # TODO: need to teardown and fail 
                            pass
                        self.calculate_target(host)

        if finished and not fatal_error:
            if not self.server_http_reader.body_available():
                finished, fatal_error = self.server_http_reader.read_request_body()

        if finished and not fatal_error:
            self.server_state = self.S_SERVER_REQUEST_READ
            self.request_prepared = False

        if fatal_error:
            self.server_state = self.S_NEED_CONNECTION_CLOSE

        return finished, fatal_error

    def write_server(self):
        finished, fatal_error = True, False

        if not self.server_http_writer:
            self.server_http_writer = HttpWriter(self.ssock)

        if self.tunnel_request:
            status = '200'
            message = 'Connection Established'
            headers = {}
            body = ''
            finished, fatal_error = self.server_http_writer.send_response(status, message, headers, body)

            if finished and not fatal_error:
                self.server_state = self.S_TUNNEL_ESTABLISHED
                self.client_state = self.S_TUNNEL_ESTABLISHED
                self.server_to_client = ProxyTunnel(self.ssock, self.csock)
                self.client_to_server = ProxyTunnel(self.csock, self.ssock)

        elif self.proxy_request:
            version, status, message, headers = self.client_http_reader.extract_response_headers()
            body = self.client_http_reader.body()
            # TODO: refactor
            if headers.has_key('content-encoding'):
                headers['content-encoding'] = 'identity'
            need_client_close = False
            # TODO: add support for persistent connections
            if 'HTTP/1.1' == self.version:
                if headers.has_key('connection') and headers['connection'].lower() == 'close':
                    need_client_close = True
            else:
                if not headers.has_key('connection') or headers['connection'].lower() != 'keep-alive':
                    need_client_close = True

            if self.observer != None:
                # TODO: fix this all to dynamically send to account for manipulation
                # no need to recalculate each time ...
                headers, body = self.observer.on_response(self.client_hostname, headers, body, self.request_context)

            finished, fatal_error = self.server_http_writer.send_response(status, message, headers, body)

            if finished and not fatal_error:
                # this is assuming no failures and completion of request/response
                self.server_state = self.S_SERVER_RESPONSE_SENT
                if need_client_close:
                    self.client_state = self.S_NEED_CONNECTION_CLOSE
                else:
                    self.client_state = self.S_CLIENT_CONNECTED
                self.setup_object_state()

        if fatal_error:
            self.server_state = self.S_NEED_CONNECTION_CLOSE

        return finished, fatal_error

    def read_client(self):
        finished, fatal_error = True, False

        if not self.client_http_reader:
            self.client_http_reader = HttpReader(self.csock)

        if not self.client_http_reader.headers_available():
            finished, fatal_error = self.client_http_reader.read_response_headers()

        if finished and not fatal_error:
            if not self.client_http_reader.body_available():
                finished, fatal_error = self.client_http_reader.read_response_body(self.method)

        if finished and not fatal_error:
            self.client_state = self.S_CLIENT_RESPONSE_READ

        if fatal_error:
            self.client_state = self.S_NEED_CONNECTION_CLOSE

        return finished, fatal_error

    def write_client(self):
        finished, fatal_error = True, False

        if not self.client_http_writer:
            self.client_http_writer = HttpWriter(self.csock)
        
        if not self.request_prepared:
            self.method, self.request_resource, self.version, self.request_headers = self.server_http_reader.extract_response_headers()
            self.request_body = self.server_http_reader.body()

            if self.observer is not None:
                self.request_headers, self.request_body, self.request_context = self.observer.on_request(self.client_hostname, self.client_ip_address, self.method, self.request_resource, self.version, self.request_headers, self.request_body)

            for name in ('proxy-connection', 'transfer-encoding',):
                if self.request_headers.has_key(name):
                    del(self.request_headers[name])
            self.request_headers['connection'] = 'keep-alive'

            self.request_prepared = True

        finished, fatal_error = self.client_http_writer.send_request(self.method, self.request_resource, self.request_headers, self.request_body)

        if finished and not fatal_error:
            self.client_state = self.S_CLIENT_REQUEST_SENT

        if fatal_error:
            if self.client_state == self.S_CACHED_CLIENT_CONNECTION:
                # stale, but could have failed on upload ...
                self.client_state = self.S_NEED_CLIENT_CONNECTION
            else:
                self.client_state = self.S_NEED_CONNECTION_CLOSE

        return finished, fatal_error

    def read_tunnel_client(self):
        finished, fatal_error = self.client_to_server.read()
        if fatal_error:
            self.client_state = self.S_NEED_CONNECTION_CLOSE
        return finished, fatal_error

    def write_tunnel_client(self):
        finished, fatal_error = self.server_to_client.write()
        if fatal_error:
            self.client_state = self.S_NEED_CONNECTION_CLOSE
        return finished, fatal_error

    def read_tunnel_server(self):
        finished, fatal_error = self.server_to_client.read()
        if fatal_error:
            self.server_state = self.S_NEED_CONNECTION_CLOSE
        return finished, fatal_error

    def write_tunnel_server(self):
        finished, fatal_error = self.client_to_server.write()
        if fatal_error:
            self.server_state = self.S_NEED_CONNECTION_CLOSE
        return finished, fatal_error

