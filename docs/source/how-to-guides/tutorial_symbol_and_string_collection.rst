.. _tutorial_symbol_and_string_collection:

How To get symbols and strings from a PURL/package
==================================================

In this tutorial we'll introduce the different addon pipeline that can be used for
collecting symbols and strings from codebase resources.

.. note::
    This tutorial assumes that you have a working installation of PurlDB.
    If you don't, please refer to the `installation <../purldb/overview.html#installation>`_ page.


Through out this tutorial we will use ``pkg:github/llvm/llvm-project@10.0.0`` and will show
the symbol and string for `llvm-project/clang/lib/Basic/Builtins.cpp <https://github.com/llvm/llvm-project/blob/d32170dbd5b0d54436537b6b75beaf44324e0c28/clang/lib/Basic/Builtins.cpp>`_
resource.

.. code-block:: c
    :name: Builtins.cpp

    //===--- Builtins.cpp - Builtin function implementation -------------------===//
    //
    // Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
    // See https://llvm.org/LICENSE.txt for license information.
    // SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
    //
    //===----------------------------------------------------------------------===//
    //
    //  This file implements various things for builtin functions.
    //
    //===----------------------------------------------------------------------===//

    #include "clang/Basic/Builtins.h"
    #include "clang/Basic/IdentifierTable.h"
    #include "clang/Basic/LangOptions.h"
    #include "clang/Basic/TargetInfo.h"
    #include "llvm/ADT/StringRef.h"
    using namespace clang;

    static const Builtin::Info BuiltinInfo[] = {
      { "not a builtin function", nullptr, nullptr, nullptr, ALL_LANGUAGES,nullptr},
    #define BUILTIN(ID, TYPE, ATTRS)                                               \
      { #ID, TYPE, ATTRS, nullptr, ALL_LANGUAGES, nullptr },
    #define LANGBUILTIN(ID, TYPE, ATTRS, LANGS)                                    \
      { #ID, TYPE, ATTRS, nullptr, LANGS, nullptr },
    #define LIBBUILTIN(ID, TYPE, ATTRS, HEADER, LANGS)                             \
      { #ID, TYPE, ATTRS, HEADER, LANGS, nullptr },
    #include "clang/Basic/Builtins.def"
    };

    const Builtin::Info &Builtin::Context::getRecord(unsigned ID) const {
      if (ID < Builtin::FirstTSBuiltin)
        return BuiltinInfo[ID];
      assert(((ID - Builtin::FirstTSBuiltin) <
              (TSRecords.size() + AuxTSRecords.size())) &&
            "Invalid builtin ID!");
      if (isAuxBuiltinID(ID))
        return AuxTSRecords[getAuxBuiltinID(ID) - Builtin::FirstTSBuiltin];
      return TSRecords[ID - Builtin::FirstTSBuiltin];
    }

    void Builtin::Context::InitializeTarget(const TargetInfo &Target,
                                            const TargetInfo *AuxTarget) {
      assert(TSRecords.empty() && "Already initialized target?");
      TSRecords = Target.getTargetBuiltins();
      if (AuxTarget)
        AuxTSRecords = AuxTarget->getTargetBuiltins();
    }

    bool Builtin::Context::isBuiltinFunc(llvm::StringRef FuncName) {
      for (unsigned i = Builtin::NotBuiltin + 1; i != Builtin::FirstTSBuiltin; ++i)
        if (FuncName.equals(BuiltinInfo[i].Name))
          return strchr(BuiltinInfo[i].Attributes, 'f') != nullptr;

      return false;
    }

    bool Builtin::Context::builtinIsSupported(const Builtin::Info &BuiltinInfo,
                                              const LangOptions &LangOpts) {
      bool BuiltinsUnsupported =
          (LangOpts.NoBuiltin || LangOpts.isNoBuiltinFunc(BuiltinInfo.Name)) &&
          strchr(BuiltinInfo.Attributes, 'f');
      bool MathBuiltinsUnsupported =
        LangOpts.NoMathBuiltin && BuiltinInfo.HeaderName &&
        llvm::StringRef(BuiltinInfo.HeaderName).equals("math.h");
      bool GnuModeUnsupported = !LangOpts.GNUMode && (BuiltinInfo.Langs & GNU_LANG);
      bool MSModeUnsupported =
          !LangOpts.MicrosoftExt && (BuiltinInfo.Langs & MS_LANG);
      bool ObjCUnsupported = !LangOpts.ObjC && BuiltinInfo.Langs == OBJC_LANG;
      bool OclC1Unsupported = (LangOpts.OpenCLVersion / 100) != 1 &&
                              (BuiltinInfo.Langs & ALL_OCLC_LANGUAGES ) ==  OCLC1X_LANG;
      bool OclC2Unsupported =
          (LangOpts.OpenCLVersion != 200 && !LangOpts.OpenCLCPlusPlus) &&
          (BuiltinInfo.Langs & ALL_OCLC_LANGUAGES) == OCLC20_LANG;
      bool OclCUnsupported = !LangOpts.OpenCL &&
                            (BuiltinInfo.Langs & ALL_OCLC_LANGUAGES);
      bool OpenMPUnsupported = !LangOpts.OpenMP && BuiltinInfo.Langs == OMP_LANG;
      bool CPlusPlusUnsupported =
          !LangOpts.CPlusPlus && BuiltinInfo.Langs == CXX_LANG;
      return !BuiltinsUnsupported && !MathBuiltinsUnsupported && !OclCUnsupported &&
            !OclC1Unsupported && !OclC2Unsupported && !OpenMPUnsupported &&
            !GnuModeUnsupported && !MSModeUnsupported && !ObjCUnsupported &&
            !CPlusPlusUnsupported;
    }

    /// initializeBuiltins - Mark the identifiers for all the builtins with their
    /// appropriate builtin ID # and mark any non-portable builtin identifiers as
    /// such.
    void Builtin::Context::initializeBuiltins(IdentifierTable &Table,
                                              const LangOptions& LangOpts) {
      // Step #1: mark all target-independent builtins with their ID's.
      for (unsigned i = Builtin::NotBuiltin+1; i != Builtin::FirstTSBuiltin; ++i)
        if (builtinIsSupported(BuiltinInfo[i], LangOpts)) {
          Table.get(BuiltinInfo[i].Name).setBuiltinID(i);
        }

      // Step #2: Register target-specific builtins.
      for (unsigned i = 0, e = TSRecords.size(); i != e; ++i)
        if (builtinIsSupported(TSRecords[i], LangOpts))
          Table.get(TSRecords[i].Name).setBuiltinID(i + Builtin::FirstTSBuiltin);

      // Step #3: Register target-specific builtins for AuxTarget.
      for (unsigned i = 0, e = AuxTSRecords.size(); i != e; ++i)
        Table.get(AuxTSRecords[i].Name)
            .setBuiltinID(i + Builtin::FirstTSBuiltin + TSRecords.size());
    }

    void Builtin::Context::forgetBuiltin(unsigned ID, IdentifierTable &Table) {
      Table.get(getRecord(ID).Name).setBuiltinID(0);
    }

    unsigned Builtin::Context::getRequiredVectorWidth(unsigned ID) const {
      const char *WidthPos = ::strchr(getRecord(ID).Attributes, 'V');
      if (!WidthPos)
        return 0;

      ++WidthPos;
      assert(*WidthPos == ':' &&
            "Vector width specifier must be followed by a ':'");
      ++WidthPos;

      char *EndPos;
      unsigned Width = ::strtol(WidthPos, &EndPos, 10);
      assert(*EndPos == ':' && "Vector width specific must end with a ':'");
      return Width;
    }

    bool Builtin::Context::isLike(unsigned ID, unsigned &FormatIdx,
                                  bool &HasVAListArg, const char *Fmt) const {
      assert(Fmt && "Not passed a format string");
      assert(::strlen(Fmt) == 2 &&
            "Format string needs to be two characters long");
      assert(::toupper(Fmt[0]) == Fmt[1] &&
            "Format string is not in the form \"xX\"");

      const char *Like = ::strpbrk(getRecord(ID).Attributes, Fmt);
      if (!Like)
        return false;

      HasVAListArg = (*Like == Fmt[1]);

      ++Like;
      assert(*Like == ':' && "Format specifier must be followed by a ':'");
      ++Like;

      assert(::strchr(Like, ':') && "Format specifier must end with a ':'");
      FormatIdx = ::strtol(Like, nullptr, 10);
      return true;
    }

    bool Builtin::Context::isPrintfLike(unsigned ID, unsigned &FormatIdx,
                                        bool &HasVAListArg) {
      return isLike(ID, FormatIdx, HasVAListArg, "pP");
    }

    bool Builtin::Context::isScanfLike(unsigned ID, unsigned &FormatIdx,
                                      bool &HasVAListArg) {
      return isLike(ID, FormatIdx, HasVAListArg, "sS");
    }

    bool Builtin::Context::performsCallback(unsigned ID,
                                            SmallVectorImpl<int> &Encoding) const {
      const char *CalleePos = ::strchr(getRecord(ID).Attributes, 'C');
      if (!CalleePos)
        return false;

      ++CalleePos;
      assert(*CalleePos == '<' &&
            "Callback callee specifier must be followed by a '<'");
      ++CalleePos;

      char *EndPos;
      int CalleeIdx = ::strtol(CalleePos, &EndPos, 10);
      assert(CalleeIdx >= 0 && "Callee index is supposed to be positive!");
      Encoding.push_back(CalleeIdx);

      while (*EndPos == ',') {
        const char *PayloadPos = EndPos + 1;

        int PayloadIdx = ::strtol(PayloadPos, &EndPos, 10);
        Encoding.push_back(PayloadIdx);
      }

      assert(*EndPos == '>' && "Callback callee specifier must end with a '>'");
      return true;
    }

    bool Builtin::Context::canBeRedeclared(unsigned ID) const {
      return ID == Builtin::NotBuiltin ||
            ID == Builtin::BI__va_start ||
            (!hasReferenceArgsOrResult(ID) &&
              !hasCustomTypechecking(ID));
    }


Ctags Symbols
-------------

- Send GET request to PurlDB with::
    
    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_symbols

.. warning::
    The ``collect_symbols`` pipeline requires ``universal-ctags``.

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` for resources.

- Below is the Ctags symbol for ``clang/lib/Basic/Builtins.cpp``
  file in ``extra_data`` field.

.. code-block:: json

    {
      "package": "http://127.0.0.1:8001/api/packages/ddedb539-32fd-43fd-b2c7-d50e5b718711/",
      "purl": "pkg:github/llvm/llvm-project@10.0.0",
      "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/lib/Basic/Builtins.cpp",
      "type": "file",
      "name": "Builtins.cpp",
      "extension": ".cpp",
      "size": 7566,
      "md5": "6afa8fe94d28fb1926851fa7eaf2cffa",
      "sha1": "5cf1719199d3183d7811a3f133d2a4bfdd2d7da4",
      "sha256": "9ba7fe01cb504dd97c7694ab716291e1b9584ee6646219469c14d6724da7292b",
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
              "InitializeTarget",
              "LANGBUILTIN",
              "LIBBUILTIN",
              "builtinIsSupported",
              "canBeRedeclared",
              "forgetBuiltin",
              "getRecord",
              "getRequiredVectorWidth",
              "initializeBuiltins",
              "isBuiltinFunc",
              "isLike",
              "isPrintfLike",
              "isScanfLike",
              "performsCallback"
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

- Below is the Xgettext strings for ``clang/lib/Basic/Builtins.cpp``
  file in ``extra_data`` field.

.. code-block:: json

    {
      "package": "http://127.0.0.1:8001/api/packages/ddedb539-32fd-43fd-b2c7-d50e5b718711/",
      "purl": "pkg:github/llvm/llvm-project@10.0.0",
      "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/lib/Basic/Builtins.cpp",
      "type": "file",
      "name": "Builtins.cpp",
      "extension": ".cpp",
      "size": 7566,
      "md5": "6afa8fe94d28fb1926851fa7eaf2cffa",
      "sha1": "5cf1719199d3183d7811a3f133d2a4bfdd2d7da4",
      "sha256": "9ba7fe01cb504dd97c7694ab716291e1b9584ee6646219469c14d6724da7292b",
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
              "not a builtin function"
              "Invalid builtin ID!"
              "Already initialized target?"
              "math.h"
              "Vector width specifier must be followed by a ':'"
              "Vector width specific must end with a ':'"
              "Not passed a format string"
              "Format string needs to be two characters long"
              "Format string is not in the form \\\"xX\\"
              "Format specifier must be followed by a ':'"
              "Format specifier must end with a ':'"
              "pP"
              "sS"
              "Callback callee specifier must be followed by a '<'"
              "Callee index is supposed to be positive!"
              "Callback callee specifier must end with a '>'"
          ]
      }
    }

Tree-Sitter Symbols and Strings
-------------------------------

- Send GET request to PurlDB with::
    
    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_tree_sitter_symbols

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` and ``source_strings`` for resources.

- Below is the Tree-Sitter symbols and strings for ``clang/lib/Basic/Builtins.cpp`` file
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
                "clang",
                "BuiltinInfo",
                "ALL_LANGUAGES",
                "BUILTIN",
                "ID",
                "TYPE",
                "ATTRS",
                "TYPE",
                "ATTRS",
                "ALL_LANGUAGES",
                "LANGBUILTIN",
                "LIBBUILTIN",
                "ID",
                "TYPE",
                "ATTRS",
                "HEADER",
                "LANGS",
                "getRecord",
                "ID",
                "ID",
                "FirstTSBuiltin",
                "BuiltinInfo",
                "ID",
                "assert",
                "ID",
                "FirstTSBuiltin",
                "TSRecords",
                "AuxTSRecords",
                "isAuxBuiltinID",
                "ID",
                "AuxTSRecords",
                "getAuxBuiltinID",
                "ID",
                "FirstTSBuiltin",
                "TSRecords",
                "ID",
                "FirstTSBuiltin",
                "InitializeTarget",
                "Target",
                "AuxTarget",
                "assert",
                "TSRecords",
                "TSRecords",
                "Target",
                "AuxTarget",
                "AuxTSRecords",
                "AuxTarget",
                "isBuiltinFunc",
                "FuncName",
                "i",
                "NotBuiltin",
                "i",
                "FirstTSBuiltin",
                "i",
                "FuncName",
                "BuiltinInfo",
                "i",
                "strchr",
                "BuiltinInfo",
                "i",
                "builtinIsSupported",
                "BuiltinInfo",
                "LangOpts",
                "BuiltinsUnsupported",
                "LangOpts",
                "LangOpts",
                "BuiltinInfo",
                "strchr",
                "BuiltinInfo",
                "MathBuiltinsUnsupported",
                "LangOpts",
                "BuiltinInfo",
                "StringRef",
                "BuiltinInfo",
                "GnuModeUnsupported",
                "LangOpts",
                "BuiltinInfo",
                "GNU_LANG",
                "MSModeUnsupported",
                "LangOpts",
                "BuiltinInfo",
                "MS_LANG",
                "ObjCUnsupported",
                "LangOpts",
                "BuiltinInfo",
                "OBJC_LANG",
                "OclC1Unsupported",
                "LangOpts",
                "BuiltinInfo",
                "ALL_OCLC_LANGUAGES",
                "OCLC1X_LANG",
                "OclC2Unsupported",
                "LangOpts",
                "LangOpts",
                "BuiltinInfo",
                "ALL_OCLC_LANGUAGES",
                "OCLC20_LANG",
                "OclCUnsupported",
                "LangOpts",
                "BuiltinInfo",
                "ALL_OCLC_LANGUAGES",
                "OpenMPUnsupported",
                "LangOpts",
                "BuiltinInfo",
                "OMP_LANG",
                "CPlusPlusUnsupported",
                "LangOpts",
                "BuiltinInfo",
                "CXX_LANG",
                "BuiltinsUnsupported",
                "MathBuiltinsUnsupported",
                "OclCUnsupported",
                "OclC1Unsupported",
                "OclC2Unsupported",
                "OpenMPUnsupported",
                "GnuModeUnsupported",
                "MSModeUnsupported",
                "ObjCUnsupported",
                "CPlusPlusUnsupported",
                "initializeBuiltins",
                "Table",
                "LangOpts",
                "i",
                "NotBuiltin",
                "i",
                "FirstTSBuiltin",
                "i",
                "builtinIsSupported",
                "BuiltinInfo",
                "i",
                "LangOpts",
                "Table",
                "BuiltinInfo",
                "i",
                "i",
                "i",
                "e",
                "TSRecords",
                "i",
                "e",
                "i",
                "builtinIsSupported",
                "TSRecords",
                "i",
                "LangOpts",
                "Table",
                "TSRecords",
                "i",
                "i",
                "FirstTSBuiltin",
                "i",
                "e",
                "AuxTSRecords",
                "i",
                "e",
                "i",
                "Table",
                "AuxTSRecords",
                "i",
                "i",
                "FirstTSBuiltin",
                "TSRecords",
                "forgetBuiltin",
                "ID",
                "Table",
                "Table",
                "getRecord",
                "ID",
                "getRequiredVectorWidth",
                "ID",
                "WidthPos",
                "strchr",
                "getRecord",
                "ID",
                "WidthPos",
                "WidthPos",
                "assert",
                "WidthPos",
                "WidthPos",
                "EndPos",
                "Width",
                "strtol",
                "WidthPos",
                "EndPos",
                "assert",
                "EndPos",
                "Width",
                "isLike",
                "ID",
                "FormatIdx",
                "HasVAListArg",
                "Fmt",
                "assert",
                "Fmt",
                "assert",
                "strlen",
                "Fmt",
                "assert",
                "toupper",
                "Fmt",
                "Fmt",
                "Like",
                "strpbrk",
                "getRecord",
                "ID",
                "Fmt",
                "Like",
                "HasVAListArg",
                "Like",
                "Fmt",
                "Like",
                "assert",
                "Like",
                "Like",
                "assert",
                "strchr",
                "Like",
                "FormatIdx",
                "strtol",
                "Like",
                "isPrintfLike",
                "ID",
                "FormatIdx",
                "HasVAListArg",
                "isLike",
                "ID",
                "FormatIdx",
                "HasVAListArg",
                "isScanfLike",
                "ID",
                "FormatIdx",
                "HasVAListArg",
                "isLike",
                "ID",
                "FormatIdx",
                "HasVAListArg",
                "performsCallback",
                "ID",
                "Encoding",
                "CalleePos",
                "strchr",
                "getRecord",
                "ID",
                "CalleePos",
                "CalleePos",
                "assert",
                "CalleePos",
                "CalleePos",
                "EndPos",
                "CalleeIdx",
                "strtol",
                "CalleePos",
                "EndPos",
                "assert",
                "CalleeIdx",
                "Encoding",
                "CalleeIdx",
                "EndPos",
                "PayloadPos",
                "EndPos",
                "PayloadIdx",
                "strtol",
                "PayloadPos",
                "EndPos",
                "Encoding",
                "PayloadIdx",
                "assert",
                "EndPos",
                "canBeRedeclared",
                "ID",
                "ID",
                "NotBuiltin",
                "ID",
                "BI__va_start",
                "hasReferenceArgsOrResult",
                "ID",
                "hasCustomTypechecking",
                "ID"
            ],
            "source_strings": [
                "clang/Basic/Builtins.h",
                "clang/Basic/IdentifierTable.h",
                "clang/Basic/LangOptions.h",
                "clang/Basic/TargetInfo.h",
                "llvm/ADT/StringRef.h",
                "not a builtin function",
                "clang/Basic/Builtins.def",
                "Invalid builtin ID!",
                "Already initialized target?",
                "math.h",
                "Vector width specifier must be followed by a ':'",
                "Vector width specific must end with a ':'",
                "Not passed a format string",
                "Format string needs to be two characters long",
                "Format string is not in the form xX",
                "Format specifier must be followed by a ':'",
                "Format specifier must end with a ':'",
                "pP",
                "sS",
                "Callback callee specifier must be followed by a '<'",
                "Callee index is supposed to be positive!",
                "Callback callee specifier must end with a '>'"
            ]
        }
    }

Pygments Symbols and Strings
-------------------------------

- Send GET request to PurlDB with::
    
    /api/collect/?purl=pkg:github/llvm/llvm-project@10.0.0&addon_pipelines=collect_pygments_symbols

- Once the indexing has completed visit ``/api/resources/?purl=pkg:github/llvm/llvm-project@10.0.0``
  to get the ``source_symbols`` and ``source_strings`` for resources.

- Below is the Pygments symbols and strings for ``clang/lib/Basic/Builtins.cpp`` file
  in ``extra_data`` field.

.. code-block:: json

    {
      "package": "http://127.0.0.1:8001/api/packages/ddedb539-32fd-43fd-b2c7-d50e5b718711/",
      "purl": "pkg:github/llvm/llvm-project@10.0.0",
      "path": "llvm-project-llvmorg-10.0.0.tar.gz-extract/llvm-project-llvmorg-10.0.0/clang/lib/Basic/Builtins.cpp",
      "type": "file",
      "name": "Builtins.cpp",
      "extension": ".cpp",
      "size": 7566,
      "md5": "6afa8fe94d28fb1926851fa7eaf2cffa",
      "sha1": "5cf1719199d3183d7811a3f133d2a4bfdd2d7da4",
      "sha256": "9ba7fe01cb504dd97c7694ab716291e1b9584ee6646219469c14d6724da7292b",
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
              "Builtin::Context::getRecord",
              "Builtin::Context::InitializeTarget",
              "Builtin::Context::isBuiltinFunc",
              "Builtin::Context::builtinIsSupported",
              "Builtin::Context::initializeBuiltins",
              "Builtin::Context::forgetBuiltin",
              "Builtin::Context::getRequiredVectorWidth",
              "Builtin::Context::isLike",
              "Builtin::Context::isPrintfLike",
              "Builtin::Context::isScanfLike",
              "Builtin::Context::performsCallback",
              "Builtin::Context::canBeRedeclared"
          ],
          "source_strings": [
              "\"",
              "not a builtin function",
              "\"",
              "\"",
              "Invalid builtin ID!",
              "\"",
              "\"",
              "Already initialized target?",
              "\"",
              "1",
              "'",
              "f",
              "'",
              "'",
              "f",
              "'",
              "\"",
              "math.h",
              "\"",
              "100",
              "1",
              "200",
              "1",
              "0",
              "0",
              "0",
              "'",
              "V",
              "'",
              "0",
              "'",
              ":",
              "'",
              "\"",
              "Vector width specifier must be followed by a ':'",
              "\"",
              "10",
              "'",
              ":",
              "'",
              "\"",
              "Vector width specific must end with a ':'",
              "\"",
              "\"",
              "Not passed a format string",
              "\"",
              "2",
              "\"",
              "Format string needs to be two characters long",
              "\"",
              "0",
              "1",
              "\"",
              "Format string is not in the form",
              "\\\"",
              "xX",
              "\\\"",
              "\"",
              "1",
              "'",
              ":",
              "'",
              "\"",
              "Format specifier must be followed by a ':'",
              "\"",
              "'",
              ":",
              "'",
              "\"",
              "Format specifier must end with a ':'",
              "\"",
              "10",
              "\"",
              "pP",
              "\"",
              "\"",
              "sS",
              "\"",
              "'",
              "C",
              "'",
              "'",
              "<",
              "'",
              "\"",
              "Callback callee specifier must be followed by a '<'",
              "\"",
              "10",
              "0",
              "\"",
              "Callee index is supposed to be positive!",
              "\"",
              "'",
              ",",
              "'",
              "1",
              "10",
              "'",
              ">",
              "'",
              "\"",
              "Callback callee specifier must end with a '>'",
              "\""
          ]
      }
    }
