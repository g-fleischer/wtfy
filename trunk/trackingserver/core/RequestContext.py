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

class RequestContext(object):
    def __init__(self, handler):
        self.handler = handler
        self.headers = handler.request.headers
        self.body = handler.request.body
        self.method = handler.request.method
        self.cookies = handler.request.cookies
        self.path = handler.request.path
        self.client_address = handler.request.connection.address
        self.postvars = None

        self.trackid = None
        self.tracking_id = None

class WebSocketContext(object):
    def __init__(self, handler, path):
        self.handler = handler
        self.headers = {}
        self.body = ''
        self.method = 'GET'
        self.cookies = ''
        self.path = path
        self.client_address = ('','')
        self.postvars = None

        self.trackid = None
        self.tracking_id = None
