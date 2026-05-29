# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import json

from cyclonedx.model import bom as cdx_bom
from cyclonedx.model import component as cdx_component
from cyclonedx.output import OutputFormat
from cyclonedx.output import make_outputter
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator

from purldb_project import __version__ as purldb_version


def get_cyclonedx_bom(package):
    """
    Return a CycloneDX `Bom` object filled with provided `project` data.
    See https://cyclonedx.org/use-cases/#dependency-graph
    """

    component = package.as_cyclonedx()

    bom = cdx_bom.Bom()
    bom.metadata = cdx_bom.BomMetaData(
        component=component,
        tools=[
            cdx_bom.Tool(
                name="PurlDB",
                version=purldb_version,
            )
        ],
    )
    bom.components.add(component)

    dependencies = []
    for dependency in package.dependencies.all():
        dc = cdx_component.Component(name="", bom_ref=dependency.purl)
        dependencies.append(dc)
        bom.components.add(dc)
    bom.register_dependency(component, dependencies)

    return bom


def sort_bom_with_schema_ordering(bom_as_dict, schema_version):
    """Sort the ``bom_as_dict`` using the ordering from the ``schema_version``."""
    schema_file = JsonStrictValidator(schema_version)._schema_file
    with open(schema_file) as sf:
        schema_dict = json.loads(sf.read())

    order_from_schema = list(schema_dict.get("properties", {}).keys())
    ordered_dict = {key: bom_as_dict.get(key) for key in order_from_schema if key in bom_as_dict}

    return ordered_dict


def to_cyclonedx(package, cyclonedx_version="1.6"):
    """
    Generate output for the provided ``project`` in CycloneDX BOM format.
    The output file is created in the ``project`` "output/" directory.
    Return the path of the generated output file.
    """
    schema_version = SchemaVersion.from_version(cyclonedx_version)

    bom = get_cyclonedx_bom(package)
    json_outputter = make_outputter(bom, OutputFormat.JSON, schema_version)

    # Using the internal API in place of the output_as_string() method to avoid
    # a round of deserialization/serialization while fixing the field ordering.
    json_outputter.generate()
    bom_as_dict = json_outputter._bom_json

    # The default order out of the outputter is not great, the following sorts the
    # bom using the order from the schema.
    sorted_bom_as_dict = sort_bom_with_schema_ordering(bom_as_dict, schema_version)

    return sorted_bom_as_dict
