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
from cStringIO import StringIO
import hashlib

class XmlSocketService(tornado.netutil.TCPServer):
    def __init__(self, framework):
        tornado.netutil.TCPServer.__init__(self)
        self.framework = framework

    class XmlSocketClient(object):
        POLICY_REQUEST = '<policy-file-request/>'
        def __init__(self, framework, stream, address):
            self.framework = framework
            self.stream = stream
            self.address = address
            self.dataIO = StringIO()
            self.stream.read_until_close(self.on_close, self.on_streaming_read)
        
        def on_close(self, data):
            self.framework.debug('XmlSocketClient', 'on_close')

        def on_streaming_read(self, data):
            self.framework.debug('XmlSocketClient', 'on_streaming_read')
            # TODO: enforce maximum
            self.dataIO.write(data)
            if '\0' in data:
                # have complete request
                self.process_request()

        def process_request(self):
            try:
                data = self.dataIO.getvalue()
                self.dataIO.close()
                self.framework.debug('XmlSocketClient', 'process_request', data)
                request = data.strip('\0')
                if self.POLICY_REQUEST == request:
                    self.stream.write(self.get_policy(), self.on_write_complete)
                else:
                    self.framework.process_results(self.address, request)

            except Exception, ex:
                self.framework.log_exception(ex)

            self.stream.write('<x/>\0', self.on_write_complete)

        def on_write_complete(self):
            self.stream.close()

        def get_policy(self):
            return self.framework.get_flash_crossdomain_policy()

    def handle_stream(self, stream, address):
        self.framework.debug('XmlSocketService', 'got stream', stream, address)
        XmlSocketService.XmlSocketClient(self.framework, stream, address)

#        self.clients.append(self.FakeHttpsClient(self.framework, stream, address))
