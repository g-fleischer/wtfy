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
import tornado.websocket
import json
from RequestContext import WebSocketContext

class WebSocketHandler(tornado.websocket.WebSocketHandler):

    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "OPTIONS")

    def initialize(self, framework):
        self.framework = framework

    def open(self):
        print("WebSocket opened",)
        pass

    def on_message(self, message):
        print('socket message', message)

        if message.startswith('{'):
            # TODO: handle JSON content
            pass
        elif message.startswith('/'):
            # request for raw content
            found, body, content_type = self.framework.web_application().get_file_content(WebSocketContext(self, message), message[1:])
            response = json.dumps({'status':'ok', 'body':body, 'content_type':content_type})
            print(response)
            self.write_message(response)
        else:
            self.framework.log_debug('unhandled: ' + message)

    def on_close(self):
        print("WebSocket closed",)
        pass

