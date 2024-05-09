.. _tutorial_symbol_and_string_collection:

How To get symbols and strings from a PURL/package
==================================================

In this tutorial we'll introduce the different addon pipeline that can be used for
collecting symbols and strings from codebase resources.

.. note::
    This tutorial assumes that you have a working installation of PurlDB.
    If you don't, please refer to the `installation <../purldb/overview.html#installation>`_ page.


Through out this tutorial we will use ``pkg:github/llvm/llvm-project@10.0.0`` and will show
the symbol and string for `llvm-project/clang/lib/Basic/Targets/BPF.cpp <https://github.com/llvm/llvm-project/blob/llvmorg-10.0.0/clang/lib/Basic/Targets/BPF.cpp>`_
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

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_symbols

.. warning::
    The ``collect_symbols`` pipeline requires ``universal-ctags``.

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

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_source_strings

.. warning::
    The ``collect_source_strings`` pipeline requires ``gettext``.

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

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_tree_sitter_symbols

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

    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_pygments_symbols

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
