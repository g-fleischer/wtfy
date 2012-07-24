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
import re
import gzip
import zlib
from urllib2 import urlparse

class HttpWriter():
    HTTP_VERSION = '1.1'
    def __init__(self, csock):
        self.csock = csock
        self.sent = False
        self.headers_prepared = False
        self.headers_sent = False
        self.body_prepared = False
        self.body_sent = False

    def send_request(self, method, resource, headers, body):
        finished, fatal_error = False, False
        try:
            self._send_request(method, resource, headers, body)
            finished = True
        except socket.error, e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                pass
            else:
                sys.stderr.write('warn: failed reading headers%s\n' % (e))
                finished = fatal_error = True
        except Exception, e:
            sys.stderr.write('error reading headers: %s' % (traceback.format_exc(e)))
            finished = fatal_error = True

        return finished, fatal_error

    def send_response(self, status, message, headers, body):
        finished, fatal_error = False, False
        try:
            self._send_response(status, message, headers, body)
            finished = True
        except socket.error, e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                pass
            else:
                sys.stderr.write('warn: failed reading headers%s\n' % (e))
                finished = fatal_error = True
        except Exception, e:
            sys.stderr.write('error reading headers: %s' % (traceback.format_exc(e)))
            finished = fatal_error = True

        return finished, fatal_error

    def _send_request(self, method, resource, headers, body):
        self._send_header((method, resource, self.HTTP_VERSION), headers, body, True)
        if body:
            self._send_body(body)

    def _send_response(self, status, message, headers, body):
        self._send_header((self.HTTP_VERSION, status, message), headers, body, False)
        if body:
            self._send_body(body)

    def _send_header(self, header_pieces, headers, body, is_request):

        if not self.headers_prepared:
            body_length = len(body)
            had_length = False
            had_host = False
            if is_request:
                resource = header_pieces[1]
                splitted = urlparse.urlsplit(resource)
                url = splitted.path
                if splitted.query:
                    url += '?' + splitted.query
                header_line = '%s %s HTTP/%s\r\n' % (header_pieces[0], url, header_pieces[2])
            else:
                header_line = 'HTTP/%s %s %s\r\n' % header_pieces

            io_request = StringIO()
            io_request.write(header_line)
            for name, value in headers.iteritems():
                if name == 'content-length':
                    io_request.write('%s: %s\r\n' % (name.title(), body_length))
                    had_length = True
                else:
                    io_request.write('%s: %s\r\n' % (name.title(), value))
                if name == 'host':
                    had_host = True

            if not had_length and body_length > 0:
                io_request.write('%s: %s\r\n' % ('Content-Length', body_length))

            if not had_host and is_request:
                splitted = urlparse.urlsplit(resource)
                io_request.write('%s: %s\r\n' % ('Host', splitted.hostname))

            io_request.write('\r\n')
            self.buffer = io_request.getvalue()
            io_request.close()
            self.headers_prepared = True
            self.to_write = len(self.buffer)
            self.written = 0

        if not self.headers_sent:
            while self.to_write > 0:
                written = self.csock.send(self.buffer[self.written:])
                self.written += written
                self.to_write -= written

            self.headers_sent = True

    def _send_body(self, body):

        # TODO: won't work for streaming content...
        if not self.body_prepared:
            self.to_write = len(body)
            self.written = 0
            self.body_prepared = True
                                
        if not self.body_sent:
            while self.to_write > 0:
                written = self.csock.send(body[self.written:])
                self.written += written
                self.to_write -= written

            self.body_sent = True

    
