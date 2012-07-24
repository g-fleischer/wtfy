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
import os
import inspect
import pkgutil
import modules


class ModuleHandler(object):
    def __init__(self, framework):
        self.framework = framework

    def load_modules(self):
        paths = []
        for basepath in [self.framework.executable_path, self.framework.basepath]:
            path = os.path.join(basepath, 'modules')
            if os.path.isdir(path):
                if path not in paths:
                    paths.append(path)

        for importer, modname, ispkg in pkgutil.walk_packages(paths, prefix='modules.'):
            print('X', importer, modname, ispkg)
            try:
                try:
                    module = reload(sys.modules[modname])
                except KeyError:
                    module = __import__(modname, fromlist='fake')

                members = inspect.getmembers(module, inspect.isclass)
                for member in members:
                    clazz = member[1]()
                    print(clazz.PATH)
                    d = dir(clazz)

            except Exception, e:
                self.framework.log_exception(e)

    def visit_modules(self, arg, dirname, names):
        for name in names:
            if name.endswith('.py') and name != '__init__.py':
                filename = os.path.join(dirname, name)
                modname = name[:-3]
                self.load_module(modname)
                self.modules.append(modname)

    def load_module(self, modname):
        module = __import__('modules.'+modname, self.globals)

