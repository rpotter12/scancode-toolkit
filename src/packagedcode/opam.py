
# Copyright (c) nexB Inc. and others. All rights reserved.
# http://nexb.com and https://github.com/nexB/scancode-toolkit/
# The ScanCode software is licensed under the Apache License version 2.0.
# Data generated with ScanCode require an acknowledgment.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# When you publish or redistribute any data created with ScanCode or any ScanCode
# derivative work, you must accompany this data with the following acknowledgment:
#
#  Generated with ScanCode and provided on an "AS IS" BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, either express or implied. No content created from
#  ScanCode should be considered or used as legal advice. Consult an Attorney
#  for any legal advice.
#  ScanCode is a free software code scanning tool from nexB Inc. and others.
#  Visit https://github.com/nexB/scancode-toolkit/ for support and download.

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import io
import logging
import re

import attr
from packageurl import PackageURL

from commoncode import filetype
from commoncode import fileutils
from packagedcode import models


"""
Handle opam package.
"""

TRACE = False

logger = logging.getLogger(__name__)

if TRACE:
    import sys
    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)


@attr.s()
class OpamPackage(models.Package):
    metafiles = ('*opam',)
    extensions = ('.opam',)
    default_type = 'opam'
    default_primary_language = 'Ocaml'
    default_web_baseurl = 'https://opam.ocaml.org/packages'
    default_download_baseurl = None
    default_api_baseurl = None

    @classmethod
    def recognize(cls, location):
        yield parse(location)

    @classmethod
    def get_package_root(cls, manifest_resource, codebase):
        return manifest_resource.parent(codebase)

    def repository_homepage_url(self, baseurl=default_web_baseurl):
        if self.name:
            return '{}/{}'.format(baseurl, self.name)


def is_opam(location):
    return location.endswith('opam')


def parse(location):
    """
    Return a Package object from a opam file or None.
    """
    if not is_opam(location):
        return

    package_data = parse_opam(location)
    return build_opam_package(package_data)


def build_opam_package(package_data):
    """
    Return a Package from a opam file or None.
    """
    package_dependencies = []
    deps = package_data.get('depends') or []
    for dep in deps:
        package_dependencies.append(
            models.DependentPackage(
                purl=dep.purl,
                requirement=dep.version,
                scope='dependency',
                is_runtime=True,
                is_optional=False,
                is_resolved=False,
            )
        )

    name = package_data.get('name')
    homepage_url = package_data.get('homepage')
    download_url = package_data.get('src')
    vcs_url = package_data.get('dev-repo')
    bug_tracking_url = package_data.get('bug-reports')
    declared_license = package_data.get('license')
    sha1 = package_data.get('sha1')
    md5 = package_data.get('md5')
    sha256 = package_data.get('sha256')
    sha512 = package_data.get('sha512')
    summary = package_data.get('synopsis')
    description = package_data.get('description')
    if summary:
        description = summary
    elif summary and description:
        if len(summary) > len(description):
            description = summary

    parties = []
    authors = package_data.get('authors') or []
    for author in authors:
        parties.append(
            models.Party(
                type=models.party_person,
                name=author,
                role='author'
            )
        )
    maintainers = package_data.get('maintainer') or []
    for maintainer in maintainers:
        parties.append(
            models.Party(
                type=models.party_person,
                email=maintainer,
                role='maintainer'
            )
        )

    package = OpamPackage(
        name=name,
        vcs_url=vcs_url,
        homepage_url=homepage_url,
        download_url=download_url,
        sha1=sha1,
        md5=md5,
        sha256=sha256,
        sha512=sha512,
        bug_tracking_url=bug_tracking_url,
        declared_license=declared_license,
        description=description,
        parties=parties,
        dependencies=package_dependencies
    )

    return package

"""
Example:- 

Sample opam file(sample3.opam):
opam-version: "2.0"
version: "4.11.0+trunk"
synopsis: "OCaml development version"
depends: [
  "ocaml" {= "4.11.0" & post}
  "base-unix" {post}
]
conflict-class: "ocaml-core-compiler"
flags: compiler
setenv: CAML_LD_LIBRARY_PATH = "%{lib}%/stublibs"
build: [
  ["./configure" "--prefix=%{prefix}%"]
  [make "-j%{jobs}%"]
]
install: [make "install"]
maintainer: "caml-list@inria.fr"
homepage: "https://github.com/ocaml/ocaml/"
bug-reports: "https://github.com/ocaml/ocaml/issues"
authors: [
  "Xavier Leroy"
  "Damien Doligez"
  "Alain Frisch"
  "Jacques Garrigue"
] 

>>> p = parse_opam('sample3.opam')
>>> for k, v in p.items():
>>>     print(k, v)

Output:
opam-version 2.0
version 4.11.0+trunk
synopsis OCaml development version
depends [Opam(name='ocaml', version='= 4.11.0 & post'), Opam(name='base-unix', version='post')]
conflict-class ocaml-core-compiler
flags compiler
setenv CAML_LD_LIBRARY_PATH = %{lib}%/stublibs
build 
install make install
maintainer ['caml-list@inria.fr']
homepage https://github.com/ocaml/ocaml/
bug-reports https://github.com/ocaml/ocaml/issues
authors ['Xavier Leroy', 'Damien Doligez', 'Alain Frisch', 'Jacques Garrigue']
"""

@attr.s()
class Opam(object):
    name = attr.ib(default=None)
    version = attr.ib(default=None)

    @property
    def purl(self):
        return PackageURL(
                    type='opam',
                    name=self.name
                ).to_string()


# Regex expressions to parse file lines
parse_file_line = re.compile(
    r'(?P<key>^(.+?))'
    r'\:\s*'
    r'(?P<value>(.*))'
).match

parse_checksum = re.compile(
    r'(?P<key>^(.+?))'
    r'\='
    r'(?P<value>(.*))'
).match

parse_dep = re.compile(
    r'^\s*\"'
    r'(?P<name>[A-z0-9\-]*)'
    r'\"\s*'
    r'(?P<version>(.*))'
).match

"""
Example:
>>> p = parse_file_line('authors: "BAP Team"')
>>> assert p.group('key') == ('authors')
>>> assert p.group('value') == ('"BAP Team"')

>>> p = parse_dep('"bap-std" {= "1.0.0"}')
>>> assert p.group('name') == ('bap-std')
>>> assert p.group('version') == ('{= "1.0.0"}')
"""

def parse_opam(location):
    """
    Return a mapping of package data collected from the opam OCaml package manifest file at `location`.
    """
    with io.open(location, encoding='utf-8') as data:
        lines = data.readlines()

    opam_data = {}

    for i, line in enumerate(lines):
        parsed_line = parse_file_line(line)
        if parsed_line:
            key = parsed_line.group('key').strip()
            value = parsed_line.group('value').strip()
            if key == 'description': # Get multiline description
                value = ''
                for cont in lines[i+1:]:
                    value += ' ' + cont.strip()
                    if '"""' in cont:
                        break

            opam_data[key] = clean_data(value)

            if key == 'maintainer':
                stripped_val = value.strip('["] ')
                stripped_val = stripped_val.split('" "')
                opam_data[key] = stripped_val
            elif key == 'authors':
                if '[' in line: # If authors are present in multiple lines
                    for authors in lines[i+1:]:
                        value += ' ' + authors.strip()
                        if ']' in authors:
                            break
                    value = value.strip('["] ')
                else:
                    value = clean_data(value)   
                value = value.split('" "')
                opam_data[key] = value
            elif key == 'depends': # Get multiline dependencies
                value = []
                for dep in lines[i+1:]:
                    if ']' in dep:
                        break
                    parsed_dep = parse_dep(dep)
                    if parsed_dep:
                        value.append(Opam(
                                name=parsed_dep.group('name').strip(),
                                version=parsed_dep.group('version').strip('{ } ').replace('"', '')
                            )
                        )
                opam_data[key] = value
            elif key == 'src': # Get multiline src
                if not value:
                    value = lines[i+1].strip()
                opam_data[key] = clean_data(value)
            elif key == 'checksum': # Get checksums
                if '[' in line:
                    for checksum in lines[i+1:]:
                        checksum = checksum.strip('" ')
                        if ']' in checksum:
                            break
                        parsed_checksum = parse_checksum(checksum)
                        key = clean_data(parsed_checksum.group('key').strip())
                        value = clean_data(parsed_checksum.group('value').strip())
                        opam_data[key] = value
                else:
                    value = value.strip('" ')
                    parsed_checksum = parse_checksum(value)
                    if parsed_checksum:
                        key = clean_data(parsed_checksum.group('key').strip())
                        value = clean_data(parsed_checksum.group('value').strip())
                        opam_data[key] = value

    return opam_data


def clean_data(data):
    """
    Return data after removing unnecessary special character.
    """
    for strippable in ("'", '"', '[', ']',):
        data = data.replace(strippable, '')

    return data.strip()