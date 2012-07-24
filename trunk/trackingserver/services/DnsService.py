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
import struct

import tornado.netutil
from tornado.ioloop import IOLoop

class DnsService(object):
    def __init__(self, framework):
        self.framework = framework
        self.external_ip = self.get_ip(self.framework.get_config("external_ip"))

    def get_ip(self, ip_address):
        ip = 0
        the_ip = ip_address.split('.')
        for i in range(0, 4):
            n = int(the_ip[i])
            ip = (ip << 8) + n
        return ip

    def process_dns_request(self, data):
        # https://www.ietf.org/rfc/rfc1035.txt
        query = DNS.Lib.Munpacker(data)
        header = query.getHeader()
        (qid, qr, opcode, aa, tc, rd, ra, z, rcode,
                  qdcount, ancount, nscount, arcount) = header
        # TODO: should check qdcount?
        question = query.getQuestion()
        (qname, qtype, qclass) = question
        self.framework.debug('DnsService', 'header', header)
        self.framework.debug('DnsService', 'question', question)
        response = DNS.Lib.Mpacker()
        if DNS.Type.A == qtype and DNS.Opcode.QUERY == opcode:
            qr = 1
            aa = 1
            ra = 0
            z = 0
            rcode = DNS.Status.NOERROR
            ancount = 1
            nscount = 0
            arcount = 0
            response.addHeader(qid, qr, opcode, aa, tc, rd, ra, z, rcode, qdcount, ancount, nscount, arcount)
            response.addQuestion(qname, qtype, qclass)
            response.addRRheader(qname, DNS.Type.A, DNS.Class.IN, 1)
            response.addbytes(struct.pack('!L', self.external_ip))
            response.endRR()
        else:
            # unsupported
            qr = 1
            aa = 1
            ra = 0
            z = 0
            rcode = DNS.Status.REFUSED
            ancount = 1
            nscount = 0
            arcount = 0
            response.addHeader(qid, qr, opcode, aa, tc, rd, ra, z, rcode, qdcount, ancount, nscount, arcount)
            response.addQuestion(qname, qtype, qclass)

        return response.getbuf()

class DnsTcpServer(DnsService, tornado.netutil.TCPServer):
    def __init__(self, framework):
        tornado.netutil.TCPServer.__init__(self)
        DnsService.__init__(self, framework)
        self.framework = framework

    def handle_stream(self, stream, address):
        # TCP server
        self.framework.debug('DnsService', stream, address)
        self.stream = stream
        self.stream.read_bytes(2, self.on_header_read)

    def on_header_read(self, data):
        count = DNS.Lib.unpack16bit(data)
        self.framework.debug('DnsService', 'count', count)
        self.stream.read_bytes(count, self.on_content_read)

    def on_content_read(self, data):
        buf = self.process_dns_request(data)
        data = DNS.Lib.pack16bit(len(buf)) + buf
        self.stream.write(data, self.on_response_sent)

    def on_response_sent(self):
        self.framework.debug('DnsService', 'response sent')
        self.stream.close()

class DnsUdpServer(DnsService):
    def __init__(self, framework):
        DnsService.__init__(self, framework)
        self.framework = framework
        self.sockets = {}

    def add_sockets(self, sockets):
        self.io_loop = IOLoop.instance()
        for sock in sockets:
            fd = sock.fileno()
            self.sockets[fd] = sock
            self.io_loop.add_handler(fd, self.accept_handler, IOLoop.READ)

    def add_socket(self, sock):
        self.add_sockets([sock])

    def accept_handler(self, fd, events):
        self.framework.debug('DnsService', 'udp', fd, events)
        # TODO: implement non-blocking read/write
        sock = self.sockets[fd]
        data, address = sock.recvfrom(512)
        self.framework.debug('DnsService', 'got', address, data)
        buf = self.process_dns_request(data)
        self.framework.debug('DnsService', 'sending', len(buf), buf)
        sock.sendto(buf, address)

