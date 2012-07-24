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

from ProxyConnection import ProxyConnection

from DnsResolver import DnsResolver

class ProxyServer():

    def __init__(self, bind_address = '', bind_port = '8118'):
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.connections = {}
        self.timeout = 30
        self.resolver = DnsResolver()
        self.resolve_cache = {}
        self.cname_list = {}
        self.queries = {}
        self.client_socket_cache = []

    def cache_client_socket(self, cache_item):
        self.client_socket_cache.append(cache_item)

    def check_client_socket_cache(self, target, port):
        for i in range(0, len(self.client_socket_cache)):
            cache_item = self.client_socket_cache[i]
            if ((cache_item[1] == target and cache_item[3] == port) or
                (cache_item[2] == target and cache_item[3] == port)):
                break
        else:
            return None

        del(self.client_socket_cache[i])
        return cache_item
        
    def resolve_host(self, host):
        if self.resolve_cache.has_key(host):
            # TODO: add time check
            return self.resolve_cache[host][0]
        else:
            query = self.resolver.submit(host)
            self.queries[query] = host
            return None

    def is_resolved(self, host):
        if self.resolve_cache.has_key(host):
            # TODO: add time check
            return self.resolve_cache[host][0]
        else:
            return None

    def process_resolved_hosts(self):
        for query in self.resolver.completed():
            host = self.queries.pop(query)
            status, result = query.check()
            print(result, status, host)
            if 'OK' == status:
                ip_address = None
                cname = None
                ttl = 1
                for a in result.answers:
                    if 'CNAME' == a['typename']:
                        cname, ttl = a['data'], a['ttl']
                    elif 'A' == a['typename']:
                        ip_address, ttl = a['data'], a['ttl']
                        break
                if ip_address:
                    self.resolve_cache[host] = (ip_address, ttl)
                    while self.cname_list.has_key(host):
                        host = self.cname_list[host]
                        self.resolve_cache[host] = (ip_address, ttl)

                elif cname:
                    ip_address = self.resolve_host(cname)
                    if not ip_address:
                        self.cname_list[cname] = host
                    else:
                        self.resolve_cache[host] = (ip_address, ttl)

    def process(self, observer = None):

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setblocking(0)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        server.bind((self.bind_address, self.bind_port))
        server.listen(128)

        lastone = None

        while True:
            try:
                # check for hostname resolution
                self.process_resolved_hosts()
                for server_fileno, connection in self.connections.iteritems():
                    if connection.need_client_resolve():
                        ip_address = self.is_resolved(connection.client_hostname)
                        if ip_address:
                            connection.client_resolved(ip_address)
                        

                rlist = [server.fileno()]
                wlist = []
                xlist = []

                rlist.extend([c.server_fileno() for c in self.connections.values() if c.is_server_readable()])
                wlist.extend([c.server_fileno() for c in self.connections.values() if c.is_server_writeable()])
                xlist.extend([c.server_fileno() for c in self.connections.values() if c.is_server_connected()])

                rlist.extend([c.client_fileno() for c in self.connections.values() if c.is_client_readable()])
                wlist.extend([c.client_fileno() for c in self.connections.values() if c.is_client_writeable()])
                xlist.extend([c.client_fileno() for c in self.connections.values() if c.is_client_connected()])

                rlist.extend(self.resolver.readable())
                wlist.extend(self.resolver.writeable())
                xlist.extend(self.resolver.established())
                

#                print(rlist, wlist, xlist)
                rlist, wlist, xlist = select.select(rlist, wlist, xlist, 1)

                # TODO: clean-up and unify
                for fileno in xlist:
                    self.resolver.handle(fileno, 'x')
                for fileno in wlist:
                    self.resolver.handle(fileno, 'w')
                for fileno in rlist:
                    self.resolver.handle(fileno, 'r')

                # debug
                thisone = (rlist, wlist, xlist)
                if thisone != lastone:
#                    print(thisone)
                    lastone = thisone

                server_fileno = server.fileno()
                if server_fileno in rlist:
                    csock, caddr = server.accept()
                    print('client connection:', csock.fileno(), caddr)
                    pc = ProxyConnection(self, csock, caddr, observer)
                    self.connections[pc.server_fileno()] = pc

                now = time.time()
                cleanup_list = []
                for server_fileno, connection in self.connections.iteritems():
                    client_fileno = connection.client_fileno()
                    if server_fileno in xlist or client_fileno in xlist:
                        cleanup_list.append(server_fileno)
                        continue

                    finished, fatal_error = False, False
                    try:
                        if connection.tunnel_request and connection.is_tunnel_established():
                            if server_fileno in rlist:
                                finished, fatal_error = connection.read_tunnel_server()
                            if server_fileno in wlist:
                                finished, fatal_error = connection.write_tunnel_server()
                            if client_fileno in rlist:
                                finished, fatal_error = connection.read_tunnel_client()
                            if client_fileno in wlist:
                                finished, fatal_error = connection.write_tunnel_client()
                        else:
                            if server_fileno in rlist or pc.is_server_readable(): # could be first connection
                                finished, fatal_error = connection.read_server()
                            if server_fileno in wlist:
                                finished, fatal_error = connection.write_server()
                            if client_fileno in rlist:
                                finished, fatal_error = connection.read_client()
                            if client_fileno in wlist:
                                finished, fatal_error = connection.write_client()

                    except Exception, e:
                        sys.stderr.write('client error: %s\n' % (traceback.format_exc()))
                        cleanup_list.append(server_fileno)

                # check for new connection, timeouts, closes
                for server_fileno, connection in self.connections.iteritems():
                    if server_fileno in cleanup_list:
                        pass
                    elif connection.elapsed_seconds(now) > self.timeout:
                        cleanup_list.append(server_fileno)
                    elif connection.need_client_connection():
                        connection.connect_client()
                    elif connection.tunnel_request and (connection.need_server_close() or connection.need_client_close()):
                        cleanup_list.append(server_fileno)
                    elif connection.proxy_request and (connection.need_server_close() and connection.need_client_close()):
                        cleanup_list.append(server_fileno)
                    if connection.need_client_close():
                        connection.close_client()
                    if connection.need_server_close():
                        connection.close_server()

                for server_fileno in cleanup_list:
                    connection = self.connections.pop(server_fileno)
                    connection.close()

            except Exception, e:
                sys.stderr.write('major error: %s\n' % (traceback.format_exc()))
