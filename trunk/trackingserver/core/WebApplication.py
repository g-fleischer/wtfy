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
import os
import re
import traceback
import time
import hashlib
import zipfile
import urllib2
import cgi
from cStringIO import StringIO
from pyPdf import PdfFileWriter

class WebApplication(object):

    def __init__(self, framework):
        self.framework = framework
        # TODO: make reset configurable
        self.CACHE_DAYS = 365 
        self.CACHE_SECONDS = self.CACHE_DAYS * 24 * 60 * 60
        self.TEMP_CACHE_SECONDS = 60
        self.DYNAMIC_DIRECTORY = self.framework.get_config('dynamic_directory')
        self.STATIC_DIRECTORY = self.framework.get_config('static_directory')
        self.EXTERNAL_DOMAIN = self.framework.get_config('domain')
        self.RE_REPLACEMENT = re.compile(r'\$\{(\w+)\s*\}')

    def get_content_type(self, filename):
        if filename.endswith('.html'):
            content_type = 'text/html'
        elif filename.endswith('.css'):
            content_type = 'text/css'
        elif filename.endswith('.js'):
            content_type = 'text/javascript'
        elif filename.endswith('.jar'):
            content_type = 'application/java-archive' # or, application/x-jar
        elif filename.endswith('.ico'):
            content_type = 'image/x-icon'
        elif filename.endswith('.swf'):
            content_type = 'application/x-shockwave-flash'
        elif filename.endswith('.pdf'):
            content_type = 'application/pdf'
        elif filename.endswith('.xap'):
            content_type = 'application/x-silverlight-2'
        elif filename.endswith('.xml'):
            content_type = 'text/xml'
        elif filename.endswith('.png'):
            content_type = 'image/png'
        else:
            content_type = 'text/plain'

        return content_type

    def dynamic_replacement(self, match, trackid):
        if 'trackid' == match.group(1).rstrip():
            return trackid
        elif 'domain' == match.group(1).rstrip():
            return self.EXTERNAL_DOMAIN
        else:
            return '<unknown>'

    def format_time(self, tm):
        return time.strftime('%a, %d %b %Y %H:%M:%S', tm)

    def append_id_zip_content(self, context, filename):
        fhandle = file(os.path.join(self.DYNAMIC_DIRECTORY, filename), 'rb')
        buf = StringIO()
        buf.write(fhandle.read())
        fhandle.close()

        buf.seek(0,0)
        zwrite = zipfile.ZipFile(buf, 'a')
        zwrite.writestr('id.txt', context.trackid)
        zwrite.close()

        contents = buf.getvalue()
        content_type = self.get_content_type(filename)

        return contents, content_type

    def get_pdf_content(self, context, filename):
        jsfile = os.path.join(self.DYNAMIC_DIRECTORY, 'pdf-%s.js' % (filename[0:-4].lower()))
        output = PdfFileWriter()
        output.addBlankPage(100,100)
        if os.path.exists(jsfile):
            fhandle = open(jsfile, 'rb')
            jscontents = fhandle.read()
            jscontents = self.RE_REPLACEMENT.sub(lambda m: self.dynamic_replacement(m, context.trackid), jscontents)
            fhandle.close()
            output.addJS(jscontents)
        buf = StringIO()
        output.write(buf)

        contents = buf.getvalue()
        content_type = 'application/pdf'

        return contents, content_type

    def get_dynamic_content(self, context, filename):

        # TODO: always allocate a new one?
        if not context.trackid:
            context.trackid, context.tracking_id, context.tracking_digest = self.framework.generate_tracking_id()

        fhandle = open(os.path.join(self.DYNAMIC_DIRECTORY, filename), 'rb')
        contents = fhandle.read()
        contents = self.RE_REPLACEMENT.sub(lambda m: self.dynamic_replacement(m, context.trackid), contents)
        fhandle.close()
        content_type = self.get_content_type(filename)
        return contents, content_type

    def get_static_content(self, context, filename):
        fhandle = open(os.path.join(self.STATIC_DIRECTORY, filename), 'rb')
        contents = fhandle.read()
        fhandle.close()
        content_type = self.get_content_type(filename)
        return contents, content_type

    def get_file_content(self, context, filename):
        found, body, content_type = False, '', ''
        if filename and '..' not in filename:
            static_file = os.path.join(self.STATIC_DIRECTORY, filename)
            dynamic_file = os.path.join(self.DYNAMIC_DIRECTORY, filename)
            if os.path.isfile(dynamic_file):
                body, content_type = self.get_dynamic_content(context, filename)
                found = True
            elif os.path.isfile(static_file):
                body, content_type = self.get_static_content(context, filename)
                found = True

        return found, body, content_type

    def get_tracking_id(self, context, query, vars):
        trackid = None
        # TODO: check consistency between different values !!!!

        if query.startswith('trackid='):
            trackid = query[len('trackid='):]
        if vars.startswith('trackid='):
            trackid = vars[len('trackid='):]
        if context.headers.has_key('x-trackid'):
            trackid = context.headers['x-trackid']
            if '/' in trackid:
                trackid, junk = trackid.split('/', 1)
        if context.headers.has_key('if-none-match'):
            trackid = context.headers['if-none-match']
            if '/' in trackid:
                trackid, junk = trackid.split('/', 1)
        if context.headers.has_key('cookie'):
            cookies = context.headers['cookie'].split(';')
            for cookie in cookies:
                name, value = cookie, ''
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                if 'trackid' == name.strip():
                    trackid = value.strip()
        if trackid:
            trackid = trackid.replace('"','')

        if trackid:
            if ':' in trackid:
                versioning, tracking_data = trackid.split(':', 1)
            else:
                tracking_data = trackid
                versioning = '0'

            context.tracking_id, context.tracking_digest = self.framework.extract_tracking_id(tracking_data)
            if context.tracking_id:
                context.trackid = trackid
                context.versioning = versioning
            else:
                context.trackid = None
                context.versioning = None

        # TODO: always allocate a new one?
        if not context.trackid:
            context.trackid, context.tracking_id, context.tracking_digest = self.framework.generate_tracking_id()

    def send_cached_response(self, context, body, content_type, cache_seconds = None, headers = None, must_revalidate = False):
        now = time.time()
        if cache_seconds is None:
            cache_seconds = self.CACHE_SECONDS
        future = now + cache_seconds
        handler = context.handler
        handler.set_status(200)
        self.set_common_headers(context, content_type, headers, future)

        # TODO: include must-revalidate?
        if must_revalidate:
            handler.set_header('Cache-Control', 'private, no-transform, must-revalidate, max-age=%d' % cache_seconds)
#            handler.set_header('Cache-Control', 'private, no-transform, must-revalidate')
        else:
            handler.set_header('Cache-Control', 'private, no-transform, max-age=%d' % cache_seconds)
        handler.set_header('Last-Modified', '%s GMT' % self.format_time(time.gmtime(now)))
        handler.set_header('Expires', '%s GMT' % self.format_time(time.gmtime(future)))

        if not body is None:
            handler.set_header('Content-Length', '%d' % len(body))
            handler.write(body)

        handler.finish()

    def set_common_headers(self, context, content_type, headers, future):
        handler = context.handler
        handler.set_header('Content-Type', content_type)
        handler.set_header('Access-Control-Allow-Origin', '*')
        handler.set_header('Access-Control-Expose-Headers', 'ETag')
        if 'text/plain' == content_type:
            handler.set_header('X-Content-Type-Options', 'nosniff')

        if context.trackid:
            handler.set_header('Set-Cookie', 'trackid=%s; path=/; expires=%s GMT' % (context.trackid, self.format_time(time.gmtime(future))))
            handler.set_header('ETag', '"%s"' % (context.trackid)) # TODO: Send Weak?
            # TODO: reference P3P policy using tracking DNS?
            handler.set_header('P3P', 'policyref="http://%s/p3p/%s.xml",CP="Not a P3P policy"' % (self.EXTERNAL_DOMAIN, context.trackid)) 
        else:
            handler.set_header('P3P', 'CP="Not a P3P policy"')

        if None != headers:
            for name, value in headers.iteritems():
                handler.set_header(name, value)

    def send_response(self, context, status, body, content_type, headers = None):
        now = time.time()
        future = now + self.CACHE_SECONDS
        handler = context.handler
        handler.set_status(status)
        self.set_common_headers(context, content_type, headers, future)
        handler.set_header('Last-Modified', '%s GMT' % self.format_time(time.gmtime(now)))

        if not body is None:
            handler.set_header('Content-Length', '%d' % len(body))
            handler.write(body)

        handler.finish()

    def save_request(self, context):

        method = context.method
        path = context.path
        query, vars = '', ''
        ipaddr, srcport = context.client_address

        print('path', path)

        cookie_trackid = context.handler.get_cookie('trackid')
        inm_trackid = None
        x_trackid = None

        headers_io = StringIO()
        summary_headers_io = StringIO()
        useragent, referer, origin = None, None, None
        for name, value in context.headers.get_all():
            print('headers', name, value)
            skip = False
            lname = name.lower()
            if 'user-agent' == lname:
                useragent = value
            elif 'referer' == lname:
                referer = value
                skip = True
            elif 'origin' == lname:
                origin = value
                skip = True
            elif 'x-trackid' == lname:
                x_trackid = value
                skip = True
            elif 'if-none-match' == lname:
                inm_trackid = value
                if inm_trackid and '"' in inm_trackid:
                    inm_trackid = inm_trackid.replace('"', '')
                skip = True
            elif lname in ('cookie', 'if-modified-since'):
                skip = True

            summary_headers_io.write(name + '\n')
            if not skip:
                headers_io.write('%s: %s\n' % (name, value))

        db = self.framework.get_db()
        for possible_trackid in (inm_trackid, cookie_trackid, x_trackid):
            if possible_trackid:
                tracking_id, tracking_digest, versioning = self.framework.extract_tracking_data(possible_trackid)
                if tracking_id:
                    # found valid
                    if context.tracking_id and tracking_id != context.tracking_id:
                        # TODO: save correlate
                        pass
                    context.trackid = possible_trackid
                    context.tracking_id = tracking_id
                    context.tracking_digest = tracking_digest
                    context.versioning = versioning
                    context.trackid_found = True

        # if none found, generate a new
        # TODO: always do this?
        if not context.tracking_id:
            context.trackid_found = False
            context.trackid, context.tracking_id, context.tracking_digest = self.framework.generate_tracking_id()
            context.versioning = None
            
        headers = headers_io.getvalue()
        summary_headers = summary_headers_io.getvalue()

        headers_hasher = hashlib.md5()
        summary_headers_hasher = hashlib.md5()
        headers_hasher.update(headers)
        summary_headers_hasher.update(summary_headers)
        headers_fingerprint = headers_hasher.hexdigest()
        summary_headers_fingerprint = summary_headers_hasher.hexdigest()

        db.insert_request(ipaddr, srcport, context.tracking_id, context.path, useragent, referer, origin, headers_fingerprint, summary_headers_fingerprint)
        db.insert_http_headers(headers_fingerprint, headers)
        db.insert_http_headers_summary(summary_headers_fingerprint, summary_headers)
        if useragent:
            db.insert_http_headers_summary_useragent_xref(summary_headers_fingerprint, useragent)

        return path

    def process_request(self, context):

        path = self.save_request(context)

        now = time.time()
        if path in ('./nocookie.html',):
            body, content_type = self.get_dynamic_content(context, path[1:])
            self.send_response(context, 200, body, content_type)
        elif path in ('/id.js', '/ids.js', '/id.html', '/id.css', '/file.html', '/inline.html', '/file.txt', '/file.jar', '/inline.jar', '/detect-noscript-blocking.html', '/favicon.png',):
            future = now + (self.CACHE_SECONDS)
            body, content_type = self.get_dynamic_content(context, path[1:])
            headers = {}
            if '/file.html' == path:
                headers['Content-Disposition'] = 'attachment; filename=file.html'
            if '/inline.html' == path:
                headers['Content-Disposition'] = 'inline; filename=inline.html'
            if '/file.txt' == path:
                headers['Content-Disposition'] = 'attachment; filename=file.txt'
            if '/file.jar' == path:
                headers['Content-Disposition'] = 'attachment; filename=file.jar'
            if '/inline.jar' == path:
                headers['Content-Disposition'] = 'inline; filename=inline.jar'
            self.send_cached_response(context, body, content_type, headers = headers, must_revalidate = True)
        elif path in ('/empty.html'):
            self.send_response(context, 200, '', 'text/html', {'Cache-Control':'no-cache'})
        elif path in ('/Tracker.pdf'):
            body, content_type = self.get_pdf_content(context, path[1:])
            self.send_cached_response(context, body, content_type)
        elif path in ('/Tracking.pdf'):
            body, content_type = self.get_pdf_content(context, path[1:])
            self.send_cached_response(context, body, content_type)
        elif path in ('/Tracker.jar'):
            body, content_type = self.append_id_zip_content(context, path[1:])
            self.send_cached_response(context, body, content_type)
        elif path.endswith('.xap'):
            body, content_type = self.append_id_zip_content(context, path[1:])
            self.send_cached_response(context, body, content_type)
        elif path in ('/track.js', '/ping.html'):
            body, content_type = self.get_dynamic_content(context, path[1:])
            self.send_cached_response(context, body, content_type)
        elif path in ('/test.html', '/test.jar',):
            future = now + (self.TEMP_CACHE_SECONDS)
            body, content_type = self.get_dynamic_content(context, path[1:])
            self.send_cached_response(context, body, content_type, self.TEMP_CACHE_SECONDS)
        elif path in ('/favicon.ico',):
            future = now + (self.TEMP_CACHE_SECONDS)
            body, content_type = self.get_dynamic_content(context, path[1:])
        elif path in ('/3rdparty-iframe.html',):
            body, content_type = self.get_dynamic_content(context, path[1:])
            self.send_cached_response(context, body, content_type, self.CACHE_SECONDS)
        elif path in ('/crossdomain.xml'):
            future = now + (self.TEMP_CACHE_SECONDS)
            useragent = context.headers.get('User-Agent')
            content_type = 'text/xml'
            if useragent and 'Java/' in useragent:
                body = self.framework.get_java_crossdomain_xml()
            else:
                body = self.framework.get_flash_crossdomain_xml()
            self.send_cached_response(context, body, content_type, self.TEMP_CACHE_SECONDS)
        elif path in ('/dump-request',):
            bio = StringIO()
            bio.write('HEADERS\n' + '='*32 + '\n')
            for name, value in context.headers.get_all():
                bio.write('%s=%s\n' % (name, value))
            bio.write('\n' + '='*32 + '\n')
            body = bio.getvalue()
            self.send_response(context, 200, body, 'text/plain')
        elif path in ('/flash-results',):
            self.framework.process_results(context.client_address, context.body)
            body = 'trackid=%s' % (context.trackid)
            self.send_response(context, 200, body, 'text/plain')
        elif path in ('/pdf-results',):
            self.framework.process_results(context.client_address, context.body)
            body = '<Response trackid="%s"></Response>' % (context.trackid)
            self.send_response(context, 200, body, 'text/xml')
        elif path in ('/echo-pdf-results',):
            self.framework.process_results(context.client_address, context.body)
            self.send_response(context, 200, context.body, 'text/xml')
        else:
            filename = path[1:]
            found, body, content_type = self.get_file_content(context, filename)
            if found:
                self.send_cached_response(context, body, content_type, must_revalidate = True)
            else:
                content_type = 'text/plain'
                body = 'Not found'
                self.send_response(context, 404, body, content_type, {'Cache-Control':'no-cache'})

    def do_OPTIONS(self, context):
        try:
            now = time.time()
            future = now + (self.CACHE_SECONDS)

            path = context.path
            query, vars = '', ''

            if '?' in path:
                path, query = path.split('?', 1)
            if ';' in path:
                path, vars = path.split(';', 1)

            self.get_tracking_id(context, query, vars)

            headers = {}
            ac_request_method = context.headers.get('Access-Control-Request-Method')
            ac_request_headers = context.headers.get('Access-Control-Request-Headers')
            if (ac_request_method or ac_request_headers):
                if ac_request_method:
                    headers['Access-Control-Allow-Methods'] = ac_request_method
                if ac_request_headers:
                    headers['Access-Control-Allow-Headers'] = ac_request_headers
                headers['Access-Control-Max-Age'] = str(self.CACHE_SECONDS)
            else:
                headers = {'Allow': ','.join(context.handler.SUPPORTED_METHODS)}
            self.send_response(context, 200, '', 'text/plain', headers)
        except Exception, exc:
            self.framework.log_exception(exc)
            if '127.0.0.1' == context.client_address[0]:
                body = traceback.format_exc(exc)
            else:
                body = 'Oops. Server error.'
            self.send_response(context, 500, body, 'text/plain')

    def do_GET(self, context):
        try:
            self.process_request(context)
        except Exception, exc:
            self.framework.log_exception(exc)
            if '127.0.0.1' == context.client_address[0]:
                body = traceback.format_exc(exc)
            else:
                body = 'Oops. Server error.'
            self.send_response(context, 500, body, 'text/plain')

    def do_POST(self, context):
        try: 
            ctype, pdict = cgi.parse_header(context.headers.get('content-type'))
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(StringIO(context.body), pdict) # TODO: use tornado method
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(context.headers.get('content-length'))
                postvars = cgi.parse_qs(context.body, keep_blank_values=1)
            else:
                postvars = {}
            context.postvars = postvars
            self.process_request(context)
        except Exception, exc:
            self.framework.log_exception(exc)
            if '127.0.0.1' == context.client_address[0]:
                body = traceback.format_exc(exc)
            else:
                body = 'Oops. Server error.'
            self.send_response(context, 500, body, 'text/plain')
        
