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
import DNS
import socket
import errno
import random
import time
import sys
import traceback

class DnsResolver():

    class DnsQuery():

        S_NONE = 0
        S_REQUEST_PENDING = 1
        S_REQUEST_SENT = 2
        S_RESPONSE_RECEIVED = 4
        S_ERROR = 8

        def __init__(self, sock, qname, qtype, flags, server):
            self.sock = sock
            self.qname = qname
            self.qtype = qtype
            self.flags = flags
            self.start = int(time.time())
            self.server = server
            self.timeout_seconds = 10

            self.request_data = None
            self.response_data = None

            self.state = self.S_REQUEST_PENDING
            self.status = 'UNRESOLVED'
            self.result = None

            self.quiet = False
            self.debug = False

        def __str__(self):
            return 'DnsQuery >>> fileno=%s, qname=%s, qtype=%s, state=%s' % (self.fileno(), self.qname, self.qtype, self.state)

        def state(self):
            return self.state

        def fileno(self):
            try:
                return self.sock.fileno() or -1
            except socket.error, e:
                return -1

        def is_request_pending(self):
            return self.state == self.S_REQUEST_PENDING

        def is_request_sent(self):
            return self.state == self.S_REQUEST_SENT

        def is_response_received(self):
            return self.state == self.S_RESPONSE_RECEIVED

        def check(self):
            return self.status, self.result

        def write_request(self):
            if not self.request_data:
                self.tid = random.randint(0,65535)
                opcode = DNS.Opcode.QUERY
                rd = self.rd = 1
                qname = self.qname
                qtype = self.qtype

                m = DNS.Lib.Mpacker()
                m.addHeader(self.tid,
                      0, opcode, 0, 0, rd, 0, 0, 0,
                      1, 0, 0, 0)
                m.addQuestion(qname, qtype, DNS.Class.IN)

                self.request_data = m.getbuf()

            ok, finished = False, False
            try:
                # TODO: validate amount written
                self.sock.send(self.request_data)
                ok = True
                finished = True
            except socket.error, e:
                if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    ok = True
                elif not self.quiet:
                    sys.stderr.write('failed on send [%s]: %s\n' % (self.qname, e))

            if finished:
                self.state = self.S_REQUEST_SENT

            if not ok:
                self.state = self.S_ERROR

        def read_response(self):
            finished, ok = False, False
            if not self.response_data:
                try:
                    (self.response_data, self.server_address) = self.sock.recvfrom(65535)
                    ok = True
                    finished = True
                except socket.error, e:
                    if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                        ok = True
                    else:
                        ok = False
            if ok and finished:
                u = DNS.Lib.Munpacker(self.response_data)
                # TODO: calculate elapsed
                self.result = DNS.Lib.DnsResult(u, {'name':self.qname, 'qtype':self.qtype, 'rd':self.rd, 'server':self.server})
                if self.result.header['id'] != self.tid:
                    # invalid
                    raise Exception('invalid DNS reponse received; tid=%s != tid=%s' % (self.result.header['id'], self.tid))

                if self.debug:
                    self.result.show()

                self.state = self.S_RESPONSE_RECEIVED

            if not ok:
                self.state = self.S_ERROR

        def set_error(self):
            self.state = self.S_ERROR

        def set_status(self, status):
            self.status = status
            
        def is_timeout(self, now):
            if self.start < (now - self.timeout_seconds):
                return True
            else:
                return False

        def is_error(self):
            return self.state == self.S_ERROR

        def cleanup(self):
            try:
                self.sock.close()
            except Exception, ex:
                if not self.quiet:
                    sys.stderr.write('ignoring error on cleanup: %s\n' % (traceback.formt_exc(ex)))

    def __init__(self):
        DNS.Base.ParseResolvConf()
        self.servers = DNS.Base.defaults['server']

        self.queries = {}
        self.quiet = False
        
    def submit(self, qname, qtype = DNS.Type.A, flags = 0):
        for server in self.servers:
            ok, sock = self.make_udp_socket(server, 53)
            if ok:
                query = DnsResolver.DnsQuery(sock, qname, qtype, flags, server)
                self.queries[query.fileno()] = query
                return query
        raise Exception('failed to connect to name server')

    def make_udp_socket(self, address, port):
        ok = False
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(0)
            sock.connect((address, port))
            ok = True
        except socket.error, e:
            if e.errno == errno.EINPROGRESS:
                ok = True
            else:
                if not self.quiet:
                    sys.stderr.write('failed on connect [%s:%d]: %s\n' % (ip_address, port, e))
        
        return ok, sock

    def handle(self, fileno, ltype):
        if not self.queries.has_key(fileno):
            return False
        try:
            query = self.queries[fileno]
            if 'x' == ltype:
                query.set_error()
            if query.is_request_pending() and 'w' == ltype:
                query.write_request()
            elif query.is_request_sent()  and 'r' == ltype:
                query.read_response()
            else:
                sys.stderr.write('bad state fo connection->[%s] state=[%s]' % (query.fileno(), query.state))
                pass
            
        except Exception, ex:
            sys.stderr.write('failed to handle with error: %s\n' %  (traceback.format_exc(ex)))

        return True

    def set_error(fileno):
        try:
            self.queries[fileno].set_error()
        except KeyError, e:
            pass
        
    def completed(self):
        completed = []

        now = int(time.time())
        for fileno, query in self.queries.iteritems():
            if query.is_error():
                sys.stderr.write('error on [%s] [%s %s]\n' % (query.qname, query.start, now))
                completed.append((fileno, 'ERROR'))
            elif query.is_timeout(now):
                sys.stderr.write('timeout on [%s] [%s %s]\n' % (query.qname, query.start, now))
                completed.append((fileno, 'TIMEOUT'))
            elif query.is_response_received():
                completed.append((fileno, 'OK'))

        completed_queries = []
        for fileno, status in completed:
            query = self.queries.pop(fileno)
            query.set_status(status)
            completed_queries.append(query)

        return completed_queries

    def established(self):
        established = []
        for fileno, query in self.queries.iteritems():
            if not query.is_response_received():
                established.append(fileno)

        return established

    def writeable(self):
        writeable = []
        for fileno, query in self.queries.iteritems():
            if query.is_request_pending():
                writeable.append(fileno)

        return writeable

    def readable(self):
        readable = []
        for fileno, query in self.queries.iteritems():
            if query.is_request_sent():
                readable.append(fileno)

        return readable

if '__main__' == __name__:
    import select

    resolver = DnsResolver()
    queries = {}
    for host in sys.argv[1:]:
        query = resolver.submit(host)
        queries[query] = host
    
    while len(queries) > 0:

        rlist = resolver.readable()
        wlist = resolver.writeable()
        xlist = resolver.established()

        rlist, wlist, xlist = select.select(rlist, wlist, xlist, 1)
#        print(rlist, wlist, xlist)

        for fileno in xlist:
            resolver.handle(fileno, 'x')
        for fileno in wlist:
            resolver.handle(fileno, 'w')
        for fileno in rlist:
            resolver.handle(fileno, 'r')

        for query in resolver.completed():
            hostname = queries.pop(query)
            status, result = query.check()
            print(status, result, hostname)
            for a in result.answers:
                print(a['type'], a['typename'], a['data'])

