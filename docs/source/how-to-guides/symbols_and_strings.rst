.. _symbols_and_strings:

=======================================================
Collect symbols and strings from a PURL aka. purl2sym
=======================================================

In this tutorial we introduce the different addon pipelines used for collecting symbols and strings
from codebase resources.

.. note::
    This tutorial assumes that you have a working installation of PurlDB.
    If you don't, please refer to the `installation <../how-to-guides/installation.html#installation>`_ page.


Problem
----------------

The identification of the corresponding source code compiled in native compiled binaries such as
ELF, Mach-O or PE/COFF binaries is complex and important: only by knowing the code origin can one
know if this code is subject to known vulnerabilities or if there is licensing conflict. The
majority of code in IoT and embedded devices is composed of natively compiled binaries, though there
is of course a significant Android-based ecosystem using Java with specific constraints: multiple
programming languages (Java and Kotlin) and bytecode compiled binaries. Many devices also embed
secondary code (typically for admin an UI) such as  Lua, JavaScript, Python or PHP.

Solution
---------

To help with identification of binaries it is important to aggregate collection of identifiers and
symbols from FOSS code and index them such that they can be easily retrieved to built efficient
detection engines, such as based on automatons and binary scanners.

The symbols and strings or "purl2sym" feature is API-based and works this way:

    1. The workflow starts with an initial request for a Package URL or a download URL, or a
    fragment of PURL. The tool then assembles the list of all known versions for this package,
    possibly filtered for a version range (using a PURL "vers" expression) and returns a list
    containing all known PURLs for the package satisfying these requirements. This is part of the
    standard APIs from PurlDB and the purlcli command line tool. For instance a typical request may
    be equivalent tp "Get all PURLs for BusyBox".

    2. For each of the results one can then send a new request for just that PURL. For instance a
    typical request may be "Get all the symbols for busybox 1.21.0. and 1.22.0".

    3. PurlDB returns a JSON API response with the list of PURLs and URLs being processed and their
    collection status. This response includes readily available, already collected symbols.

    4. For each of the results of step 1 for which there are no results yet the tool fetches and
    store the corresponding code archives, then extracts the archives and run multiple tools to
    extract the actual identifiers, symbols  and strings and store them.

The type of symbols and identifiers to collect include:

    - Strings and literals (for instance collected using xgettext).

    - Code symbols such as function names, variable names, method names, class names, etc. extracted
      with various programming language-aware parsers such as ctags, tree-sitter or Pygments.


The collected symbols are stored at the the level of each file of a package, with additional
existing file-level attributes such as the detected file type or programming language and are
available in the extra_data section of the results.


Symbols and strings use cases
-----------------------------------

Why would you collect symbols and strings? Taken alone, symbols and strings are not very
interesting. Instead, they are the building blocks of important and useful workflows and processes
to support the binary analysis (and in some cases the source analysis).

Here are some examples of the applications made possible when collecting symbols and strings:

Binary analysis
~~~~~~~~~~~~~~~~

Once we have collected symbols and strings from the source code, we can search these in a binary.
The presence of these symbols in the binaries can be used to find the origin of code complied in
binaries with a lightweight "reverse" engineering process. For instance, a tool like BANG
<https://github.com/armijnhemel/binaryanalysis-ng/>_ can use the source symbols to build
automatons-based search indexes to support an efficient binary origin analysis.


Binary to source mapping, aka. back2source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In another context, we can use the collected source symbols and strings to map these to the
binaries assumed to be built from these sources and validate that we have the complete and
corresponding source code for a build binary software.


Code search
~~~~~~~~~~~~~~

We can use symbols and strings to build efficient source code search indexes that are focusing on
the essence of the source code and are more readily amenable to indexing that raw source code.
The set of source code symbols and strings is akin to an essential fingerprint for the code.


Vulnerable code reachability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If we can determine the vulnerable code commit or patch that introduced or fixed a vulnerability,
we can then extract the symbols and strings from this commit or patch. We can then combine this
with binary analysis to deternmine of the vulnerable code may be present or called in a codebase
or binary that reuse this vulnerable component.


Code cross-references
~~~~~~~~~~~~~~~~~~~~~~~~~~

Symbols and strings can be used to build cross reference indexes of a large source code base to
help navigate and understand the structure of the codebase. They are routinely used in code editors
and IDEs to support this navigation.


Tutorial
----------


Through out this tutorial we will use ``pkg:github/llvm/llvm-project@10.0.0`` and will show
the symbol and string for `llvm-project/clang/lib/Basic/Targets/BPF.cpp
<https://github.com/llvm/llvm-project/blob/llvmorg-10.0.0/clang/lib/Basic/Targets/BPF.cpp>`_
resource.

.. raw:: html

   <details>
   <summary><a>BPF.cpp</a></summary>
   </br>

.. code-block:: cpp

    //===--- BPF.cpp - Implement BPF target feature support -------------------===//
    //
    // Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
    // See https://llvm.org/LICENSE.txt for license information.
    // SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
    //
    //===----------------------------------------------------------------------===//
    //
    // This file implements BPF TargetInfo objects.
    //
    //===----------------------------------------------------------------------===//

    #include "BPF.h"
    #include "Targets.h"
    #include "clang/Basic/MacroBuilder.h"
    #include "clang/Basic/TargetBuiltins.h"
    #include "llvm/ADT/StringRef.h"

    using namespace clang;
    using namespace clang::targets;

    const Builtin::Info BPFTargetInfo::BuiltinInfo[] = {
    #define BUILTIN(ID, TYPE, ATTRS)                                               \
      {#ID, TYPE, ATTRS, nullptr, ALL_LANGUAGES, nullptr},
    #include "clang/Basic/BuiltinsBPF.def"
    };

    void BPFTargetInfo::getTargetDefines(const LangOptions &Opts,
                                        MacroBuilder &Builder) const {
      Builder.defineMacro("__bpf__");
      Builder.defineMacro("__BPF__");
    }

    static constexpr llvm::StringLiteral ValidCPUNames[] = {"generic", "v1", "v2",
                                                            "v3", "probe"};

    bool BPFTargetInfo::isValidCPUName(StringRef Name) const {
      return llvm::find(ValidCPUNames, Name) != std::end(ValidCPUNames);
    }

    void BPFTargetInfo::fillValidCPUList(SmallVectorImpl<StringRef> &Values) const {
      Values.append(std::begin(ValidCPUNames), std::end(ValidCPUNames));
    }

    ArrayRef<Builtin::Info> BPFTargetInfo::getTargetBuiltins() const {
      return llvm::makeArrayRef(BuiltinInfo, clang::BPF::LastTSBuiltin -
                                                Builtin::FirstTSBuiltin);
    }

.. raw:: html

   </details>
   </br>


Ctags Symbols
-------------

- Send GET request to PurlDB with::

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_symbols_ctags

.. warning::
    The ``collect_symbols_ctags`` pipeline requires ``universal-ctags``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` for resources.

.. code-block:: json
  :caption: Ctags symbol for ``clang/lib/Basic/Targets/BPF.cpp`` in ``extra_data`` field
  :emphasize-lines: 35-41

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/lib/Basic/Targets/BPF.cpp",
        "type": "file",
        "name": "BPF.cpp",
        "extension": ".cpp",
        "size": 1788,
        "md5": "382b406d1023d12cd8f28106043774ee",
        "sha1": "366146c8228c4e2cd46c47618fa3211ce48d96e2",
        "sha256": "d7609c502c7d462dcee1b631a80eb765ad7d10597991d88c3d4cd2ae0370eeba",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c",
        "file_type": "C source, ASCII text",
        "programming_language": "C++",
        "is_binary": false,
        "is_text": true,
        "is_archive": false,
        "is_media": false,
        "is_key_file": false,
        "detected_license_expression": "",
        "detected_license_expression_spdx": "",
        "license_detections": [],
        "license_clues": [],
        "percentage_of_license_text": null,
        "copyrights": [],
        "holders": [],
        "authors": [],
        "package_data": [],
        "emails": [],
        "urls": [],
        "extra_data": {
            "source_symbols": [
                "BUILTIN",
                "BuiltinInfo",
                "ValidCPUNames",
                "fillValidCPUList",
                "getTargetBuiltins",
                "getTargetDefines",
                "isValidCPUName"
            ]
        }
    }


Xgettext Strings
----------------

- Send GET request to PurlDB with::

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_strings_gettext

.. warning::
    The ``collect_strings_gettext`` pipeline requires ``gettext``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_strings`` for resources.

.. code-block:: json
  :caption: Xgettext strings for ``clang/lib/Basic/Targets/BPF.cpp`` in ``extra_data`` field
  :emphasize-lines: 35-41

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/lib/Basic/Targets/BPF.cpp",
        "type": "file",
        "name": "BPF.cpp",
        "extension": ".cpp",
        "size": 1788,
        "md5": "382b406d1023d12cd8f28106043774ee",
        "sha1": "366146c8228c4e2cd46c47618fa3211ce48d96e2",
        "sha256": "d7609c502c7d462dcee1b631a80eb765ad7d10597991d88c3d4cd2ae0370eeba",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c",
        "file_type": "C source, ASCII text",
        "programming_language": "C++",
        "is_binary": false,
        "is_text": true,
        "is_archive": false,
        "is_media": false,
        "is_key_file": false,
        "detected_license_expression": "",
        "detected_license_expression_spdx": "",
        "license_detections": [],
        "license_clues": [],
        "percentage_of_license_text": null,
        "copyrights": [],
        "holders": [],
        "authors": [],
        "package_data": [],
        "emails": [],
        "urls": [],
        "extra_data": {
            "source_strings": [
                "__bpf__",
                "__BPF__",
                "generic",
                "v",
                "v",
                "v",
                "probe"
            ]
        }
    }

Tree-Sitter Symbols and Strings
-------------------------------

- Send GET request to PurlDB with::

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_symbols_tree_sitter

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` and ``source_strings`` for resources.

.. code-block:: json
  :caption: Tree-Sitter symbols and strings for ``clang/lib/Basic/Targets/BPF.cpp`` in ``extra_data`` field
  :emphasize-lines: 35-69, 72-84

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/lib/Basic/Targets/BPF.cpp",
        "type": "file",
        "name": "BPF.cpp",
        "extension": ".cpp",
        "size": 1788,
        "md5": "382b406d1023d12cd8f28106043774ee",
        "sha1": "366146c8228c4e2cd46c47618fa3211ce48d96e2",
        "sha256": "d7609c502c7d462dcee1b631a80eb765ad7d10597991d88c3d4cd2ae0370eeba",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c",
        "file_type": "C source, ASCII text",
        "programming_language": "C++",
        "is_binary": false,
        "is_text": true,
        "is_archive": false,
        "is_media": false,
        "is_key_file": false,
        "detected_license_expression": "",
        "detected_license_expression_spdx": "",
        "license_detections": [],
        "license_clues": [],
        "percentage_of_license_text": null,
        "copyrights": [],
        "holders": [],
        "authors": [],
        "package_data": [],
        "emails": [],
        "urls": [],
        "extra_data": {
            "source_symbols": [
                "clang",
                "targets",
                "BuiltinInfo",
                "BUILTIN",
                "ID",
                "TYPE",
                "ATTRS",
                "TYPE",
                "ATTRS",
                "ALL_LANGUAGES",
                "getTargetDefines",
                "Opts",
                "Builder",
                "Builder",
                "Builder",
                "ValidCPUNames",
                "isValidCPUName",
                "Name",
                "find",
                "ValidCPUNames",
                "Name",
                "end",
                "ValidCPUNames",
                "fillValidCPUList",
                "Values",
                "Values",
                "begin",
                "ValidCPUNames",
                "end",
                "ValidCPUNames",
                "getTargetBuiltins",
                "makeArrayRef",
                "BuiltinInfo",
                "LastTSBuiltin",
                "FirstTSBuiltin"
            ],
            "source_strings": [
                "BPF.h",
                "Targets.h",
                "clang/Basic/MacroBuilder.h",
                "clang/Basic/TargetBuiltins.h",
                "llvm/ADT/StringRef.h",
                "clang/Basic/BuiltinsBPF.def",
                "__bpf__",
                "__BPF__",
                "generic",
                "v1",
                "v2",
                "v3",
                "probe"
            ]
        }
    }

Pygments Symbols and Strings
-------------------------------

- Send GET request to PurlDB with::

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_symbols_pygments

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` and ``source_strings`` for resources.


.. code-block:: json
  :caption: Pygments symbols and strings for ``clang/lib/Basic/Targets/BPF.cpp`` in ``extra_data`` field
  :emphasize-lines: 35-40, 43-63

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/lib/Basic/Targets/BPF.cpp",
        "type": "file",
        "name": "BPF.cpp",
        "extension": ".cpp",
        "size": 1788,
        "md5": "382b406d1023d12cd8f28106043774ee",
        "sha1": "366146c8228c4e2cd46c47618fa3211ce48d96e2",
        "sha256": "d7609c502c7d462dcee1b631a80eb765ad7d10597991d88c3d4cd2ae0370eeba",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c",
        "file_type": "C source, ASCII text",
        "programming_language": "C++",
        "is_binary": false,
        "is_text": true,
        "is_archive": false,
        "is_media": false,
        "is_key_file": false,
        "detected_license_expression": "",
        "detected_license_expression_spdx": "",
        "license_detections": [],
        "license_clues": [],
        "percentage_of_license_text": null,
        "copyrights": [],
        "holders": [],
        "authors": [],
        "package_data": [],
        "emails": [],
        "urls": [],
        "extra_data": {
            "source_symbols": [
                "clang",
                "clang",
                "targets",
                "BPFTargetInfo::getTargetDefines",
                "BPFTargetInfo::isValidCPUName",
                "BPFTargetInfo::fillValidCPUList"
            ],
            "source_strings": [
                "\"",
                "__bpf__",
                "\"",
                "\"",
                "__BPF__",
                "\"",
                "\"",
                "generic",
                "\"",
                "\"",
                "v1",
                "\"",
                "\"",
                "v2",
                "\"",
                "\"",
                "v3",
                "\"",
                "\"",
                "probe",
                "\""
            ]
        }
    }
