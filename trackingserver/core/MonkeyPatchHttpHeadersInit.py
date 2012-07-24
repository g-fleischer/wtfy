#
# Author: Gregory Fleischer (gfleischer@gmail.com)
#
# Copyright (c) 2012 Gregory Fleischer
#
# This file is part of WTFY.
#
#
# The Original Code is Tornado.
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
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

# Monkey patch for Tornado: httputil.HTTPHeaders.__init__

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

def MonkeyPatchHttpHeadersInit(self, *args, **kwargs):
    # Don't pass args or kwargs to dict.__init__, as it will bypass
    # our __setitem__
    dict.__init__(self)
    self._as_list = OrderedDict()
    self._last_key = None
    if (len(args) == 1 and len(kwargs) == 0 and
        isinstance(args[0], HTTPHeaders)):
        # Copy constructor
        for k, v in args[0].get_all():
            self.add(k, v)
    else:
        # Dict-style initialization
        self.update(*args, **kwargs)

