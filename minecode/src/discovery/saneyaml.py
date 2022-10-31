#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from functools import partial

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
    from yaml import CSafeDumper as SafeDumper
except ImportError:
    from yaml import SafeLoader
    from yaml import SafeDumper


"""
Wrapper around PyYAML to provide sane defaults ensuring that dump/load does not
damage content, keeps ordering, use always block-style and use four spaces
indents to get readable YAML and quotes and folds texts in a sane way.

Use the `load` function to get a primitive type from a YAML string and the
`dump` function to get a YAML string from a primitive type.

Load and dump rely on subclasses of SafeLoader and SafeDumper respectively doing
all the dirty bidding to get PyYAML straight.
"""

# Check:
# https://github.com/ralienpp/reyaml/blob/master/reyaml/__init__.py
# https://pypi.python.org/pypi/PyYAML.Yandex/3.11.1
# https://pypi.python.org/pypi/ruamel.yaml/0.9.1
# https://pypi.python.org/pypi/yaml2rst/0.2


def load(s):
    """
    Return an object safely loaded from YAML string `s`. `s` must be unicode
    or be a string that converts to unicode without errors.
    """
    return yaml.load(s, Loader=SaneLoader)


def dump(obj):
    """
    Return a safe and sane YAML unicode string representation from `obj`.
    """
    return yaml.dump(
        obj,
        Dumper=SaneDumper,
        default_flow_style=False,
        default_style=None,
        canonical=False,
        allow_unicode=True,
        # do not encode as Unicode
        encoding=None,
        indent=4,
        width=90,
        line_break='\n',
        explicit_start=False,
        explicit_end=False,
    )


class SaneLoader(SafeLoader):
    """
    A safe loader configured with many sane defaults.
    """
    def ignore_aliases(self, data):
        return True


def string_loader(loader, node):
    """
    Ensure that a scalar type (a value) is returned as a plain unicode string.
    """
    return loader.construct_scalar(node)


SaneLoader.add_constructor(u'tag:yaml.org,2002:str', string_loader)

# Load as strings most scalar types: nulls, ints, (such as in version
# 01) floats (such version 2.20) and timestamps conversion (in
# versions too) are all emitted as unicode strings. This avoid
# unwanted type conversions for unquoted strings and the resulting
# content damaging. This overrides the implicit resolvers. Callers
# must handle type conversion explicitly from unicode to other types
# in the loaded objects.

SaneLoader.add_constructor(u'tag:yaml.org,2002:null', string_loader)
SaneLoader.add_constructor(u'tag:yaml.org,2002:timestamp', string_loader)
SaneLoader.add_constructor(u'tag:yaml.org,2002:float', string_loader)
SaneLoader.add_constructor(u'tag:yaml.org,2002:int', string_loader)
SaneLoader.add_constructor(u'tag:yaml.org,2002:null', string_loader)

# keep  boolean conversion
# SaneLoader.add_constructor(u'tag:yaml.org,2002:boolean', string_loader)


def ordered_loader(loader, node):
    """
    Ensure that YAML maps ordered is preserved and loaded in an dict now always ordered
    """
    assert isinstance(node, yaml.MappingNode)
    omap = dict()
    yield omap

    for key, value in node.value:
        key = loader.construct_object(key)
        value = loader.construct_object(value)
        omap[key] = value


SaneLoader.add_constructor(u'tag:yaml.org,2002:map', ordered_loader)
SaneLoader.add_constructor(u'tag:yaml.org,2002:omap', ordered_loader)

# Fall back to mapping for anything else, e.g. ignore tags such as
# !!Python, ruby and other dangerous mappings: treat them as a mapping
SaneLoader.add_constructor(None, ordered_loader)


class SaneDumper(SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        """
        Ensure that lists items are always indented.
        """
        return super(SaneDumper, self).increase_indent(flow, indentless=False)

    def ignore_aliases(self, data):
        """
        Avoid having aliases created from re-used Python objects.
        """
        return True


def ordered_dumper(dumper, data):
    """
    Ensure that maps are always dumped in the items order.
    """
    return dumper.represent_mapping(u'tag:yaml.org,2002:map', data.items())


SaneDumper.add_representer(dict, ordered_dumper)


def null_dumper(dumper, value):
    """
    Always dump nulls as empty string.
    """
    return dumper.represent_scalar(u'tag:yaml.org,2002:null', u'')


SafeDumper.add_representer(type(None), null_dumper)


def string_dumper(dumper, value, _tag=u'tag:yaml.org,2002:str'):
    """
    Ensure that all scalars are dumped as UTF-8 unicode, folded and
    quoted in the sanest and most readable way.
    """
    if not isinstance(value, basestring):
        value = repr(value)

    if isinstance(value, str):
        value = value.decode('utf-8')

    style = None
    multilines = '\n' in value
    if multilines:
        literal_style = '|'
        style = literal_style

    return dumper.represent_scalar(_tag, value, style=style)


SaneDumper.add_representer(str, string_dumper)

# treat number as strings, not as numbers
SaneDumper.add_representer(int, partial(string_dumper, _tag=u'tag:yaml.org,2002:int'))
SaneDumper.add_representer(float, partial(string_dumper, _tag=u'tag:yaml.org,2002:float'))


def boolean_dumper(dumper, value):
    """
    Dump booleans as yes or no strings.
    """
    value = u'yes' if value else u'no'
    style = None
    return dumper.represent_scalar(u'tag:yaml.org,2002:bool', value, style=style)


SaneDumper.add_representer(bool, boolean_dumper)
