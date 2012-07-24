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
import tornado
import tornado.netutil
import socket

class FtpService(tornado.netutil.TCPServer):
    class FtpDataServer(tornado.netutil.TCPServer):
        def __init__(self, framework, ftp_client):
            tornado.netutil.TCPServer.__init__(self)
            self.framework = framework
            self.ftp_client = ftp_client

        def handle_stream(self, stream, address):
            self.framework.debug('FtpService', 'data', stream.socket.fileno(), address)

    class FtpClient(tornado.netutil.TCPServer):
        def __init__(self, framework, server, stream, address):
            tornado.netutil.TCPServer.__init__(self)
            self.framework = framework
            self.server = server
            self.stream = stream
            self.client_address = address
#            self.stream.write('220 OK\r\n530 Please login with USER and PASS.\r\n', self.on_response_sent)
#            self.stream.write('220 Welcome FTP\r\n321 Password Required. Send email address\r\n', self.on_response_sent)
            self.stream.write('220 Welcome FTP\r\n', self.on_response_sent)
            self.curdir = '/'
            self.data_channel = None
            self.data_cmd = ''
            self.data_content = ''

        def handle_stream(self, stream, address):
            self.framework.debug('FtpService','data channel', stream.socket.fileno(), address)
            if self.data_channel:
                self.data_channel.close()
            self.data_channel = stream

        def on_response_sent(self):
            self.stream.read_until('\r\n', self.on_request)

        def on_data_sent(self):
            self.framework.debug('FtpService','data was sent')
            self.stream.write('226 Transfer Complete\r\n', self.on_response_sent)
            self.data_channel.close()
            self.data_channel = None

        def on_request(self, data):
            self.framework.debug('FtpService','got data', data)
            cmd = data.strip()
            content = ''
            if ' ' in cmd:
                cmd, content = cmd.split(' ', 1)
            if 'QUIT' == cmd:
                self.stream.write('221 Goodbye\r\n', self.close_connection)
            elif 'SYST' == cmd:
                self.stream.write('214 UNIX Type: L8\r\n', self.on_response_sent)
            elif 'PWD' == cmd:
                self.stream.write('257 \"%s\" is current directory.\r\n' % (self.curdir), self.on_response_sent)
            elif 'PASS' == cmd:
                self.stream.write('230 Login Okay\r\n', self.on_response_sent)
            elif 'USER' == cmd:
                if 'anonymous' == content.lower():
                    self.stream.write('331 Password Required. Send email address\r\n', self.on_response_sent)
                else:
                    self.stream.write('230 Login Okay\r\n', self.on_response_sent)
            elif 'TYPE' == cmd and content.startswith('I'):
                self.stream.write('200 Type set to I\r\n', self.on_response_sent)
            elif 'TYPE' == cmd and content.startswith('A'):
                self.stream.write('200 Type set to A\r\n', self.on_response_sent)
            elif 'HELP' == cmd:
                self.stream.write('214-Commands supported:\r\nPASV PWD FEAT SYST CWD LIST\r\nRETR MDTM SIZE HELP QUIT\r\n214 Help OK\r\n', self.on_response_sent)
            elif 'FEAT' == cmd:
                self.stream.write('211-Extensions supported:\r\n MDTM\r\n SIZE\r\n211 End\r\n', self.on_response_sent)
            elif 'PORT' == cmd:
                # TODO: crap
                p = content.split(',')
                s = self.framework.make_socket(socket.AF_INET, socket.SOCK_STREAM, 0)
                if self.data_channel:
                    self.data_channel.close()
                self.data_channel = tornado.iostream.IOStream(s)
                self.data_channel.connect((self.client_address[0], (int(p[4])*256+int(p[5]))), self.data_channel_connected)
            elif 'PASV' == cmd:
                if self.data_channel:
                    self.data_channel.close()
                self.data_channel, response = self.server.get_passive_connection(self)
                self.stream.write('227 Entering Passive Mode (%s)\r\n' % (response), self.on_response_sent)
            elif ('CWD' == cmd or 'XCWD' == cmd) and content:
                # need to check if file
                content = content.replace('..','').replace('//', '/')
                if 'favicon' in content:
                    # file
                    self.stream.write('550 No such directory.\r\n', self.on_response_sent)
                else:
                    self.curdir = content
                    self.stream.write('250 Directory successfully changed.\r\n', self.on_response_sent)
            elif 'SIZE' == cmd and content:
                # TODO:
                size = 0
                if '/' != content:
                    size = 4
                self.stream.write('213 %d\r\n' % (size), self.on_response_sent)
            elif 'MDTM' == cmd and content:
                # TODO:
                self.stream.write('213 20120402021337\r\n', self.on_response_sent)
            elif 'RETR' == cmd and content:
                self.data_cmd = cmd
                self.data_content = content
                self.stream.write('150 Opening BINARY mode data connection\r\n', self.on_begin_data)
            elif 'LIST' == cmd:
                self.data_cmd = cmd
                self.stream.write('150 Opening ASCII mode data connection\r\n', self.on_begin_data)
            elif 'STOR' == cmd:
                self.stream.write('550 Access Denied\r\n', self.on_response_sent)
            else:
                self.stream.write('502 Command not implemented\r\n', self.on_response_sent)

        def data_channel_connected(self):
            self.stream.write('200 PORT command successful.\r\n', self.on_response_sent)

        def on_begin_data(self):
            # TODO: make configurable
            self.framework.debug('FtpService','beginning data', self.data_cmd, self.data_content)
            if 'LIST' == self.data_cmd:
                self.data_channel.write('-rw-r--r--  1 gfleischer  staff  4 Apr  1 21:13 favicon.ico\r\n', self.on_data_sent)
            elif 'RETR' == self.data_cmd:
                self.data_channel.write('ABCD', self.on_data_sent)
            else:
                self.on_data_sent()
        
        def close_connection(self):
            if self.data_channel:
                self.data_channel.close()
            self.stream.close()

    def __init__(self, framework):
        tornado.netutil.TCPServer.__init__(self)
        self.framework = framework
        self.clients = []
        self.data_server = FtpService.FtpDataServer(self.framework, self)
        self.pasv_port = 48000 # TODO: make configuration options
        self.external_address = ','.join(self.framework.get_config('external_ip').split('.'))

    def handle_stream(self, stream, address):
        self.framework.debug('FtpService',stream , address)
        self.clients.append(self.FtpClient(self.framework, self, stream, address))

    def get_passive_connection(self, client):
        self.pasv_port += 1 # TODO: apply modulo
        psock = self.framework.make_tcp_server_socket(self.pasv_port)
        data_server = FtpService.FtpDataServer(self.framework, client)
        data_server.add_socket(psock)
        response = '%s,%d,%d' % (self.external_address, (self.pasv_port >> 8) % 0xff, self.pasv_port % 0xff)
        self.framework.debug('FtpService', 'allocated passive', self.pasv_port, psock.fileno(), response)
        return data_server, response
