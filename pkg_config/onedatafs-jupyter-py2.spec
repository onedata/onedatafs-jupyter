%global _scl_prefix /opt/onedata

%{?scl:%scl_package python2-onedatafs-jupyter}
%{!?scl:%global pkg_name %{name}}

%define version {{version}}
%define unmangled_version %{version}
%define fsonedatafs_version {{fsonedatafs_version}}
%define release 1

Summary: Onedata Jupyter Contents Manager implementation
Name: %{?scl_prefix}python2-onedatafs-jupyter
Version: %{version}
Release: 1%{?dist}
Source0: onedatafs-jupyter-%{version}.tar.gz
License: MIT
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Onedata <support@onedata.org>
Url: https://github.com/onedata/onedatafs-jupyter

Requires: epel-release
Requires: scl-utils
Requires: %scl_require_package %{scl} python2-fs-onedatafs = %{fsonedatafs_version}
Requires: python-six
Requires: python-typing
BuildRequires: python
BuildRequires: python-setuptools

%description
Onedata Jupyter Contents Manager implementation.

%prep
%setup -n onedatafs-jupyter-%{version}

%build
python2 setup.py build

%install
python2 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --prefix=/opt/onedata/%{scl}/root/usr --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
