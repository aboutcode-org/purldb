.. _tutorial_symbol_and_string_collection:

How To get symbols and strings from a PURL/package
==================================================

In this tutorial we'll introduce the different addon pipeline that can be used for
collecting symbols and strings from codebase resources.

.. note::
    This tutorial assumes that you have a working installation of PurlDB.
    If you don't, please refer to the `installation <../purldb/overview.html#installation>`_ page.


Through out this tutorial we will use ``pkg:github/llvm/llvm-project@10.0.0`` and will show
the symbol and string for `llvm-project/clang/include/clang/Analysis/BodyFarm.h <https://github.com/llvm/llvm-project/blob/d32170dbd5b0d54436537b6b75beaf44324e0c28/clang/include/clang/Analysis/BodyFarm.h>`_
resource.

.. code-block:: c
    :name: BodyFarm.h

    //== BodyFarm.h - Factory for conjuring up fake bodies -------------*- C++ -*-//
    //
    // Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
    // See https://llvm.org/LICENSE.txt for license information.
    // SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
    //
    //===----------------------------------------------------------------------===//
    //
    // BodyFarm is a factory for creating faux implementations for functions/methods
    // for analysis purposes.
    //
    //===----------------------------------------------------------------------===//

    #ifndef LLVM_CLANG_LIB_ANALYSIS_BODYFARM_H
    #define LLVM_CLANG_LIB_ANALYSIS_BODYFARM_H

    #include "clang/AST/DeclBase.h"
    #include "clang/Basic/LLVM.h"
    #include "llvm/ADT/DenseMap.h"
    #include "llvm/ADT/Optional.h"

    namespace clang {

    class ASTContext;
    class FunctionDecl;
    class ObjCMethodDecl;
    class ObjCPropertyDecl;
    class Stmt;
    class CodeInjector;

    class BodyFarm {
    public:
    BodyFarm(ASTContext &C, CodeInjector *injector) : C(C), Injector(injector) {}

    /// Factory method for creating bodies for ordinary functions.
    Stmt *getBody(const FunctionDecl *D);

    /// Factory method for creating bodies for Objective-C properties.
    Stmt *getBody(const ObjCMethodDecl *D);

    /// Remove copy constructor to avoid accidental copying.
    BodyFarm(const BodyFarm &other) = delete;

    private:
    typedef llvm::DenseMap<const Decl *, Optional<Stmt *>> BodyMap;

    ASTContext &C;
    BodyMap Bodies;
    CodeInjector *Injector;
    };
    } // namespace clang

    #endif


Ctags Symbols
-------------

- Send GET request to PurlDB with ``/api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0
  &addon_pipelines=collect_symbols``.

.. warning::
    The ``collect_symbols`` pipeline requires ``universal-ctags``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` for resources.

- Below is the Ctags symbol for ``clang/include/clang/Analysis/BodyFarm.h``
  file in ``extra_data`` field.

.. code-block:: json

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>/",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/include/clang/Analysis/BodyFarm.h",
        "type": "file",
        "name": "BodyFarm.h",
        "extension": ".h",
        "size": 1509,
        "md5": "808b7438da9841d95ae3a8135e7bf61f",
        "sha1": "38093fc0f043d0e639cc0b225e1acc038ffb7020",
        "sha256": "83693b005ba387627ad10cef752d2559fe724cc0c7d4e86c4947f22403273e0c",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c++",
        "file_type": "C++ source, ASCII text",
        "programming_language": "C",
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
                "Bodies",
                "BodyFarm",
                "BodyFarm",
                "BodyMap",
                "C",
                "Injector",
                "LLVM_CLANG_LIB_ANALYSIS_BODYFARM_H",
                "clang"
            ]
        }
    }


Xgettext Strings
----------------

- Send GET request to PurlDB with ``/api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0
  &addon_pipelines=collect_source_strings``.

.. warning::
    The ``collect_source_strings`` pipeline requires ``gettext``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_strings`` for resources.

- Below is the Xgettext strings for ``clang/include/clang/Analysis/BodyFarm.h``
  file in ``extra_data`` field.

.. code-block:: json

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>/",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/include/clang/Analysis/BodyFarm.h",
        "type": "file",
        "name": "BodyFarm.h",
        "extension": ".h",
        "size": 1509,
        "md5": "808b7438da9841d95ae3a8135e7bf61f",
        "sha1": "38093fc0f043d0e639cc0b225e1acc038ffb7020",
        "sha256": "83693b005ba387627ad10cef752d2559fe724cc0c7d4e86c4947f22403273e0c",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c++",
        "file_type": "C++ source, ASCII text",
        "programming_language": "C",
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
            "source_strings": []
        }
    }

Tree-Sitter Symbols and Strings
-------------------------------

- Send GET request to PurlDB with ``/api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0
  &addon_pipelines=collect_tree_sitter_symbols``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` and ``source_strings`` for resources.

- Below is the Tree-Sitter symbols and strings for ``clang/include/clang/Analysis/BodyFarm.h`` file
  in ``extra_data`` field.

.. code-block:: json

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>/",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/include/clang/Analysis/BodyFarm.h",
        "type": "file",
        "name": "BodyFarm.h",
        "extension": ".h",
        "size": 1509,
        "md5": "808b7438da9841d95ae3a8135e7bf61f",
        "sha1": "38093fc0f043d0e639cc0b225e1acc038ffb7020",
        "sha256": "83693b005ba387627ad10cef752d2559fe724cc0c7d4e86c4947f22403273e0c",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c++",
        "file_type": "C++ source, ASCII text",
        "programming_language": "C",
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
                "LLVM_CLANG_LIB_ANALYSIS_BODYFARM_H",
                "LLVM_CLANG_LIB_ANALYSIS_BODYFARM_H",
                "clang",
                "ASTContext",
                "FunctionDecl",
                "ObjCMethodDecl",
                "ObjCPropertyDecl",
                "Stmt",
                "CodeInjector",
                "BodyFarm",
                "BodyFarm",
                "ASTContext",
                "C",
                "CodeInjector",
                "injector",
                "C",
                "C",
                "Injector",
                "injector",
                "getBody",
                "D",
                "getBody",
                "D",
                "BodyFarm",
                "other",
                "delete",
                "llvm",
                "DenseMap",
                "const",
                "Decl",
                "Optional",
                "Stmt",
                "BodyMap",
                "ASTContext",
                "C",
                "Bodies",
                "Injector"
            ],
            "source_strings": [
                "clang/AST/DeclBase.h",
                "clang/Basic/LLVM.h",
                "llvm/ADT/DenseMap.h",
                "llvm/ADT/Optional.h"
            ]
        }
    }

Pygments Symbols and Strings
-------------------------------

- Send GET request to PurlDB with ``/api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0
  &addon_pipelines=collect_source_strings``.

.. warning::
    The ``collect_source_strings`` pipeline requires ``gettext``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_strings`` for resources.

- Below is the Xgettext strings for ``clang/include/clang/Analysis/BodyFarm.h``
  file in ``extra_data`` field.

.. code-block:: json

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>/",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/include/clang/Analysis/BodyFarm.h",
        "type": "file",
        "name": "BodyFarm.h",
        "extension": ".h",
        "size": 1509,
        "md5": "808b7438da9841d95ae3a8135e7bf61f",
        "sha1": "38093fc0f043d0e639cc0b225e1acc038ffb7020",
        "sha256": "83693b005ba387627ad10cef752d2559fe724cc0c7d4e86c4947f22403273e0c",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c++",
        "file_type": "C++ source, ASCII text",
        "programming_language": "C",
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
            "source_strings": []
        }
    }

Tree-Sitter Symbols and Strings
-------------------------------

- Send GET request to PurlDB with ``/api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0
  &addon_pipelines=collect_pygments_symbols``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` and ``source_strings`` for resources.

- Below is the Pygments symbols and strings for ``clang/include/clang/Analysis/BodyFarm.h`` file
  in ``extra_data`` field.

.. code-block:: json

    {
        "package": "http://127.0.0.1:8001/api/packages/<package-id>/",
        "purl": "pkg:github/llvm/llvm-project@10.0.0",
        "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/include/clang/Analysis/BodyFarm.h",
        "type": "file",
        "name": "BodyFarm.h",
        "extension": ".h",
        "size": 1509,
        "md5": "808b7438da9841d95ae3a8135e7bf61f",
        "sha1": "38093fc0f043d0e639cc0b225e1acc038ffb7020",
        "sha256": "83693b005ba387627ad10cef752d2559fe724cc0c7d4e86c4947f22403273e0c",
        "sha512": null,
        "git_sha1": null,
        "mime_type": "text/x-c++",
        "file_type": "C++ source, ASCII text",
        "programming_language": "C",
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
                "getBody"
            ],
            "source_strings": []
        }
    }
