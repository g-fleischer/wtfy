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
import zlib
import os
import uuid
import time
import sqlite3
from sqlite3 import dbapi2 as sqlite

from dbinterface import dbinterface

class Compressed(object):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)

def adapt_compressed(compressed):
#    return buffer(zlib.compress(compressed.value))
    return buffer(compressed.value)

def convert_compressed(blob):
#    return Compressed(zlib.decompress(str(blob)))
    return Compressed(str(blob))

class dbsqlite(dbinterface):

    SQL_CREATE_TABLE_REQUESTS = """CREATE TABLE Requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
        request_dt DATETIME NOT NULL,
        ipaddr INT NOT NULL,
        srcport INT NOT NULL,
        trackid VARCHAR(32) NOT NULL,
        path TEXT NOT NULL,
        useragent TEXT,
        referer TEXT,
        origin TEXT,
        header_fingerprint VARCHAR(32),
        header_fingerprint_summary VARCHAR(32)
        )"""

    SQL_CREATE_TABLE_TRACKER = """CREATE TABLE Tracker (Name TEXT PRIMARY KEY NOT NULL UNIQUE, Value TEXT NULL)"""
    SQL_CREATE_TABLE_HTTP_HEADERS = """CREATE TABLE Http_Headers (Fingerprint VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE, Data compressed)"""
    SQL_CREATE_TABLE_HTTP_HEADERS_SUMMARY = """CREATE TABLE Http_Headers_Summary (Fingerprint VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE, Data compressed)"""
    SQL_CREATE_TABLE_HTTP_HEADERS_SUMMARY_USERAGENT_XREF = """
         CREATE TABLE Http_Headers_Summary_Useragent_Xref (Fingerprint VARCHAR(32) NOT NULL, UserAgent TEXT NOT NULL, 
         PRIMARY KEY(FingerPrint, UserAgent))""" # TODO: Size this ....?

    SQL_CREATE_TABLE_TRACKING_SEEN = """CREATE TABLE Tracking_Seen (
        trackid VARCHAR(32),
        ipaddr INT NOT NULL,
        request_dt DATETIME NOT NULL,
        PRIMARY KEY (trackid, ipaddr)
        )"""

    SQL_CREATE_TABLE_CORRELATE_TRACKING = """CREATE TABLE Tracking_Correlation (
        trackid_1 VARCHAR(32) NOT NULL, 
        trackid_2 VARCHAR(32) NOT NULL,
        request_dt DATETIME NOT NULL,
        ipaddr INT NOT NULL,
        PRIMARY KEY (trackid_1, trackid_2)
        )"""

    SQL_CREATE_TABLE_RESULTS = """CREATE TABLE Results (
        results_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
        request_dt DATETIME NOT NULL,
        ipaddr INT NOT NULL,
        srcport INT NOT NULL,
        trackid VARCHAR(32) NOT NULL,
        moduleid VARCHAR(64) NOT NULL,
        data_content TEXT,    
        fingerprint VARCHAR(32)
        )"""

    SQL_CREATE_TABLE_RESULTS_DATA = """CREATE TABLE Results_Data (
        Fingerprint VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE,
        Data compressed
        )"""

    def __init__(self, framework):
        dbinterface.__init__(self, framework)

    def initialize(self):
        self._filename = self.framework.get_config('sqlite_dbfile')
        self._conn = self._connectdb(self._filename)

    def _connectdb(self, filename):
        # Register the adapter
        sqlite.register_adapter(Compressed, adapt_compressed)
        sqlite.register_converter("compressed", convert_compressed)

        if os.path.exists(filename):
            need_create = False
        else:
            need_create = True

        conn = sqlite.connect(filename, detect_types=sqlite.PARSE_DECLTYPES, check_same_thread = False)

        if need_create:
            self._createdb(conn)
        else:
            if not self._validatedb(conn):
                # TODO: should clobber existing tables?
                self._createdb(conn)

        return conn

    def _createdb(self, conn):
        cursor = conn.cursor()

        cursor.execute(self.SQL_CREATE_TABLE_TRACKER)
        cursor.execute("""INSERT INTO Tracker (Name, Value) values (?, ?)""", ['VERSION', self.framework.version()])
        cursor.execute("""INSERT INTO Tracker (Name, Value) values (?, ?)""", ['UUID', uuid.uuid4().hex])

        cursor.execute(self.SQL_CREATE_TABLE_REQUESTS)
        cursor.execute(self.SQL_CREATE_TABLE_HTTP_HEADERS)
        cursor.execute(self.SQL_CREATE_TABLE_HTTP_HEADERS_SUMMARY)
        cursor.execute(self.SQL_CREATE_TABLE_HTTP_HEADERS_SUMMARY_USERAGENT_XREF)
        cursor.execute(self.SQL_CREATE_TABLE_TRACKING_SEEN)
        cursor.execute(self.SQL_CREATE_TABLE_CORRELATE_TRACKING)
        cursor.execute(self.SQL_CREATE_TABLE_RESULTS)
        cursor.execute(self.SQL_CREATE_TABLE_RESULTS_DATA)

        conn.commit()
        cursor.close()

    def _validatedb(self, conn):
        cursor = conn.cursor()
        cursor.execute("""SELECT name FROM sqlite_master WHERE type='table'""")
        rows = cursor.fetchall()
        found = False
        count = 0
        for row in rows:
            count += 1
            if 'tracker' == str(row[0]).lower():
                found = True
                break

        if not found and count > 0:
            raise Exception('Existing SQLITE database is not TRACKER format')

        cursor.execute("""SELECT Value FROM Tracker WHERE Name='VERSION'""")
        row = cursor.fetchone()
        if not row or str(row[0]) != self.framework.version():
            raise Exception('Sorry. No database upgrade path available.')

        cursor.close()
        return found

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_unique_id(self):
        cursor = self._conn.cursor()
        try:
            cursor.execute("""SELECT value from Tracker where name='UUID'""")
            row = cursor.fetchone()
            results = str(row[0])
        finally:
            cursor.close()

        return results

    def insert_request(self, ipaddr, srcport, trackid, path, useragent, referer, origin, header_fingerprint, header_fingerprint_summary):
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Requests (request_id, request_dt, ipaddr, srcport, trackid, path, useragent, referer, origin, header_fingerprint, header_fingerprint_summary) 
            VALUES  (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [None, int(time.time()), ipaddr, srcport, trackid, path, useragent, referer, origin, header_fingerprint, header_fingerprint_summary])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()

    def insert_http_headers(self, fingerprint, headers):
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Http_Headers VALUES(?, ?)""", [fingerprint, Compressed(str(headers))])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()

    def insert_http_headers_summary(self, fingerprint, headers):
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Http_Headers_Summary VALUES(?, ?)""", [fingerprint, Compressed(str(headers))])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()

    def insert_http_headers_summary_useragent_xref(self, fingerprint, useragent):
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Http_Headers_Summary_Useragent_Xref VALUES(?, ?)""", [fingerprint, useragent])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()

    def insert_tracking_correlation(self, trackid_1, trackid_2, ipaddr, request_dt = None):
        if request_dt is None:
            request_dt = int(time.time())
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Tracking_Correlation (trackid_1, trackid_2, ipaddr, request_dt) 
            VALUES  (?, ?, ?, ?)""", [trackid_1, trackid_2, ipaddr, request_dt])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()

    def insert_tracking_seen(self, trackid, ipaddr, request_dt = None):
        if request_dt is None:
            request_dt = int(time.time())
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Tracking_Seen (trackid, ipaddr, request_dt) 
            VALUES  (?, ?, ?)""", [trackid, ipaddr, request_dt])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()

    def insert_results(self, ipaddr, srcport, trackid, moduleid, data_content, fingerprint, request_dt = None):
        if request_dt is None:
            request_dt = int(time.time())
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Results (results_id, request_dt, ipaddr, srcport, trackid, moduleid, data_content, fingerprint) 
            VALUES  (?, ?, ?, ?, ?, ?, ?, ?)""", [None, int(time.time()), ipaddr, srcport, trackid, moduleid, data_content, fingerprint])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()

    def insert_results_data(self, fingerprint, data):
        cursor = self._conn.cursor()
        try:
            cursor.execute("""INSERT INTO Results_Data VALUES(?, ?)""", [fingerprint, Compressed(str(data))])
            self._conn.commit()
        except sqlite.IntegrityError:
            pass
        except Exception, ex:
            self.framework.log_exception(ex)
        finally:
            cursor.close()
