#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import unittest
from unittest.case import expectedFailure

from discovery.version import version_hint


class VersionHintTestCase(unittest.TestCase):

    def version_tester(self, versions, ignore_pre_releases=False):
        """Test versions mapping of (path, expected)"""
        for path in versions:
            self.assertEqual(
                versions[path],
                version_hint(path, ignore_pre_releases=ignore_pre_releases)
            )

    def test_version_hint_base(self):
        versions = {
            '/xmlgraphics/fop/source/fop-1.0-src.zip': '1.0',
            '/xml/xindice/xml-xindice-1.2m1-src.zip': '1.2m1',
            '/xmlgraphics/fop/binaries/fop-0.94-bin-jdk1.3.tar.gz': '0.94',
            '/xmlgraphics/batik/batik-src-1.7beta1.zip': '1.7beta1',
            '/xmlgraphics/batik/batik-1.7-jre13.zip': '1.7',
            '/xmlbeans/source/xmlbeans-2.3.0-src.tgz': '2.3.0',
            '/xml/xindice/source/xml-xindice-1.2m1-src.tar.gz': '1.2m1',
            '/xml/xerces-p/binaries/XML-Xerces-2.3.0-4-win32.zip': '2.3.0-4',
            '/xml/xerces-p/source/XML-Xerces-2.3.0-3.tar.gz': '2.3.0-3',
            '/xml/xalan-j/source/xalan-j_2_7_0-src-2jars.tar.gz': '2_7_0',
            '/xml/security/java-library/xml-security-src-1_0_5D2.zip': '1_0_5D2',
            '/xml/commons/binaries/xml-commons-external-1.4.01-bin.zip': '1.4.01',
            '/xml/commons/xml-commons-1.0.b2.zip': '1.0.b2',
            '/xml/cocoon/3.0/cocoon-all-3.0.0-alpha-1-dist.tar.gz': '3.0.0-alpha-1',
            '/xerces/j/source/Xerces-J-tools.2.10.0-xml-schema-1.1-beta.tar.gz': '2.10.0',
            '/xerces/c/3/binaries/xerces-c-3.1.1-x86_64-solaris-cc-5.10.tar.gz': '3.1.1',
            '/xerces/c/3/binaries/xerces-c-3.1.1-x86_64-windows-vc-8.0.zip': '3.1.1',
            '/xerces/c/2/binaries/xerces-c_2_8_0-x86-windows-vc_7_1.zip': '2_8_0',
            '/ws/woden/1.0M8/apache-woden-src-1.0M8.tar.gz': '1.0M8',
            '/ws/scout/0_7rc1/source/scout-0.7rc1-src.zip': '0.7rc1',
            '/ws/juddi/3_0/juddi-portal-bundle-3.0.0.rc1.zip': '3.0.0.rc1',
            '/ws/juddi/3_0/juddi-portal-bundle-3.0.0.beta.zip': '3.0.0.beta',
            '/ws/juddi/2_0RC7/juddi-tomcat-2.0rc7.zip': '2.0rc7',
            '/ws/axis2/tools/1_4_1/axis2-wsdl2code-maven-plugin-1.4.1.jar': '1.4.1',
            '/ws/axis/1_4/axis-src-1_4.zip': '1_4',
            '/tuscany/java/sca/2.0-M5/apache-tuscany-sca-all-2.0-M5-src.tar.gz': '2.0-M5',
            '/ws/axis-c/source/win32/axis-c-1.6b-Win32-trace-src.zip': '1.6b',
            '/turbine/turbine-2.3.3-rc1/source/turbine-2.3.3-RC1-src.zip': '2.3.3-RC1',
            '/tomcat/tomcat-connectors/jk/binaries/win64/jk-1.2.30/ia64/symbols-1.2.30.zip': '1.2.30',
            '/tomcat/tomcat-7/v7.0.0-beta/bin/apache-tomcat-7.0.0-windows-i64.zip': '7.0.0',
            '/tomcat/tomcat-4/v4.1.40/bin/apache-tomcat-4.1.40-LE-jdk14.exe': '4.1.40',
            '/tapestry/tapestry-src-5.1.0.5.tar.gz': '5.1.0.5',
            '/spamassassin/source/Mail-SpamAssassin-rules-3.3.0.r901671.tgz': '3.3.0.r901671',
            '/spamassassin/Mail-SpamAssassin-rules-3.3.1.r923257.tgz': '3.3.1.r923257',
            '/shindig/1.1-BETA5-incubating/shindig-1.1-BETA5-incubating-source.zip': '1.1-BETA5',
            '/servicemix/nmr/1.0.0-m3/apache-servicemix-nmr-1.0.0-m3-src.tar.gz': '1.0.0-m3',
            '/qpid/0.6/qpid-dotnet-0-10-0.6.zip': '0.6',
            '/openjpa/2.0.0-beta/apache-openjpa-2.0.0-beta-binary.zip': '2.0.0-beta',
            '/myfaces/source/portlet-bridge-2.0.0-alpha-2-src-all.tar.gz': '2.0.0-alpha-2',
            '/myfaces/source/myfaces-extval20-2.0.3-src.tar.gz': '2.0.3',
            '/geronimo/eclipse/updates/plugins/org.apache.geronimo.st.v21.ui_2.1.1.jar': '2.1.1',
            '/directory/studio/update/1.x/plugins/org.apache.directory.studio.aciitemeditor_1.5.2.v20091211.jar': '1.5.2.v20091211',
            '/db/torque/torque-3.3/source/torque-gen-3.3-RC3-src.zip': '3.3-RC3',
            '/cayenne/cayenne-3.0B1.tar.gz': '3.0B1',
            '/cayenne/cayenne-3.0M4-macosx.dmg': '3.0M4',
            '/xmlgraphics/batik/batik-docs-current.zip': 'current',
            '/xmlgraphics/batik/batik-docs-previous.zip': 'previous',
            '/poi/dev/bin/poi-bin-3.7-beta1-20100620.zip': '3.7-beta1-20100620',
            '/excalibur/avalon-logkit/source/excalibur-logkit-2.0.dev-0-src.zip': '2.0.dev-0',
            '/db/derby/db-derby-10.4.2.0/derby_core_plugin_10.4.2.zip': '10.4.2',
            '/httpd/modpython/win/2.7.1/mp152dll.zip': '2.7.1',
            '/perl/mod_perl-1.31/apaci/mod_perl.config.sh': '1.31',
            '/xml/xerces-j/old_xerces2/Xerces-J-bin.2.0.0.alpha.zip': '2.0.0.alpha',
            '/xml/xerces-p/archives/XML-Xerces-1.7.0_0.tar.gz': '1.7.0_0',
            '/httpd/docs/tools-2004-05-04.zip': '2004-05-04',
            '/ws/axis2/c/M0_5/axis2c-src-M0.5.tar.gz': 'M0.5',
            '/jakarta/poi/dev/src/jakarta-poi-1.8.0-dev-src.zip': '1.8.0-dev',
            '/tapestry/tapestry-4.0-beta-8.zip': '4.0-beta-8',
            '/openejb/3.0-beta-1/openejb-3.0-beta-1.zip': '3.0-beta-1',
            '/tapestry/tapestry-4.0-rc-1.zip': '4.0-rc-1',
            '/jakarta/tapestry/source/3.0-rc-3/Tapestry-3.0-rc-3-src.zip': '3.0-rc-3',
            '/jakarta/lucene/binaries/lucene-1.3-final.tar.gz': '1.3-final',
            '/jakarta/tapestry/binaries/3.0-beta-1a/Tapestry-3.0-beta-1a-bin.zip': '3.0-beta-1a',
            '/poi/release/bin/poi-bin-3.0-FINAL-20070503.tar.gz': '3.0-FINAL-20070503',
            '/harmony/milestones/M4/apache-harmony-hdk-r603534-linux-x86-32-libstdc++v6-snapshot.tar.gz': 'r603534',
            '/ant/antidote/antidote-20050330.tar.bz2': '20050330',
            '/apr/not-released/apr_20020725223645.tar.gz': '20020725223645',
            '/ibatis/source/ibatis.net/src-revision-709676.zip': 'revision-709676',
            '/ws/axis-c/source/win32/axis-c-src-1-2-win32.zip': '1-2',
            '/jakarta/slide/most-recent-2.0rc1-binaries/jakarta-slide 2.0rc1 jakarta-tomcat-4.1.30.zip': '2.0rc1',
            '/httpd/modpython/win/3.0.1/python2.2.1-apache2.0.43.zip': '2.2.1',
            '/ant/ivyde/updatesite/features/org.apache.ivy.feature_2.1.0.cr1_20090319213629.jar': '2.1.0.cr1_20090319213629',
            '/jakarta/poi/dev/bin/poi-2.0-pre1-20030517.jar': '2.0-pre1-20030517',
            '/jakarta/poi/release/bin/jakarta-poi-1.5.0-FINAL-bin.zip': '1.5.0-FINAL',
            '/jakarta/poi/release/bin/poi-bin-2.0-final-20040126.zip': '2.0-final-20040126',
            '/activemq/apache-activemq/5.0.0/apache-activemq-5.0.0-sources.jar': '5.0.0',
            '/turbine/turbine-2.2/source/jakarta-turbine-2.2-B1.tar.gz': '2.2-B1',
            '/ant/ivyde/updatesite/features/org.apache.ivy.feature_2.0.0.cr1.jar': '2.0.0.cr1',
            '/ant/ivyde/updatesite/features/org.apache.ivy.feature_2.0.0.final_20090108225011.jar': '2.0.0.final_20090108225011',
            '/ws/axis/1_2RC3/axis-src-1_2RC3.zip': '1_2RC3',
            '/commons/lang/old/v1.0-b1.1/commons-lang-1.0-b1.1.zip': '1.0-b1.1',
            '/commons/net/binaries/commons-net-1.2.0-release.tar.gz': '1.2.0-release',
            '/ant/ivyde/2.0.0.final/apache-ivyde-2.0.0.final-200907011148-RELEASE.tgz': '2.0.0.final-200907011148-RELEASE',
            '/geronimo/eclipse/updates/plugins/org.apache.geronimo.jetty.j2ee.server.v11_1.0.0.jar': 'v11_1.0.0',
            '/jakarta/cactus/binaries/jakarta-cactus-13-1.7.1-fixed.zip': '1.7.1-fixed',
            '/jakarta/jakarta-turbine-maven/maven/jars/maven-1.0-b5-dev.20020731.085427.jar': '1.0-b5-dev.20020731.085427',
            '/xml/xalan-j/source/xalan-j_2_5_D1-src.tar.gz': '2_5_D1',
            '/ws/woden/IBuilds/I20051002_1145/woden-I20051002_1145.tar.bz2': 'I20051002_1145',
            '/commons/beanutils/source/commons-beanutils-1.8.0-BETA-src.tar.gz': '1.8.0-BETA',
            '/cocoon/BINARIES/cocoon-2.0.3-vm14-bin.tar.gz': '2.0.3-vm14',
            '/felix/xliff_filters_v1_2_7_unix.jar': 'v1_2_7',
            '/excalibur/releases/200702/excalibur-javadoc-r508111-15022007.tar.gz': 'r508111-15022007',
            '/geronimo/eclipse/updates/features/org.apache.geronimo.v20.feature_2.0.0.jar': 'v20.feature_2.0.0',
            '/geronimo/2.1.6/axis2-jaxws-1.3-G20090406.jar': '1.3-G20090406',
            '/cassandra/debian/pool/main/c/cassandra/cassandra_0.4.0~beta1-1.diff.gz': '0.4.0~beta1',
            '/ha-api-3.1.6.jar': '3.1.6',
            'ha-api-3.1.6.jar': '3.1.6',
            'fryPOS_20070919.exe': '20070919',
        }
        self.version_tester(versions)

    def test_versions_with_7z_extensions(self):
        versions = {
            'http://heanet.dl.sourceforge.net/project/imadering/Imadering_500_211.7z': '500_211',
            'http://cznic.dl.sourceforge.net/project/lttty/LtTTY/LtTTY-0.6.0.2/lttty-src-0.602.7z': '0.602',
            '/some/MPlayerGUI_0_6_79.7z': '0_6_79',
            'http://heanet.dl.sourceforge.net/project/qsubedit/0-2-1-23/QSubEdit-win32-0-2-1-23.7z': '0-2-1-23',
            'http://sourceforge.net/projects/vgmtoolbox/files/vgmtoolbox/VGMToolbox%20r930/vgmtoolbox_bin_r930.7z': 'r930',
            'blah/XMTunerSource-0-6-4.7z': '0-6-4',
        }
        self.version_tester(versions)

    def test_versions_of_debs_and_rpms(self):
        versions = {
            'bartlby-agent_1.2.3-1_i386.deb': '1.2.3',
            'milestones/6.0/debian/amd64/harmony-6.0-classlib_0.0r946981-1_amd64.deb': '6.0',
            'bartlby-extensions_1.2.3-12_amd64.deb': '1.2.3',
            'bashish-2.0.4.tar.gz': '2.0.4',
            'bashish_2.0.4-1_all.deb': '2.0.4',
            'bashish-2.0.4-1.bashish.generic.noarch.rpm': '2.0.4',
            'bbbike_3.18-1_i386.deb': '3.18',
            'bbbike_3.18-1_amd64.deb': '3.18',
            'blueproximity-1.2.4.tar.gz': '1.2.4',
            'blueproximity_1.2.4-0ubuntu1_feisty1_all.deb': '1.2.4',
            'blueproximity_1.2.4-0ubuntu1_all.deb': '1.2.4',
            'blueproximity-1.2.4-1.fc8.noarch.rpm': '1.2.4',
            'blueproximity-1.2.4-1.2_opensuse10_2.noarch.rpm': '1.2.4',
            'blueproximity-1.2.4-1.2_opensuse10_3.noarch.rpm': '1.2.4',
            'blueproximity-1.2.4-12.1_opensuse10_3.x86_64.rpm': '1.2.4',
            'blueproximity-1.2.4-12.1_opensuse10_3.i586.rpm': '1.2.4',
            'blueproximity-1.2.4-13.1_upensuse10_2.x86_64.rpm': '1.2.4',
            'blueproximity-1.2.4-13.1_opensuse10_2.i586.rpm': '1.2.4',
            'blueproximity-1.2.4-14.1_opensuse10_3.noarch.rpm': '1.2.4',
            'blueproximity-1.2.4-14.1_opensuse10_2.noarch.rpm': '1.2.4',
            'blueproximity-1.2.4-2.fc8.noarch.rpm': '1.2.4',
            'bpmcalc4amarok_0.1.2-1_all.deb': '0.1.2',
            'bpmcalc4amarok_0.1.2-1.diff.gz': '0.1.2',
        }
        self.version_tester(versions)

    def test_versions_without_rc_alpha_beta(self):
        versions = {
            '/commons/beanutils/source/commons-beanutils-1.8.0-BETA-src.tar.gz': '1.8.0',
            '/cassandra/debian/pool/main/c/cassandra/cassandra_0.4.0~beta1-1.diff.gz': '0.4.0',
            '/xmlgraphics/batik/batik-src-1.7beta1.zip': '1.7',
            '/xml/cocoon/3.0/cocoon-all-3.0.0-alpha-1-dist.tar.gz': '3.0.0',
            '/ws/scout/0_7rc1/source/scout-0.7rc1-src.zip': '0.7',
            '/ws/juddi/3_0/juddi-portal-bundle-3.0.0.rc1.zip': '3.0.0',
            '/ws/juddi/3_0/juddi-portal-bundle-3.0.0.beta.zip': '3.0.0',
            '/ws/juddi/2_0RC7/juddi-tomcat-2.0rc7.zip': '2.0',
            '/turbine/turbine-2.3.3-rc1/source/turbine-2.3.3-RC1-src.zip': '2.3.3',
            '/jakarta/slide/most-recent-2.0rc1-binaries/jakarta-slide 2.0rc1 jakarta-tomcat-4.1.30.zip': '2.0',
            '/jakarta/poi/dev/bin/poi-2.0-pre1-20030517.jar': '2.0',
            '/ws/axis/1_2RC3/axis-src-1_2RC3.zip': '1_2',
            '/ws/axis-c/source/win32/axis-c-1.6b-Win32-trace-src.zip': '1.6b',
            '/xml/commons/xml-commons-1.0.b2.zip': '1.0',
            '/commons/lang/old/v1.0-b1.1/commons-lang-1.0-b1.1.zip': '1.0',
            '/turbine/turbine-2.2/source/jakarta-turbine-2.2-B1.tar.gz': '2.2',
        }
        self.version_tester(versions, ignore_pre_releases=True)

    def test_versions_libpng(self):
        versions = {
            'libpng-1.0.16rc3-config.tar.gz': '1.0.16',
            'libpng-1.0.16rc4-config.tar.gz': '1.0.16',
            'libpng-1.0.16rc5-config.tar.gz': '1.0.16',
            'libpng-1.0.17rc1-config.tar.gz': '1.0.17',
            'libpng-1.0.18rc1-config.tar.gz': '1.0.18',
            'libpng-1.0.18rc1.tar.gz': '1.0.18',
            'libpng-1.2.17rc3-no-config.tar.gz': '1.2.17',
            'libpng-1.2.17rc4-no-config.tar.gz': '1.2.17',
            'libpng-1.2.19beta1-no-config.tar.gz': '1.2.19',
            'libpng-1.2.19beta12-no-config.tar.gz': '1.2.19',
        }
        self.version_tester(versions, ignore_pre_releases=True)

    def test_versions_corner_cases(self):
        versions = {
            '/bar/zaiko_2013-03-14_192300.7z': '2013-03-14_192300',
        }
        self.version_tester(versions)

    @expectedFailure
    def test_versions_corner_cases2(self):
        versions = {
            'foo/InstallXMTuner0-6-4.msi': '0-6-4',
            '/harmony/milestones/6.0/debian/amd64/harmony-6.0-classlib_0.0r946981-1_amd64.deb': '0.0r946981-1',
        }
        self.version_tester(versions)
