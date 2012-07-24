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
import struct
import socket
import select
import DNS
import re
NOLINGER = struct.pack('ii', 1, 0)

import tornado.netutil
from tornado.ioloop import IOLoop

class GlueDNS(object):

    def __init__(self, domain, ip_address):
        self.domain = domain
        self.ip_address = ip_address
        ip = map(int, ip_address.split('.'))
        self.DOMAIN_IP = (ip[0] << 24) + (ip[1] << 16) + (ip[2] << 8) + ip[3]
        self.RE_NAME_SERVER = re.compile(r'^ns\d\.' + re.escape(domain) + '$')
        self.RE_HEX_IP = re.compile(r'^(.+?\.)?([0-9a-fA-F]{8})\.' + re.escape(domain) + '$')

    def make_tcp_socket(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.bind(('', port))
        sock.listen(128)
        return sock

    def make_udp_socket(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))
        return sock

    def make_tcp_server(self):
        return DnsTcpServer(self)

    def make_udp_server(self):
        return DnsUdpServer(self)

    def process_dns_request(self, data):
        # https://www.ietf.org/rfc/rfc1035.txt
        query = DNS.Lib.Munpacker(data)
        header = query.getHeader()
        (qid, qr, opcode, aa, tc, rd, ra, z, rcode,
                  qdcount, ancount, nscount, arcount) = header
        # TODO: should check qdcount?
        question = query.getQuestion()
        (qname, qtype, qclass) = question
        print('header', header)
        print('question', question)
        response = DNS.Lib.Mpacker()
        valid = False
        
        m = self.RE_HEX_IP.match(qname)
        if m:

            extra = m.group(1)
            name_ip = m.group(2)

            ip = 0
            for i in range(0, 4):
                n = int(name_ip[i*2:i*2+2], 16)
                ip = (ip << 8) + n

            nsname = 'ns.' + name_ip + '.' + self.domain

            if qtype in (DNS.Type.A, DNS.Type.ANY) and DNS.Opcode.QUERY == opcode:
                
                print('A', extra, name_ip, nsname, ip)

                qr = 1
                aa = 1
                ra = 0
                z = 0
                rcode = DNS.Status.NOERROR
                if 'ns.' == extra:
                    ancount = 1
                    nscount = 0
                    arcount = 0
                    response.addHeader(qid, qr, opcode, aa, tc, rd, ra, z, rcode, qdcount, ancount, nscount, arcount)
                    response.addQuestion(qname, qtype, qclass)
                    response.addRRheader(qname, DNS.Type.A, DNS.Class.IN, 1)
                    response.addbytes(struct.pack('!L', ip))
                    response.endRR()
                else:
                    ancount = 0
                    nscount = 1
                    arcount = 1
                    response.addHeader(qid, qr, opcode, aa, tc, rd, ra, z, rcode, qdcount, ancount, nscount, arcount)
                    response.addQuestion(qname, qtype, qclass)
                    # return NS answer
                    response.addRRheader(qname, DNS.Type.NS, DNS.Class.IN, 1)
                    response.addname(nsname)
                    response.endRR()
                    # return NS answer glue record
                    response.addRRheader(nsname, DNS.Type.A, DNS.Class.IN, 1)
                    response.addbytes(struct.pack('!L', ip))
                    response.endRR()

                valid = True

            elif DNS.Type.NS == qtype and DNS.Opcode.QUERY == opcode:

                print('NS', extra, name_ip, nsname, ip)

                qr = 1
                aa = 1
                ra = 0
                z = 0
                rcode = DNS.Status.NOERROR
                ancount = 1
                nscount = 0
                arcount = 1
                response.addHeader(qid, qr, opcode, aa, tc, rd, ra, z, rcode, qdcount, ancount, nscount, arcount)
                response.addQuestion(qname, qtype, qclass)
                # return NS answer
                response.addRRheader(qname, DNS.Type.NS, DNS.Class.IN, 1)
                response.addname(nsname)
                response.endRR()
                # return NS answer glue record
                response.addRRheader(nsname, DNS.Type.A, DNS.Class.IN, 1)
                response.addbytes(struct.pack('!L', ip))
                response.endRR()

                valid = True
        else:
            #### NAMESERVER
            m = self.RE_NAME_SERVER.match(qname)
            if m and qtype in (DNS.Type.A, DNS.Type.ANY) and DNS.Opcode.QUERY == opcode:
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
                # return A answer
                response.addRRheader(qname, DNS.Type.A, DNS.Class.IN, 1)
                response.addbytes(struct.pack('!L', self.DOMAIN_IP))
                response.endRR()
                valid = True

        if not valid:
            if qtype in (DNS.Type.A, DNS.Type.AAAA, DNS.Type.ANY) and DNS.Opcode.QUERY == opcode:
                qr = 1
                aa = 0
                ra = 0
                z = 0
                rcode = DNS.Status.NXDOMAIN
                ancount = 0
                nscount = 0
                arcount = 0
                response.addHeader(qid, qr, opcode, aa, tc, rd, ra, z, rcode, qdcount, ancount, nscount, arcount)
                response.addQuestion(qname, qtype, qclass)
            else:
                # unsupported
                qr = 1
                aa = 1
                ra = 0
                z = 0
                rcode = DNS.Status.REFUSED
                ancount = 0
                nscount = 0
                arcount = 0
                response.addHeader(qid, qr, opcode, aa, tc, rd, ra, z, rcode, qdcount, ancount, nscount, arcount)
                response.addQuestion(qname, qtype, qclass)

        return response.getbuf()

class DnsTcpServer(tornado.netutil.TCPServer):
    def __init__(self, gluedns):
        tornado.netutil.TCPServer.__init__(self)
        self.gluedns = gluedns

    def handle_stream(self, stream, address):
        # TCP server
        ###print(stream, address)
        self.stream = stream
        self.stream.read_bytes(2, self.on_header_read)

    def on_header_read(self, data):
        count = DNS.Lib.unpack16bit(data)
        ###print('count', count)
        self.stream.read_bytes(count, self.on_content_read)

    def on_content_read(self, data):
        buf = self.gluedns.process_dns_request(data)
        data = DNS.Lib.pack16bit(len(buf)) + buf
        self.stream.write(data, self.on_response_sent)

    def on_response_sent(self):
        ###print('response sent')
        self.stream.close()

class DnsUdpServer(object):
    def __init__(self, gluedns):
        self.gluedns = gluedns

    def add_socket(self, sock):
        self.sock = sock
        self.io_loop = IOLoop.instance()
        self.io_loop.add_handler(sock.fileno(), self.accept_handler, IOLoop.READ)

    def accept_handler(self, fd, events):
        ###print('udp', fd, events)
        # TODO: implement non-blocking read/write
        data, address = self.sock.recvfrom(512)
        ###print('got', address, data)
        buf = self.gluedns.process_dns_request(data)
        ###print('sending', len(buf), buf)
        self.sock.sendto(buf, address)

if '__main__' == __name__:
    import sys
    domain = sys.argv[1]
    ip_address = sys.argv[2]

    gluedns = GlueDNS(domain, ip_address)

    tcp_sockets = [gluedns.make_tcp_socket(53)]
    tcp_server = gluedns.make_tcp_server()
    tcp_server.add_sockets(tcp_sockets)

    udp_socket = gluedns.make_udp_socket(53)
    udp_server = gluedns.make_udp_server()
    udp_server.add_socket(udp_socket)

    IOLoop.instance().start()
