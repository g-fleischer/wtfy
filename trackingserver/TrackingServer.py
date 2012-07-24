#!/usr/bin/env python
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
import sys
import os

def add_thirdparty_path(basepath):
    thirdparty_libnames = ('pyPdf', 'tornado','pydns',)
    thirdparty_search_path = os.path.join(basepath, 'thirdparty')
    for thirdparty_lib in thirdparty_libnames:
        # TODO: append at end of search path assuming that installed version take precedence??
        dirname = os.path.join(thirdparty_search_path, thirdparty_lib)
        if dirname not in sys.path:
            sys.path.append(dirname)

# use application executable path
executable_path = os.path.abspath(os.path.dirname(sys.argv[0]))
add_thirdparty_path(executable_path)

# use search path
basepath = sys.path[0]
if os.path.isfile(basepath):
    basepath = os.path.dirname(basepath)
add_thirdparty_path(basepath)

# apply monkey patch to force HTTP headers to be ordered
import tornado.httputil
from core.MonkeyPatchHttpHeadersInit import MonkeyPatchHttpHeadersInit
tornado.httputil.HTTPHeaders.__init__ = MonkeyPatchHttpHeadersInit

from core.Framework import Framework
from core.WebRequestHandler import WebRequestHandler
from core.WebSocketHandler import WebSocketHandler
from core.ModuleHandler import ModuleHandler

from services.FtpService import FtpService
from services.FlashPolicyService import FlashPolicyService
from services.SilverlightPolicyService import SilverlightPolicyService
from services.XmlSocketService import XmlSocketService
from services.DnsService import DnsTcpServer, DnsUdpServer
from services.FakeHttpsService import FakeHttpsService

import tornado
import tornado.httpserver
import tornado.web
from tornado.ioloop import IOLoop

class TrackingServer():
    def __init__(self):
        self.framework = Framework(executable_path, basepath)
        self.module_handler = ModuleHandler(self.framework)
        self.module_handler.load_modules()
        
    def initialize(self, config_filename):
        self.framework.read_config(config_filename)
        self.framework.initialize_db()
        
    def run(self):
        # setup sockets for different services
        ftp_sockets = [
            self.framework.make_tcp_server_socket(21)
            ]
        http_sockets = [
            self.framework.make_tcp_server_socket(80)
            ]
        https_sockets = [
            self.framework.make_tcp_server_socket(443)
            ]
        flash_policy_sockets = [
            self.framework.make_tcp_server_socket(843)
            ]
        silverlight_policy_sockets = [
            self.framework.make_tcp_server_socket(943)
            ]
        xml_sockets = [
            self.framework.make_tcp_server_socket(2345),
            self.framework.make_tcp_server_socket(4502), # for silverlight
            ]
        dns_tcp_sockets = [
            self.framework.make_tcp_server_socket(53),
            ]
        dns_udp_sockets = [
            self.framework.make_udp_server_socket(53),
            ]
        fake_https_sockets = [
            self.framework.make_tcp_server_socket(8443),
            ]

        app = tornado.web.Application([
                (r"/ws", WebSocketHandler, {'framework':self.framework}),
                (r"/.*", WebRequestHandler, {'framework':self.framework}),
                ])

        http_server = tornado.httpserver.HTTPServer(app)
        http_server.add_sockets(http_sockets)

        https_server = tornado.httpserver.HTTPServer(app,
                                                     ssl_options={
                "certfile": self.framework.get_config('ssl_certfile'),
                "keyfile": self.framework.get_config('ssl_keyfile')
                })
        https_server.add_sockets(https_sockets)

        ftp_server = FtpService(self.framework)
        ftp_server.add_sockets(ftp_sockets)

        flash_policy_server = FlashPolicyService(self.framework)
        flash_policy_server.add_sockets(flash_policy_sockets)

        silverlight_policy_server = SilverlightPolicyService(self.framework)
        silverlight_policy_server.add_sockets(silverlight_policy_sockets)

        xml_socket_server = XmlSocketService(self.framework)
        xml_socket_server.add_sockets(xml_sockets)

        dns_tcp_server = DnsTcpServer(self.framework)
        dns_tcp_server.add_sockets(dns_tcp_sockets)

        dns_udp_server = DnsUdpServer(self.framework)
        dns_udp_server.add_sockets(dns_udp_sockets)

        fake_https_server = FakeHttpsService(self.framework)
        fake_https_server.add_sockets(fake_https_sockets)

        IOLoop.instance().start()

    def cleanup(self):
        self.framework.close_db()

if '__main__' == __name__:
    # config file on command line
    if (len(sys.argv)) != 2:
        sys.stderr.write('usage: %s [configfile]\n' % (sys.argv[0]))
        sys.exit(1)
    config_filename = sys.argv[1]

    server = TrackingServer()
    server.initialize(config_filename)
    try:
        server.run()
    except KeyboardInterrupt:
        sys.stderr.write('KeyboardInterrupt caught\n')
    except Exception, exc:
        import traceback
        sys.stderr.write('FIX ME! ERROR: %s\n' % (traceback.format_exc(exc)))

    server.cleanup()
