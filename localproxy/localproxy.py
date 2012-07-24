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
import argparse
from lib.ProxyServer import ProxyServer
from TrackerInjection import TrackerInjection

if '__main__' == __name__:
    try:
        parser = argparse.ArgumentParser(description='run a local proxy to inject content')
        parser.add_argument('--bind-address', type=str, default='')
        parser.add_argument('--bind-port', type=int, default=8118)
        parser.add_argument('--inject-host', type=str, default='localhost')
        parser.add_argument('--verbose', action='store_const', const=True, default=False)
        parser.add_argument('--target', type=str, action='append', default=None)
        args = parser.parse_args()

        print('starting with', args)
        proxy = ProxyServer(args.bind_address, args.bind_port)
        injector = TrackerInjection(args.inject_host, verbose = args.verbose, targets = args.target)
        proxy.process(injector)
    except Exception, e:
        print(e)

