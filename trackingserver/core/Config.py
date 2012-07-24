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
class Config(object):
    def __init__(self, framework):
        self.framework = framework

    def read(self, filename):
        re_name_value = re.compile('^(\w+)\s*=\s*(.*?)\s*$')
        for line in open(filename,'r'):
            line = line.rstrip()
            if not line:
                continue
            elif line.startswith('#'):
                continue
            m = re_name_value.match(line)
            if not m:
                self.framework.warn('bad line in config file: [%s]' % (line))
            else:
                name, value = m.group(1), m.group(2)
                self.framework.set_config(name, value)
