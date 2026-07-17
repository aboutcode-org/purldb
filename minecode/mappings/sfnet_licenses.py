#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


"""
Structure: {'sf.net': 'dje_license.name'}

Verification:
from license_library.models import License
[name for name in DJE_NAMES
 if not License.objects.filter(dataspace__name='nexB', name=name).exists()]
"""

SFNET_LICENSES = {
    "Academic Free License (AFL)": "Academic Free License 3.0",
    "Adaptive Public License": "Adaptive Public License",
    "Affero GNU Public License ": "GNU Affero General Public License 3.0",
    "Apache License V2.0": "Apache License 2.0",
    "Apache Software License": "Apache License 2.0",
    "Apple Public Source License": "Apple Public Source License 2.0",
    "Artistic License": "Artistic License 2.0",
    "Artistic License 2.0": "Artistic License 2.0",
    "Attribution Assurance License": "Attribution Assurance License",
    "BSD License": "BSD-Modified",
    "Boost Software License (BSL1.0)": "Boost Software License 1.0",
    "Common Development and Distribution License": "Common Development and Distribution License 1.1",
    "Common Public Attribution License 1.0 (CPAL)": "Common Public Attribution License 1.0",
    "Common Public License 1.0": "Common Public License 1.0",
    "Computer Associates Trusted Open Source License 1.1": "Computer Associates Trusted Open Source License 1.1",
    "Creative Commons Attribution License": "Creative Commons Attribution License 3.0",
    "Creative Commons Attribution Non-Commercial License V2.0": "Creative Commons Attribution Non-Commercial 2.0",
    "Creative Commons Attribution ShareAlike License V2.0": "Creative Commons Attribution Share Alike License 2.0",
    "Creative Commons Attribution ShareAlike License V3.0": "Creative Commons Attribution Share Alike License 3.0",
    "CUA Office Public License Version 1.0": "CUA Office Public License 1.0",
    "Eclipse Public License": "Eclipse Public License 1.0",
    "Educational Community License, Version 2.0": "Educational Community License 2.0",
    "Eiffel Forum License V2.0": "Eiffel Forum License 2.0",
    "Eiffel Forum License": "Eiffel Forum License 2.0",
    "Entessa Public License": "Entessa Public License v1.0",
    "EU DataGrid Software License": "EU DataGrid Software License",
    "European Union Public License": "European Union Public Licence 1.1",
    "Fair License": "Fair License",
    "GNU General Public License version 2.0 (GPLv2)": "GNU General Public License 2.0",
    "GNU General Public License version 3.0 (GPLv3)": "GNU General Public License 3.0",
    "GNU General Public License with Classpath exception (Classpath::License)": "GNU General Public License 2.0 with Classpath exception",
    "GNU Library or Lesser General Public License version 2.0 (LGPLv2)": "GNU Library General Public License 2.0",
    "GNU Library or Lesser General Public License version 3.0 (LGPLv3)": "GNU Lesser General Public License 3.0",
    "Historical Permission Notice and Disclaimer": "Historical Permission Notice and Disclaimer",
    "IBM Public License": "IBM Public License",
    "ISC License": "ISC License (ISCL)",
    "Intel Open Source License": "Intel Open Source License 1989",
    "Jabber Open Source License": "Jabber Open Source License 1.0",
    "LaTeX Project Public License": "LaTeX Project Public License v1.3a",
    "Lucent Public License Version 1.02": "Lucent Public License 1.02",
    "MIT License": "MIT License",
    "Microsoft Public License": "Microsoft Public License",
    "Microsoft Reciprocal License": "Microsoft Reciprocal License",
    "Mozilla Public License 1.0 (MPL)": "Mozilla Public License 1.0",
    "Mozilla Public License 1.1 (MPL 1.1)": "Mozilla Public License 1.1",
    "Mozilla Public License 2.0 (MPL 2.0)": "Mozilla Public License 2.0",
    "NASA Open Source Agreement": "NASA Open Source License v1.3",
    "Nethack General Public License": "Nethack General Public License",
    "Nokia Open Source License": "Nokia Open Source License 1.0a",
    "Non-Profit Open Software License 3.0 (Non-Profit OSL 3.0)": "Non-Profit Open Software License 3.0",
    "NTP License": "NTP License",
    "OCLC Research Public License 2.0": "OCLC Research Public License 2.0",
    "OSI-Approved Open Source": None,
    "Open Font License 1.1 (OFL 1.1)": "Open Font License 1.1",
    "Open Group Test Suite License": "Open Group Test Suite License",
    "Open Software License 3.0 (OSL3.0)": "Open Software License 3.0",
    "Other License": None,
    "PHP License": "PHP License 3.01",
    "Public Domain": "Public Domain",
    "Python License (CNRI Python License)": "CNRI Open Source License Agreement for Python 1.6.1",
    "Python Software Foundation License": "Python Software Foundation License v2",
    "Qt Public License (QPL)": "Q Public License Version 1.0",
    "Reciprocal Public License 1.5 (RPL1.5)": "Reciprocal Public License 1.5",
    "RealNetworks Public Source License V1.0": "RealNetworks Public Source License v1.0",
    "Reciprocal Public License": "Reciprocal Public License 1.5",
    "Ricoh Source Code Public License": "Ricoh Source Code Public License v1.0",
    "Simple Public License 2.0": "Simple Public License Version 2.0",
    "Sleepycat License": "Sleepycat License (Berkeley Database License)",
    "Sun Industry Standards Source License (SISSL)": "Sun Industry Standards Source License 1.2",
    "Sun Public License": "Sun Public License 1.0",
    "Sybase Open Watcom Public License": "Sybase Open Watcom Public License v1.0",
    "University of Illinois/NCSA Open Source License": "University of Illinois/NCSA Open Source License",
    "Vovida Software License 1.0": "Vovida Software License v. 1.0",
    "W3C License": "W3C Software Notice and License",
    "Zope Public License": "Zope Public License 2.1",
    "wxWindows Library Licence": "wxWindows Library Licence 3.1",
    "X.Net License": "X.Net Inc. License",
    "zlib/libpng License": "Libpng License",
}

SFNET_NAMES = SFNET_LICENSES.keys()
DJE_NAMES = SFNET_LICENSES.values()
