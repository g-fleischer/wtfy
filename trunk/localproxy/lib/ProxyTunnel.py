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
from cStringIO import StringIO
import sys
import traceback
import socket
import errno

class ProxyTunnel():

    READ_SIZE = 4096

    def __init__(self, rsock, wsock):
        self.rsock = rsock
        self.wsock = wsock
        self.buffer = ''
        self.to_write = 0
        self.written = 0

    def read(self):
        finished, fatal_error = False, False
        try:
            if self.written > 0:
                self.buffer = self.buffer[self.written:]
                self.to_write = len(self.buffer)
                self.written = 0

            while True:
                tmp = self.rsock.recv(self.READ_SIZE)
                if not tmp:
                    break
#                print('-->', tmp)
                self.buffer += tmp
                self.to_write += len(tmp)

        except socket.error, e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                pass
            else:
                sys.stderr.write('warn: failed reading: %s\n' % (e))
                finished = fatal_error = True
        except Exception, e:
            sys.stderr.write('error reading: %s' % (traceback.format_exc(e)))
            finished = fatal_error = True

        return finished, fatal_error

    def need_write(self):
        return self.to_write > 0

    def write(self):
        finished, fatal_error = False, False
        try:
            while self.to_write > 0:
#                print('<--', self.to_write, self.buffer[self.written:])
                written = self.wsock.send(self.buffer[self.written:])
                self.to_write -= written
                self.written += written
        except socket.error, e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                pass
            else:
                sys.stderr.write('warn: failed reading: %s\n' % (e))
                finished = fatal_error = True
        except Exception, e:
            sys.stderr.write('error reading: %s' % (traceback.format_exc(e)))
            finished = fatal_error = True

        return finished, fatal_error

