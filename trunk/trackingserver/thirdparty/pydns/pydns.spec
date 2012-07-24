Summary: Python DNS library
Name: python26-pydns
Version: 2.3.5
Release: 2
Source0: pydns-%{version}.tar.gz
License: Python license
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Anthony Baxter and others <pydns-developer@lists.sourceforge.net>
Packager: Stuart D. Gathman <stuart@bmsi.com>
Url: http://pydns.sourceforge.net/
BuildRequires: python26-devel

%description
Python DNS library

%prep
%setup -n pydns-%{version}

%build
python2.6 setup.py build

%install
python2.6 setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)

%changelog
* Fri Feb 03 2012 Stuart Gathman <stuart@bmsi.com> 2.3.6-1
- Create subclasses of DNSError for different types of errors
- Remove obsolete string module
- close socket on TCP error
- rename variables that conflict with builtin "list" type

* Sat Mar 19 2011 Stuart Gathman <stuart@bmsi.com> 2.3.5-1
- Python 2.6
- Handle large TCP replies (change to blocking IO with timeout)
- server rotation
- additional convenience functions in lazy.py

* Tue Jun 09 2009 Stuart Gathman <stuart@bmsi.com> 2.3.4-1
- Support IDNA label encoding (from 2.3.3-3)
- Optionally support M$ compatible UTF-8 label encoding (DNS.LABEL_UTF8)
- Built-in SPF RR support

* Fri Aug 01 2008 Stuart Gathman <stuart@bmsi.com> 2.3.3-1
- Support IPv6 nameservers

* Thu Jul 24 2008 Stuart Gathman <stuart@bmsi.com> 2.3.2-2
- Fix tcp timeout

* Thu Jul 24 2008 Stuart Gathman <stuart@bmsi.com> 2.3.2-1
- Randomize TID and source port

* Tue May 22 2007 Stuart Gathman <stuart@bmsi.com> 2.3.1-1
- Bug fix release
- BTS Patches:
- 01resolv-conf-parse patch, thanks to Arnaud Fontaine <arnaud@andesi.org>
  (closes: #378991)
- Changes from Ubuntu (SF = Sourceforge project bug #) (closes: #411138):
- 02utf-8 patch for files with UTF-8 content
- 03socket-error-trap patch, Added DNSError trap for socket.error.
- 04lazy-init SF 1563723 lazy should initilize defaults['server']
- 05addr2bin2addr SF 863364 Mac OS X, Win2000 DHCP, addr2bin and bin2addr.
- 06win32-fix SF 1180344 win32dns.py fails on windows server 2003
- 07unpacker SF 954095 Bug in DNS.Lib.Unpacker.getbyte()
- 08import-lib SF 658601 Missing "import Lib"; for TCP protocol
