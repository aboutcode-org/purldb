#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

"""
mapping of GoogleCode licenses names to DJE license names
Structure: {'sf.net': 'dje_license.name'}


Verification:
from license_library.models import License
[name for name in DJE_NAMES
 if not License.objects.filter(dataspace__name='nexB', name=name).exists()]
"""


'''
Code licenses
<option value="asf20">&nbsp;Apache License 2.0</option>
<option value="art">&nbsp;Artistic License/GPL</option>
<option value="epl">&nbsp;Eclipse Public License 1.0</option>
<option value="gpl2">&nbsp;GNU GPL v2</option>
<option value="gpl3">&nbsp;GNU GPL v3</option>
<option value="lgpl">&nbsp;GNU Lesser GPL</option>
<option value="mit">&nbsp;MIT License</option>
<option value="mpl11">&nbsp;Mozilla Public License 1.1</option>
<option value="bsd">&nbsp;New BSD License</option>
<option value="oos">&nbsp;Other Open Source</option>
'''

'''
Possible separate content license
<option value="cc3-by">&nbsp;Creative Commons 3.0 BY</option>
<option value="cc3-by-nd">&nbsp;Creative Commons 3.0 BY-SA</option>
'''

GCODE_LICENSES = {
    'Apache License 2.0': 'Apache License 2.0',
    'GNU GPL v2': 'GNU General Public License 2.0',
    # FIXME: or GPL 1.0?
    'Artistic License/GPL': 'Artistic License 2.0',
    'New BSD License': 'BSD-Modified',
    'Eclipse Public License 1.0': 'Eclipse Public License 1.0',
    'GNU GPL v3': 'GNU General Public License 3.0',
    # FIXME: v3.0 only??
    'GNU Lesser GPL': 'GNU Lesser General Public License 3.0',
    'MIT License': 'MIT License',
    'Mozilla Public License 1.1': 'Mozilla Public License 1.1',

    'Other Open Source': None,
    'See source code': None,

    'Creative Commons 3.0 BY': 'Creative Commons Attribution License 3.0',
    'Creative Commons 3.0 BY-SA': 'Creative Commons Attribution Share Alike License 3.0',
}


GCODE_NAMES = GCODE_LICENSES.keys()
DJE_NAMES = GCODE_LICENSES.values()
