#
#  Copyright (c) nexB Inc. and others. All rights reserved.
#


import logging
import posixpath

from lxml import etree

logger = logging.getLogger(__name__)

"""
Helps to parse 'primary.xml', 'other.xml' and 'filelists.xml' of a given repo.
"""


def remove_list_repetitions(input_list):
    """Remove the repeated items in a list and return a list with unique values"""
    output = []
    for item in input_list:
        if item not in output:
            output.append(item)
    return output


def combine_dicts_using_pkgid(all_dicts):
    """
    'all_dicts' is a list of dictionaries.
    This function combines dictionaries with the same 'pkgid' and returns a
    list of all the combined dictionaries.
    """
    all_package_info = []
    for package_info in all_dicts:
        if package_info["pkgid"]:
            all_package_info.append(
                combine_list_of_dicts(
                    [a for a in all_dicts if a["pkgid"] == package_info["pkgid"]]
                )
            )
    return remove_list_repetitions(all_package_info)


def combine_list_of_dicts(input_dicts):
    """
    Combine a list of dictionaries and return a single dictionary with all the
    keys and values from all the dictionaries in the list.
    """
    all_dict_items = []
    for each_dict in input_dicts:
        all_dict_items.extend(each_dict.items())
    return dict(all_dict_items)


def convert_tuples_to_dict(input, attr_name=None):
    """
    'input' - list of tuples each contains ONLY TWO elements.
    Return a dictionary from a list of tuples and append 'attr_name' if
    provided.
    """
    infos = {}
    if input:
        if not attr_name:
            attr_name = ""
        else:
            attr_name = "_" + attr_name
        for attrib, value in input:
            infos[attrib + attr_name] = value
    return infos


def is_absolute(url):
    """Return 'True' if the URL is absolute."""
    schemes = ("http://", "ftp://", "https://")
    return url.startswith(schemes)


def build_rpm_download_url(base_url, href):
    """
    Return a download URL from a 'base_url' and an 'href', if 'href' is an
    absolute URL it is returned as is and the rest is ignored.
    """
    if is_absolute(href):
        return href
    if href.startswith("/"):
        href = href.lstrip("/")
    return posixpath.join(base_url, href)


def get_tag_text(tag):
    """
    Given a 'tag' in the format <name>some_name</name>, return 'some_name' as a
    string.<si
    """
    if tag is not None:
        return tag.text


def get_url_for_tag(location, data_type):
    """
    Parse a repomd.xml file at 'location' and return the relative URL corresponding to this data_type.

    This is an example of a repomd file (a single tag)
    <data type="filelists">
        <checksum type="sha256">32879b869d22802a7771ca920ffd7bac14412cbdf95639b5d5532c261fa5ceff</checksum>
        <open-checksum type="sha256">ec5d1ae9bd5128129c3509b8f9b502cf2cbfdef53ec9f7b9af8b0a467554719e</open-checksum>
        <location href="repodata/32879b869d22802a7771ca920ffd7bac14412cbdf95639b5d5532c261fa5ceff-filelists.xml.gz"/>
        <timestamp>1449374697</timestamp>
        <size>39529</size>
        <open-size>345725</open-size>
    </data>
    """
    repomd = etree.parse(location).getroot()
    for data_tag in repomd.findall("{http://linux.duke.edu/metadata/repo}data"):
        for attrib, value in data_tag.items():
            if attrib == "type" and value == data_type:
                download_location = data_tag.find(
                    "{http://linux.duke.edu/metadata/repo}location"
                )
                relative_url_info = convert_tuples_to_dict(
                    download_location.items(), "location"
                )
                if relative_url_info:
                    return relative_url_info["href_location"]


def get_value_from_tuple_pairs(tuples, key):
    for tuple in tuples:
        if tuple[0] == key:
            return tuple[1]


def filelistsxml_parser(location):
    """
    Parse filelists.xml file and yield the data needed to generate RPM objects.

    <filelists xmlns="http://linux.duke.edu/metadata/filelists" packages="384">
        <package pkgid="36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5" name="python-ceilometerclient" arch="src">
        <version epoch="0" ver="1.5.0" rel="1.el7"/>
        <file>python-ceilometerclient-1.5.0.tar.gz</file>
        <file>python-ceilometerclient.spec</file>
        </package>
    </filelists>

    This function yields a list of the form
    [
    ('pkgid','36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5'),
    ('name','python-ceilometerclient'),
    ('ver','1.5.0')
    ]
    """
    infos = []
    filelistsxml = etree.parse(location).getroot()
    for package in filelistsxml.findall(
        "{http://linux.duke.edu/metadata/filelists}package"
    ):
        version = package.find("{http://linux.duke.edu/metadata/filelists}version")
        package_info = dict(package.items() + version.items())
        directory_listing = package.findall(
            "{http://linux.duke.edu/metadata/filelists}file"
        )
        directories = []
        files = []
        for name in directory_listing:
            items = name.items()
            if items:
                file_type = get_value_from_tuple_pairs(items, "type")
                if file_type == "dir":
                    directories.append({"name": name.text})
            else:
                files.append({"name": name.text})
        package_info["directories"] = directories
        package_info["files"] = files
        infos.append(package_info)
    return infos


def primaryxml_parser(location):
    """
    Parse primary.xml file and yield the data needed to generate RPM objects.

    <package type="rpm">
        <checksum type="sha256" pkgid="YES">36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5</checksum>
        <location href="python-ceilometerclient-1.5.0-1.el7.src.rpm"/>
        <format>
        <rpm:license>ASL 2.0</rpm:license>
        </format>
    </package>

    This function yields a list of the form
    [
    ('checksum','36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5'),
    ('location','python-ceilometerclient-1.5.0-1.el7.src.rpm'),
    ('license','ASL 2.0')
    ]
    """
    pkgs_infos = []
    primaryxml = etree.parse(location).getroot()
    for package in primaryxml.findall("{http://linux.duke.edu/metadata/common}package"):
        package_info = dict(package.items())
        tags_infos = []
        description = package.find("{http://linux.duke.edu/metadata/common}description")
        summary = package.find("{http://linux.duke.edu/metadata/common}summary")
        packager = package.find("{http://linux.duke.edu/metadata/common}packager")
        url = package.find("{http://linux.duke.edu/metadata/common}url")
        size = package.find("{http://linux.duke.edu/metadata/common}size")
        time = package.find("{http://linux.duke.edu/metadata/common}time")
        download_location = package.find(
            "{http://linux.duke.edu/metadata/common}location"
        )
        checksum = package.find("{http://linux.duke.edu/metadata/common}checksum")

        rpm_format = package.find("{http://linux.duke.edu/metadata/common}format")
        buildhost = rpm_format.find("{http://linux.duke.edu/metadata/rpm}buildhost")
        rpm_group = rpm_format.find("{http://linux.duke.edu/metadata/rpm}group")
        header_range = rpm_format.find(
            "{http://linux.duke.edu/metadata/rpm}header-range"
        )
        rpm_license = rpm_format.find("{http://linux.duke.edu/metadata/rpm}license")
        rpm_vendor = rpm_format.find("{http://linux.duke.edu/metadata/rpm}vendor")
        source_rpm = rpm_format.find("{http://linux.duke.edu/metadata/rpm}sourcerpm")

        package_info["description"] = get_tag_text(description)
        package_info["summary"] = get_tag_text(summary)
        package_info["url"] = get_tag_text(url)
        package_info["checksum"] = get_tag_text(checksum)
        package_info["pkgid"] = get_tag_text(checksum)
        package_info["buildhost"] = get_tag_text(buildhost)
        package_info["group"] = get_tag_text(rpm_group)
        package_info["license"] = get_tag_text(rpm_license)
        package_info["sourcerpm"] = get_tag_text(source_rpm)
        tags_infos.append(convert_tuples_to_dict(packager.items(), "packager"))
        tags_infos.append(convert_tuples_to_dict(size.items(), "size"))
        tags_infos.append(convert_tuples_to_dict(time.items(), "time"))
        tags_infos.append(convert_tuples_to_dict(download_location.items()))
        tags_infos.append(convert_tuples_to_dict(header_range.items(), "header_range"))
        tags_infos.append(convert_tuples_to_dict(rpm_vendor.items(), "vendor"))

        requires = rpm_format.find("{http://linux.duke.edu/metadata/rpm}requires")
        provides = rpm_format.find("{http://linux.duke.edu/metadata/rpm}provides")
        if requires is not None:
            required_rpms = [convert_tuples_to_dict(rpm.items()) for rpm in requires]
            package_info["required_rpms"] = required_rpms
        if provides is not None:
            provided_rpms = [convert_tuples_to_dict(rpm.items()) for rpm in provides]
            package_info["provided_rpms"] = provided_rpms

        package_info = combine_list_of_dicts([package_info] + tags_infos)
        pkgs_infos.append(package_info)
    return pkgs_infos


def otherxml_parser(location):
    """
    Parse other.xml file and yield the data needed to generate RPM objects.

    <package pkgid="36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5" name="python-ceilometerclient" arch="src">
        <version epoch="0" ver="1.5.0" rel="1.el7"/>
    </package>

    This function yields a list of the form
    [
    ('ver','1.5.0'),
    ('rel','1.el7'),
    ('epoch','0')
    ]
    """
    otherxml = etree.parse(location).getroot()
    infos = []
    for package in otherxml.findall("{http://linux.duke.edu/metadata/other}package"):
        version = package.find("{http://linux.duke.edu/metadata/other}version")
        package_info = dict(package.items() + version.items())
        changelogs = package.findall("{http://linux.duke.edu/metadata/other}changelog")
        package_info["changelogs"] = []
        for changelog in changelogs:
            if changelog.items():
                change_info = convert_tuples_to_dict(changelog.items())
                change_info["changelog"] = changelog.text
                package_info["changelogs"].append(change_info)
            else:
                package_info["changelogs"].append({"changelog": changelog.text})
        infos.append(package_info)
    return infos


def get_pkg_infos(filelists_xml, primary_xml, other_xml):
    primaryxml_dicts = primaryxml_parser(primary_xml)
    otherxml_dicts = otherxml_parser(other_xml)
    filelistsxml_dicts = filelistsxml_parser(filelists_xml)

    return combine_dicts_using_pkgid(
        primaryxml_dicts + otherxml_dicts + filelistsxml_dicts
    )
