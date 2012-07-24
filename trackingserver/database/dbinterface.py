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
class dbinterface():
    def __init__(self, framework):
        self.framework = framework

    def initialize(self):
        raise Exception('not implemented')

    def get_unique_id(self):
        raise Exception('not implemented')

    def close(self):
        raise Exception('not implemented')

    def insert_request(self, ipaddr, srcport, trackid, path, useragent, referer, origin, header_fingerprint, header_fingerprint_summary):
        raise Exception('not implemented')

    def insert_http_headers(self, fingerprint, headers):
        raise Exception('not implemented')

    def insert_http_headers_summary(self, fingerprint, headers):
        raise Exception('not implemented')

    def insert_http_headers_summary_useragent_xref(self, fingerprint, useragent):
        raise Exception('not implemented')

    def insert_results_fingerprint_data(self, fingerprint, data):
        raise Exception('not implemented')

    @staticmethod
    def create_instance(framework):
        dbtype = framework.get_config('dbtype')
        if 'sqlite' == dbtype:
            import dbsqlite
            return dbsqlite.dbsqlite(framework)
        else:
            raise Exception('unsupported database type: [%s]' % (dbtype))


    
