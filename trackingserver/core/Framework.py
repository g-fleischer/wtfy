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
import struct
import socket
import select
import traceback
import sys
import uuid
import hmac
import hashlib
import re
import time
from database.dbinterface import dbinterface
from Config import Config
from WebApplication import WebApplication

NOLINGER = struct.pack('ii', 1, 0)

class Framework():
    def __init__(self, executable_path, basepath):
        self.db = None
        self.config = Config(self)
        self.configuration = {}
        self.webapp = None
        self.executable_path = executable_path
        self.basepath = basepath
        self.hmac_key = None
        self.allow_bad_hmac = False

        self.re_results = re.compile(r'<Results\s+type="(.*?)"\s+version="(.*?)"', re.S)
        self.re_tracking = re.compile(r'<Tracking\s+trackid="(.*?)"\s+existing="(.*?)"', re.S)
        self.re_fingerprints = re.compile(r'<(\w+)\s*>(.*?)</\1\s*>', re.S)

    def version(self):
        return '0.0.2-alpha'

    def web_application(self):
        if self.webapp is None:
            self.webapp = WebApplication(self)
        return self.webapp

    def get_db(self):
        return self.db

    def debug(self, source, msg, *args):
        sys.stderr.write('%s: %s (%s)\n' % (source, msg, args))

    def warn(self, msg):
        sys.stderr.write('%s\n' % (msg))

    def log_exception(self, ex):
        sys.stderr.write('FIX ME! ERROR: %s\n' % (traceback.format_exc(ex)))

    def read_config(self, config_filename):
        self.config.read(config_filename)

    def get_config(self, name):
        return self.configuration[name]

    def set_config(self, name, value):
        # set framework specific
        if 'hmac_key' == name:
            if value and value != 'changeme':
                self.hmac_key = value
        elif 'allow_bad_hmac' == name:
            if value and value.lower() == 'true':
                self.allow_bad_hmac = True

        self.configuration[name] = value

    def make_socket(self, family, sock_type, proto):
        sock = socket.socket(family, sock_type, 0)
        sock.setblocking(0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if socket.SOCK_STREAM == sock_type:
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        return sock
        
    def make_tcp_server_socket(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.bind(('', port))
        sock.listen(128)
        return sock

    def make_udp_server_socket(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))
        return sock

    def get_hmac_key(self):
        if self.hmac_key:
            return self.hmac_key
        return self.unique_id

    def generate_tracking_id(self):
        tracking_id = uuid.uuid4().hex
        h = hmac.new(self.get_hmac_key(), digestmod = hashlib.md5) # MD5 is okay
        h.update(tracking_id)
        tracking_digest = h.hexdigest()
        return ('%s.%s' % (tracking_id, tracking_digest), tracking_id, tracking_digest)

    def extract_tracking_data(self, tracking_data):
        if ':' in tracking_data:
            versioning, tracking_data = tracking_data.split(':', 1)
        else:
            versioning = None
        if '.' in tracking_data:
            tracking_id, tracking_digest = tracking_data.split('.', 1)
            h = hmac.new(self.get_hmac_key(), digestmod = hashlib.md5) # MD5 is okay
            h.update(tracking_id)
            if h.hexdigest() == tracking_digest:
                self.debug('framework', 'extracted tracking_id', tracking_id, tracking_digest)
                return tracking_id, tracking_digest, versioning
            elif self.allow_bad_hmac:
                self.debug('framework', 'allowing bad hmac; extracted tracking_id', tracking_id, tracking_digest)
                return tracking_id, h.hexdigest(), versioning
            else:
                self.debug('framework', 'bad digest', tracking_data)
                return None, None, None
        else:
            self.debug('framework', 'bad tracking', tracking_data)
            return None, None, None

    def extract_results(self, data):
        # TODO: benchmark if XML processing would be faster
        results = {
            'type' : None,
            'version' : None,
            'trackid' : None,
            'existing' : None,
            'fingerprints' : None,
            }

        m = self.re_results.search(data)
        if m:
            results['type'] = m.group(1)
            results['version'] = m.group(2)

        m = self.re_tracking.search(data)
        if m:
            results['trackid'] = m.group(1)
            results['existing'] = m.group(2)

        # TODO: extract date/time info

        n1 = data.find('<Fingerprints')
        n2 = data.find('</Fingerprints')
        if n1 > -1 and n2 > n1:
            # fingerprints
            fingerprints = []
            tmp = data[n1+14:n2]
            matches = self.re_fingerprints.findall(tmp)
            for match in matches:
                fingerprints.append(match)
            results['fingerprints'] = fingerprints

        return results

    def process_results(self, address, request):
        db = self.db

        request_dt = int(time.time())

        results = self.extract_results(request)

        print(results)

        rtype = results['type']
        version = results['version']
        trackid = results['trackid']
        existing = results['existing']

        tracking_id, etracking_id = None, None
        if trackid:
            tracking_id, tracking_digest, junk = self.extract_tracking_data(trackid)
        if existing:
            etracking_id, tracking_digest, junk =  self.extract_tracking_data(existing)

        if tracking_id:
            db.insert_tracking_seen(tracking_id, address[0], request_dt)
            if etracking_id and etracking_id != tracking_id:
                db.insert_tracking_correlation(tracking_id, etracking_id, address[0], request_dt)

        if etracking_id:
            db.insert_tracking_seen(etracking_id, address[0], request_dt)
            if not tracking_id:
                tracking_id = etracking_id

        fingerprints = results['fingerprints']
        if fingerprints:
            for name, content in fingerprints:
                content = content.strip()
                moduleid = '%s-%s-%s' % (rtype, version, name)
                hasher = hashlib.md5()
                hasher.update(content)
                digest = hasher.hexdigest()
                db.insert_results(address[0], address[1], tracking_id, moduleid, '', digest)
                db.insert_results_data(digest, content)


    def initialize_db(self):
        self.db = dbinterface.create_instance(self)
        self.db.initialize()
        self.unique_id = self.db.get_unique_id()

    def close_db(self):
        self.db.close()
        self.db = None

    def get_flash_crossdomain_policy(self):
        return '''<?xml version="1.0"?>
<cross-domain-policy> 
   <site-control permitted-cross-domain-policies="master-only"/>
   <allow-access-from domain="*" to-ports="*" />
</cross-domain-policy>'''

    def get_flash_crossdomain_xml(self):
        return '''<?xml version="1.0"?>
<cross-domain-policy>
<allow-access-from domain="*" secure="false"/>
<allow-http-request-headers-from domain="*" headers="*" secure="false"/>
</cross-domain-policy>
'''
    def get_java_crossdomain_xml(self):
        return '''<?xml version="1.0"?>
<cross-domain-policy>
<allow-access-from domain="*" />
</cross-domain-policy>
'''

    def get_silverlight_clientaccess_policy(self):
        return '''<?xml version="1.0" encoding ="utf-8"?>
<access-policy>
  <cross-domain-access>
    <policy>
      <allow-from http-methods="*" http-request-headers="*">
        <domain uri="*" />
	<domain uri="file://*" />
	<domain uri="http://*" />
	<domain uri="https://*" />
      </allow-from>
      <grant-to>
        <resource path="/" include-subpaths="true" />
      </grant-to>
    </policy>
    <policy>
      <allow-from>
        <domain uri="*" />
	<domain uri="file://*" />
	<domain uri="http://*" />
	<domain uri="https://*" />
      </allow-from>
      <grant-to>
        <socket-resource port="4502-4534" protocol="tcp" />
      </grant-to>
    </policy>
  </cross-domain-access>
</access-policy>
'''
