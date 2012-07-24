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

class FlashPolicyService(tornado.netutil.TCPServer):
    POLICY_REQUEST = '<policy-file-request/>'
    def __init__(self, framework):
        tornado.netutil.TCPServer.__init__(self)
        self.framework = framework

    def handle_stream(self, stream, address):
        self.framework.debug('FlashPolicyService', 'got stream', stream, address)
        self.stream = stream
        self.stream.read_bytes(len(self.POLICY_REQUEST)+1, self.on_read_complete)

    def on_read_complete(self, data):
        self.framework.debug('FlashPolicyService', 'FlashData data', data)
        request = data.strip('\0')
        if self.POLICY_REQUEST == request:
            self.stream.write(self.get_policy(), self.on_write_complete)
        else:
            # TODO: report error
            self.stream.close()

    def on_write_complete(self):
        self.stream.close()

    def get_policy(self):
        return self.framework.get_flash_crossdomain_policy()
