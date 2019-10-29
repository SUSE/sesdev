#
# spec file for package sesdev
#
# Copyright (c) 2019 SUSE LINUX GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#


Name:           sesdev
Version:        0.1.0
Release:        0
Summary:        CLI tool to deploy and manage SES clusters
License:        MIT
Url:            https://github.com/rjfd/sesdev
Source:         TODO
BuildRequires:  python-rpm-macros
BuildRequires:  python3-setuptools

%description
sesdev is a CLI tool for developers to help with deploying SES clusters.
This tool uses vagrant and libvirt to create VMs and install Ceph using
DeepSea. The tool is highly customizable and allows to choose different
versions of Ceph and SES, as well as, different versions of the openSUSE
based OS.

%prep
%autosetup -n sesdev-%{version} -p1

%build
%python3_build

%install
%python3_install

%files
%license LICENSE
%doc ChangeLog README
%{python3_sitelib}/*
%{_bindir}/sesdev

%changelog

