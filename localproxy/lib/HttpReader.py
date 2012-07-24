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

class HttpReader():

    READ_SIZE = 4096
    re_request_line = re.compile(r'^(\S+)\s+((?:https?://(?:\S+\.)+\w+(?::\d+)?)?/.*)\s+HTTP/\d+\.\d+\s*$', re.I)
    re_status_line = re.compile(r'^HTTP/\d\.\d\s+\d{3}(?:\s+.*)?$')

    def __init__(self, csock):
        self.csock = csock
        self.buffer = ''
        self.previous = 0
        self.has_read_headers = False
        self.has_read_body = False
        self.http_headers = ''
        self.http_body = ''

        self.parsed_headers = None
        self.parsed_headers = None
        self.has_body = False

        self.content_length = -1
        self.proxy_close_connection = False
        self.close_connection = False
        self.chunked_encoding = False
        self.content_encoding = ''
        self.content_type = ''

        self.body_io = None
        self.bytes_read = 0
        self.keep_reading = False
        self.chunksize = None
        
    def headers_available(self):
        return self.has_read_headers

    def body_available(self):
        return self.has_read_body

    def headers(self):
        return self.http_headers

    def body(self):
        return self.http_body

    def read_request_headers(self):
        finished, fatal_error = False, False
        try:
            self._read_headers()
            if self.has_read_headers:
                self.extract_request_headers()
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

    def read_response_headers(self):
        finished, fatal_error = False, False
        try:
            self._read_headers()
            if self.has_read_headers:
                self.extract_response_headers()
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

    def _read_headers(self):
        while not self.has_read_headers:
            n = self.buffer.find('\n', self.previous)
            if n < 0:
                tmp = self.csock.recv(self.READ_SIZE)
                if not tmp:
                    break
                self.buffer += tmp
                continue
            if n > 0 and self.buffer[n-1] == '\r':
                header = self.buffer[self.previous:n-1]
            else:
                header = self.buffer[self.previous:n]
        
            if 0 == len(header):
                # found end of headers
                self.has_read_headers = True
                self.previous = n + 1
                self.http_headers = self.buffer[0:self.previous]
                break

            self.previous = n + 1

    def extract_request_headers(self):
        if not self.has_read_headers:
            raise Exception('no headers available to process')

        if self.parsed_headers:
            return self.parsed_headers

        first = True
        method, resource, version = '', '' ,''
        last_name = ''
        headers_dict = {}
        for line in self.http_headers.splitlines():
            line = line.replace('\r', '')
            if not line:
                break
            elif first:
                if line.count(' ') > 1:
                    method, resource, version = line.split(' ', 2)
                    first = False
                else:
                    m = self.re_request_line.match(line)
                    if m:
                        method, resource, version = m.group(1), m.group(2), m.group(3)
                        first = False
            elif line[0] in (' ', '\t'):
                if last_name:
                    headers_dict[last_name] += ' ' + line.strip()
            elif ':' in line:
                name, value = line.split(':', 1)
                lname = name.lower()
                value = value.strip()
                if headers_dict.has_key(lname):
                    tmp = headers_dict[lname]
                    if str == type(tmp):
                        headers_dict[lname] = [tmp, value]
                    else:
                        headers_dict[lname].append(value)
                else:
                    headers_dict[lname] = value

                last_name = lname

                lvalue = value.lower()
                if 'connection' == lname:
                    if 'close' == lvalue:
                        self.close_connection = True
                elif 'proxy-connection' == lname:
                    if 'close' == lvalue:
                        self.proxy_close_connection = True
                elif 'content-length' == lname:
                    try:
                        self.content_length = int(lvalue)
                    except ValueError:
                        pass
                elif 'transfer-encoding' == lname:
                    if lvalue and 'identity' != lvalue:
                        self.chunked_encoding = True
                elif 'content-encoding' == lname:
                    self.content_encoding = lvalue
                elif 'content-type' == lname:
                    self.content_type = lname
                    
        self.parsed_headers = (method, resource, version, headers_dict)
        return self.parsed_headers

    def extract_response_headers(self):
        if not self.has_read_headers:
            raise Exception('no headers available to process')

        if self.parsed_headers:
            return self.parsed_headers

        first = True
        version, status, reason = '', '' ,''
        last_name = ''
        headers_dict = {}
        for line in self.http_headers.splitlines():
            line = line.replace('\r', '')
            if not line:
                break
            elif first:
                if line.count(' ') > 1:
                    version, status, reason = line.split(' ', 2)
                    first = False
                else:
                    m = self.re_status_line.match(line)
                    if m:
                        version, status, reason = m.group(1), m.group(2), m.group(3)
                        first = False
            elif line[0] in (' ', '\t'):
                if last_name:
                    headers_dict[last_name] += ' ' + line.strip()
            elif ':' in line:
                name, value = line.split(':', 1)
                lname = name.lower()
                value = value.strip()
                if headers_dict.has_key(lname):
                    tmp = headers_dict[lname]
                    if str == type(tmp):
                        headers_dict[lname] = [tmp, value]
                    else:
                        headers_dict[lname].append(value)
                else:
                    headers_dict[lname] = value

                last_name = lname

                lvalue = value.lower()
                if 'connection' == lname:
                    if 'close' == lvalue:
                        self.close_connection = True
                elif 'proxy-connection' == lname:
                    if 'close' == lvalue:
                        self.proxy_close_connection = True
                elif 'content-length' == lname:
                    try:
                        self.content_length = int(lvalue)
                    except ValueError:
                        pass
                elif 'transfer-encoding' == lname:
                    if lvalue and 'identity' != lvalue:
                        self.chunked_encoding = True
                elif 'content-encoding' == lname:
                    self.content_encoding = lvalue
                elif 'content-type' == lname:
                    self.content_type = lname

        self.parsed_headers = (version, status, reason, headers_dict)
        return self.parsed_headers
        
    def read_request_body(self):
        finished, fatal_error = False, False
        try:
            self._read_request_body()
            finished = True
        except socket.error, e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                pass
            else:
                sys.stderr.write('warn: failed reading headers%s\n' % (e))
                finished = fatal_error = True
        except Exception, e:
            sys.stderr.write('error reading headerse: %s' % (traceback.format_exc(e)))
            finished = fatal_error = True

        return finished, fatal_error

    def read_response_body(self, method):
        finished, fatal_error = False, False
        try:
            self._read_response_body(method)
            finished = True
        except socket.error, e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                pass
            else:
                sys.stderr.write('warn: failed reading headers%s\n' % (e))
                finished = fatal_error = True
        except Exception, e:
            sys.stderr.write('error reading headerse: %s' % (traceback.format_exc(e)))
            finished = fatal_error = True

        return finished, fatal_error

    def _read_request_body(self):
        if self.has_read_body:
            return

        (method, resource, version, headers) = self.extract_request_headers()
        if method in ('HEAD', 'GET','CONNECT',):
            self.http_body = ''
            self.has_read_body = True
            return

        if method in ('OPTIONS',) and headers.get('content-length') is None and headers.get('transfer-encoding') is None:
            self.http_body = ''
            self.has_read_body = True
            return

        self._read_body()

    def _read_response_body(self, method):

        if self.has_read_body:
            return

        (version, status, reason, headers) = self.extract_response_headers()
        if method in ('HEAD',) or str(status) in ('304',):
            self.http_body = ''
            self.has_read_body = True
            return

        if method in ('OPTIONS',) and headers.get('content-length') is None and headers.get('transfer-encoding') is None:
            self.http_body = ''
            self.has_read_body = True
            headers['content-length'] = '0'
            return

        self._read_body()

    def _read_body(self):

        if not self.has_body:
            if not self.body_io:
                self.body_io = StringIO()
                self.bytes_read = 0

            if self.chunked_encoding:
                # read chunked encoding
                self._read_chunked()
            elif self.content_length > -1:
                # read length
                self._read_bytes()
            else:
                self._read_until_end()
                self.close_connection = True
                self.proxy_close_connection = True

            self.has_body = True

        if self.has_body:
            if self.content_encoding:
                if self.content_encoding in ('gzip', 'x-gzip'):
                    self.body_io.seek(0, 0)
                    gz = gzip.GzipFile(None, 'rb', None, self.body_io)
                    self.http_body = gz.read()
                    gz.close()
                elif self.content_encoding in ('deflate', 'x-deflate', 'compress', 'x-compress'):
                    self.http_body = zlib.decompress(self.body_io.getvalue(), -15)
                else:
                    sys.stderr.write('warning: unhandled content_encoding=%s\n' % (self.content_encoding))
                    self.http_body = self.body_io.getvalue()

                self.content_length = len(self.http_body)
            else:
                self.http_body = self.body_io.getvalue()

            self.body_io.close()
            self.has_read_body = True

    def _read_chunked(self):
        self.keep_reading = True
        while self.keep_reading:
            if self.chunksize is None:
                n = self.buffer.find('\n', self.previous)
                if n < 0:
                    tmp = self.csock.recv(self.READ_SIZE)
                    if not tmp:
                        # closed ?
                        raise Exception('failure receiving chunked data when looking for chunksize\n')
                    self.buffer += tmp
                    continue
                self.chunksize = self.buffer[self.previous:n].rstrip()
                self.previous = n + 1
                self.to_read = 0

            if not self.to_read and self.chunksize:
                try:
                    self.to_read = int(self.chunksize, 16)
                except ValueError, e:
                    raise Exception('failure reading chunksize: [%s]: %s\n' %(self.chunksize, e))

            if 0 == self.to_read:
                self.chunksize = None
                self.keep_reading = False
                break

            while self.to_read > 0:
                if self.to_read < (len(self.buffer)-self.previous):
                    self.body_io.write(self.buffer[self.previous:self.previos+self.to_read])
                    self.previous += self.to_read
                    self.to_read = 0
                else:
                    tmp = self.buffer[self.previous:]
                    self.body_io.write(tmp)
                    self.to_read -= len(tmp)
                    self.buffer = ''
                    self.previous = 0
                    self.buffer = self.csock.recv(self.READ_SIZE)
                    if not self.buffer:
                        raise Exception('failure receiving chunked data\n')
                        self.keep_reading = False
                        break

            self.previos += 2 # for CRLF
            self.chunksize = None

    def _read_bytes(self):
        self.to_read = self.content_length - self.bytes_read
        if self.to_read <= 0:
            return

        if self.buffer:
            exists = len(self.buffer) - self.previous

            if self.to_read < exists:
                self.body_io.write(self.buffer[self.previous:self.previous+self.to_read])
                self.buffer = self.buffer[self.previous+self.to_read:]
                self.bytes_read = self.to_read
                self.to_read = 0
                return
            else:
                self.body_io.write(self.buffer[self.previous:])
                self.buffer = ''
                self.bytes_read = exists
                self.to_read = self.content_length - self.bytes_read
                
        while self.to_read > 0:
            self.buffer = self.csock.recv(min(self.READ_SIZE, self.to_read))
            rlen = len(self.buffer)
            self.body_io.write(self.buffer)
            self.to_read -= rlen
            self.bytes_read += rlen
            self.buffer = ''

    def _read_until_end(self):
        if self.buffer:
            self.buffer = self.buffer[self.previous:]
            self.body_io.write(self.buffer)
            self.buffer = ''
            self.previous = 0
      
        self.buffer = self.csock.recv(self.READ_SIZE)
        while self.buffer:
            self.body_io.write(self.buffer)
            self.buffer = ''
            self.buffer = self.csock.recv(self.READ_SIZE)

