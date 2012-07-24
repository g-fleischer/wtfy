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
import tornado.web
from RequestContext import RequestContext

class WebRequestHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "OPTIONS")

    def get(self):
        self.framework.web_application().do_GET(RequestContext(self))

    def options(self):
        self.framework.web_application().do_OPTIONS(RequestContext(self))

    def post(self):
        self.framework.web_application().do_POST(RequestContext(self))

    def compute_etag(self):
        # prevent default Etag handling
        return None

    def initialize(self, framework):
        # print('initialize', framework)
        self.framework = framework

    def prepare(self):
        # print('prepare',)
        pass

    def on_finish(self):
        # print('on_finish',)
        pass
    
