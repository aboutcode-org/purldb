#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#


from bs4 import BeautifulSoup
from commoncode.fileutils import file_base_name
from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import URI
from minecode.visitors import HttpVisitor


class GstreamerSeed(seed.Seeder):
    is_active = False

    def get_seeds(self):
        yield "https://gstreamer.freedesktop.org/src/"


@visit_router.route(r"https://gstreamer.freedesktop.org/src/([\w\-\.]+/)*")
class GstreamerHTMLVisitor(HttpVisitor):
    """
    Visit the HTML page of gstreamer. Yield the uri which can be used for the next visitor use or the uri stands for the file resource.
    The regex is to match:
    https://gstreamer.freedesktop.org/src/
    https://gstreamer.freedesktop.org/src/gst-openmax/pre/
    """

    def get_uris(self, content):
        page = BeautifulSoup(content, "lxml")
        url_template = self.uri + "{sub_path}"
        for a in page.find_all(name="a"):
            if "href" not in a.attrs:
                continue
            href = a["href"]
            if href:
                # For parent folder link or other unrelated links, ignore
                if href.startswith("/") or href.startswith("?"):
                    continue
                if href.endswith("/"):
                    # If the path is folder, yield it for the next visitor use.
                    yield URI(
                        uri=url_template.format(sub_path=href), source_uri=self.uri
                    )
                else:
                    # If it's the file resource, form the package_url and yield the URI with package url info
                    # For example: gst-openmax-0.10.0.4.tar.bz2
                    file_name = href
                    file_name_without_prefix = file_base_name(file_name)
                    if "-" in file_name_without_prefix:
                        project_name_versions = file_name.rpartition("-")
                        project_name = project_name_versions[0]
                        version = project_name_versions[-1]
                    else:
                        project_name = file_name
                        version = None
                    package_url = PackageURL(
                        type="gstreamer", name=project_name, version=version
                    ).to_string()
                    yield URI(
                        uri=url_template.format(sub_path=href),
                        package_url=package_url,
                        file_name=file_name,
                        source_uri=self.uri,
                    )
