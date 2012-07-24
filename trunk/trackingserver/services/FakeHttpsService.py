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
import tornado.netutil
import struct
import time

class FakeHttpsService(tornado.netutil.TCPServer):

    class FakeHttpsClient(object):
        def __init__(self, framework, stream, address):
            self.framework = framework
            self.stream = stream
            self.address = address
            self.first = True
            self.buf = ''
            self.stream.read_until_close(self.on_client_hello_complete, self.on_streaming_read)

        def on_client_hello_complete(self, data):
            self.framework.debug('FakeHttpsClient', 'client hello', data)
            if not data:
                return
            data = self.buf
            message_type = ord(data[0])
            if 22 == message_type:
                # handshake
                fields = struct.unpack("!BBBH",data[0:5])
                major = fields[1]
                minor = fields[2]
                length = fields[3]
                # TODO: complete implementation
                self.framework.debug('FakeHttpsClient','handshake', message_type, major, minor, length)

            elif 128 == message_type:
                # handshake v2
                fields = struct.unpack("!BBBBB",data[0:5])
                length = fields[1]
                htype = fields[2]
                major = fields[3]
                minor = fields[4]
                # TODO: complete implementation
                self.framework.debug('FakeHttpsClient','handshake v2', message_type, length, htype, major, minor)

            self.stream.close()

        def on_streaming_read(self, data):
            self.framework.debug('FakeHttpsClient', 'on_streaming_read', data)
            finished = False
            if self.first and len(data) > 5:
                message_type = ord(data[0])
                if 22 == message_type:
                    # handshake
                    finished = self.decode_handshake(data)
                elif 128 == message_type:
                    # handshake v2
                    finished = self.decode_v2_handshake(data)
                else:
                    # unknown/unsupported
                    finished = True

            if finished:
                self.stream.close()
            else:
                self.first = False

        def on_write_complete(self):
            self.stream.close()

        def decode_handshake(self, buf):
            finished = True
            fields = struct.unpack("!BBBH",buf[0:5])
            print "handshake"
            message_type = fields[0]
            major = fields[1]
            minor = fields[2]
            length = fields[3]
            self.framework.debug('FakeHttpsClient','handshake', message_type, major, minor, length)
            rest = buf[5:]
            if len(rest) < length or length < 38:
                # TODO: figure out how to resume
                return False
            else:
                htype = ord(rest[0])
                hlen = (ord(rest[1])<<16) + (ord(rest[2])<<8) + ord(rest[3])
                print "htype=%d, hlen=%d" % (htype, hlen)
                if htype == 1:
                    print "client hello"
                    hfields = struct.unpack("!BBL28c", rest[4:38])
                    print "client version: %d.%d" % (hfields[0],hfields[1])
                    dt = time.gmtime(hfields[2])
                    print "date/time: %s" % (time.asctime(dt))
                    idlen = ord(rest[38])
                    print "session id len: %d" % (idlen)
                    if idlen > 0:
                        rest = rest[39+idlen]
                    else:
                        rest = rest[39:]
                    cslen = struct.unpack("!H", rest[0:2])[0]
                    print "cipher suite len: %d" % (cslen)
                    rest = rest[2:]
                    fmt = "!%dH" % (cslen/2)
                    offset = cslen
                    ciphersuites = struct.unpack(fmt, rest[0:offset])
                    for cs in ciphersuites:
                        print "%04X" % cs
                    rest = rest[offset:]
                    cmlen = struct.unpack("!B", rest[0:1])[0]
                    print "compression method len: %d" % (cmlen)
                    rest = rest[1:]
                    fmt = "!%dB" % (cmlen)
                    offset = cmlen
                    compressionmethods = struct.unpack(fmt, rest[0:offset])
                    for cm in compressionmethods:
                        print "%02X" % cm
                    rest = rest[offset:]
                    if len(rest) > 0:
                        # extensions
                        exlen = struct.unpack("!H", rest[0:2])[0]
                        print "extensions length: %d of %d" % (exlen, len(rest[2:]))
                        rest = rest[2:]
                        remaining = exlen
                        while remaining > 0:
                            extype, edlen = struct.unpack("!HH", rest[0:4])
                            remaining -= 4
                            rest = rest[4:]
                            print "extension: %02X; elen %d" % (extype, edlen)
                            if 0 == extype:
                                # server name list
                                snlen, nametype, hnamelen = struct.unpack("!HBH", rest[0:5])
                                print "snlen: %d, name type: %d, hnamelen: %d" % (snlen, nametype, hnamelen)
                                # not accounting for multiple servernames
                                # may be a problem with UTF8 ...
                                hname = rest[5:hnamelen+5]
                                print "hostname: %s" % (hname)
                            else:
                                pass

                            remaining -= edlen
                            rest = rest[edlen:]

            return finished

        def decode_v2_handshake(self, buf):
            finished = False
            fields = struct.unpack("!BBBBB",buf[0:5])
            print "handshake v2"
            message_type = fields[0]
            length = fields[1]
            htype = fields[2]
            major = fields[3]
            minor = fields[4]
            self.framework.debug('FakeHttpsClient','handshake v2', message_type, length, htype, major, minor)
            rest = buf[5:]
            if len(rest) > 6:
                fields = struct.unpack("!HHH", rest[0:6])
                cipherlen = fields[0]
                sessionidlen = fields[1]
                challengelen = fields[2]
                print "cl=%d, sl=%d, challengelen=%d" % (cipherlen, sessionidlen, challengelen)
                rest = rest[6:]
                if len(rest) >= cipherlen + sessionidlen + challengelen:
                    finished = True
                if cipherlen > 0:
                    for c in range(0,cipherlen/3):
                        print "%02x%02x%02x" % (ord(rest[c*3]),ord(rest[c*3+1]),ord(rest[c*3+2]))
                    rest = rest[cipherlen:]
                if sessionidlen > 0:
                    sessionid = rest[0:sessionidlen]
                    rest = rest[sessionidlen:]
                if challengelen > 0:
                    challenge = rest[0:challengelen]
                    rest = rest[challengelen:]
                print('rest', rest, len(rest))
            return finished

    def __init__(self, framework):
        tornado.netutil.TCPServer.__init__(self)
        self.framework = framework
#        self.framework.debug('FakeHttpsService', 'init')
        self.clients = []

    def handle_stream(self, stream, address):
        self.framework.debug('FakeHttpsService', 'got stream', stream, address)
        self.clients.append(self.FakeHttpsClient(self.framework, stream, address))
