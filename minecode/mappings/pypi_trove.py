#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

"""
Mapping of Pypi trove classifiers to known concepts.
See https://pypi.python.org/pypi?%3Aaction=list_classifiers
"""


licenses = {
    'License :: Aladdin Free Public License (AFPL)': 'afpl-9.0',
    'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication': 'cc0-1.0',
    'License :: DFSG approved': 'unknown',
    'License :: Eiffel Forum License (EFL)': 'efl-2.0',
    'License :: Free For Educational Use': 'proprietary',
    'License :: Free For Home Use': 'proprietary',
    'License :: Free for non-commercial use': 'proprietary',
    'License :: Freely Distributable': 'unknown',
    'License :: Free To Use But Restricted': 'proprietary',
    'License :: Freeware': 'proprietary',
    'License :: Netscape Public License (NPL)': 'npl-1.1',
    'License :: Nokia Open Source License (NOKOS)': 'nokos-1.0a',
    # 'License :: OSI Approved': '',
    'License :: OSI Approved :: Academic Free License (AFL)': 'afl-3.0',
    'License :: OSI Approved :: Apache Software License': 'apache-2.0',
    'License :: OSI Approved :: Apple Public Source License': 'apsl-2.0',
    'License :: OSI Approved :: Artistic License': 'artistic-2.0',
    'License :: OSI Approved :: Attribution Assurance License': 'attribution',
    'License :: OSI Approved :: BSD License': 'bsd-new',
    'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)': 'cecill-2.1',
    'License :: OSI Approved :: Common Public License': 'cpl-1.0',
    'License :: OSI Approved :: Eiffel Forum License': 'efl-2.0',
    'License :: OSI Approved :: European Union Public Licence 1.0 (EUPL 1.0)': 'eupl-1.0',
    'License :: OSI Approved :: European Union Public Licence 1.1 (EUPL 1.1)': 'eupl-1.1',
    'License :: OSI Approved :: GNU Affero General Public License v3': 'agpl-3.0',
    # FIXME: we do not have agpl-3.0+
    'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)': 'agpl-3.0',
    'License :: OSI Approved :: GNU Free Documentation License (FDL)': 'gfdl-1.3',
    'License :: OSI Approved :: GNU General Public License (GPL)': 'gpl',
    'License :: OSI Approved :: GNU General Public License v2 (GPLv2)': 'gpl-2.0',
    'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)': 'gpl-2.0-plus',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)': 'gpl-3.0',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)': 'gpl-3.0-plus',
    'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)': 'lgpl-2.0',
    'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)': 'lgpl-2.0-plus',
    'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)': 'lgpl-3.0',
    'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)': 'lgpl-3.0-plus',
    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)': 'lgpl',
    'License :: OSI Approved :: IBM Public License': 'ibmpl-1.0',
    'License :: OSI Approved :: Intel Open Source License': 'intel-bsd-export-control',
    'License :: OSI Approved :: ISC License (ISCL)': 'isc',
    'License :: OSI Approved :: Jabber Open Source License': 'josl-1.0',
    'License :: OSI Approved :: MIT License': 'mit',
    # FIXME: old and not in scancode: https://opensource.org/licenses/mitrepl
    # 'License :: OSI Approved :: MITRE Collaborative Virtual Workspace License (CVW)': '',
    'License :: OSI Approved :: Motosoto License': 'motosoto-0.9.1',
    'License :: OSI Approved :: Mozilla Public License 1.0 (MPL)': 'mpl-1.0',
    'License :: OSI Approved :: Mozilla Public License 1.1 (MPL 1.1)': 'mpl-1.1',
    'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)': 'mpl-2.0',
    'License :: OSI Approved :: Nethack General Public License': 'ngpl',
    'License :: OSI Approved :: Nokia Open Source License': 'nokos-1.0a',
    'License :: OSI Approved :: Open Group Test Suite License': 'opengroup',
    'License :: OSI Approved :: Python License (CNRI Python License)': 'cnri-python-1.6.1',
    'License :: OSI Approved :: Python Software Foundation License': 'python',
    'License :: OSI Approved :: Qt Public License (QPL)': 'qpl-1.0',
    'License :: OSI Approved :: Ricoh Source Code Public License': 'ricoh-1.0',
    'License :: OSI Approved :: Sleepycat License': 'sleepycat',
    'License :: OSI Approved :: Sun Industry Standards Source License (SISSL)': 'sun-sissl-1.2',
    'License :: OSI Approved :: Sun Public License': 'spl-1.0',
    'License :: OSI Approved :: University of Illinois/NCSA Open Source License': 'uoi-ncsa',
    'License :: OSI Approved :: Vovida Software License 1.0': 'vsl-1.0',
    'License :: OSI Approved :: W3C License': 'w3c',
    'License :: OSI Approved :: X.Net License': 'xnet',
    'License :: OSI Approved :: zlib/libpng License': 'zlib',
    'License :: OSI Approved :: Zope Public License': 'zpl-2.1',
    'License :: Other/Proprietary License': 'proprietary',
    'License :: Public Domain': 'public-domain',
    # not in scancode
    # 'License :: Repoze Public License': '',
}
