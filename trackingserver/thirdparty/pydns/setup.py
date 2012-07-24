#! /usr/bin/env python
# 
# $Id: setup.py,v 1.4.2.3 2008/08/01 04:01:25 customdesigned Exp $
#

import sys,os

sys.path.insert(0,os.getcwd())

from distutils.core import setup

import DNS

setup(
        #-- Package description
        name = 'pydns',
        license = 'Python License',
        version = DNS.__version__,
        description = 'Python DNS library',
        long_description = """Python DNS library:
""",
        author = 'Anthony Baxter and others', 
        author_email = 'pydns-developer@lists.sourceforge.net',
      maintainer="Stuart D. Gathman",
      maintainer_email="stuart@bmsi.com",
      url = 'http://pydns.sourceforge.net/',
      packages = ['DNS'], keywords = ['DNS'],
      classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Python License (CNRI Python License)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: Name Service (DNS)',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ]
)

#
# $Log: setup.py,v $
# Revision 1.4.2.3  2008/08/01 04:01:25  customdesigned
# Release 2.3.3
#
# Revision 1.4.2.2  2008/08/01 03:58:03  customdesigned
# Don't try to close socket when never opened.
#
# Revision 1.4.2.1  2008/07/28 19:54:13  customdesigned
# Add pypi metadata to setup.py
#
# Revision 1.4  2002/05/06 06:32:07  anthonybaxter
# filled in a blank
#
# Revision 1.3  2001/11/23 19:43:57  stroeder
# Prepend current directory to sys.path to enable import of DNS.
#
# Revision 1.2  2001/11/23 19:36:35  stroeder
# Use DNS.__version__ as package version and corrected name
#
# Revision 1.1  2001/08/09 13:42:38  anthonybaxter
# initial setup.py. That was easy. :)
#
#
