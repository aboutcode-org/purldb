===========================
  Code Matching pipeline
===========================

The aim of this tutorial is to show how to use the MatchCode.io API to perform
code matching on an archive of files.


.. note::
    This tutorial assumes that you have a working installation of PurlDB. If you
    don't, please refer to the :ref:`installation` page.


Throughout this tutorial, we will use ``pkg:npm/deep-equal@1.0.1`` and a
modified copy of ``index.js`` from it.

.. raw:: html

   <details>
   <summary><a>BPF.cpp</a></summary>
   </br>

.. code-block:: javascript

    var pSlice = Array.prototype.slice;
    var objectKeys = require('./lib/keys.js');
    var isArguments = require('./lib/is_arguments.js');

    var deepEqual = module.exports = function (actual, expected, opts) {
        if (!opts) opts = {};
        // 7.1. All identical values are equivalent, as determined by ===.
        if (actual === expected) {
            return true;

        } else if (actual instanceof Date && expected instanceof Date) {
            return actual.getTime() === expected.getTime();

        // 7.3. Other pairs that do not both pass typeof value == 'object',
        // equivalence is determined by ==.
        } else if (!actual || !expected || typeof actual != 'object' && typeof expected != 'object') {
            return opts.strict ? actual === expected : actual == expected;

        // 7.4. For all other Object pairs, including Array objects, equivalence is
        // determined by having the same number of owned properties (as verified
        // with Object.prototype.hasOwnProperty.call), the same set of keys
        // (although not necessarily the same order), equivalent values for every
        // corresponding key, and an identical 'prototype' property. Note: this
        // accounts for both named and indexed properties on Arrays.
        } else {
            return objEquiv(actual, expected, opts);
        }
    }

    function isBuffer (x) {
        if (!x || typeof x !== 'object' || typeof x.length !== 'number') return false;
        if (typeof x.copy !== 'function' || typeof x.slice !== 'function') {
            return false;
        }
        if (x.length > 0 && typeof x[0] !== 'number') return false;
        return true;
    }

    function objEquiv(a, b, opts) {
        var i, key;
        if (isUndefinedOrNull(a) || isUndefinedOrNull(b))
            return false;
        // an identical 'prototype' property.
        if (a.prototype !== b.prototype) return false;
        //~~~I've managed to break Object.keys through screwy arguments passing.
        //   Converting to array solves the problem.
        if (isArguments(a)) {
            if (!isArguments(b)) {
                return false;
            }
            a = pSlice.call(a);
            b = pSlice.call(b);
            return deepEqual(a, b, opts);
        }
        if (isBuffer(a)) {
            if (!isBuffer(b)) {
                return false;
            }
            if (a.length !== b.length) return false;
            for (i = 0; i < a.length; i++) {
                if (a[i] !== b[i]) return false;
            }
            return true;
        }
        try {
            var ka = objectKeys(a),
                kb = objectKeys(b);
        } catch (e) {//happens when one is a string literal and the other isn't
            return false;
        }
        // having the same number of owned properties (keys incorporates
        // hasOwnProperty)
        if (ka.length != kb.length)
            return false;
        //the same set of keys (although not necessarily the same order),
        ka.sort();
        kb.sort();
        //~~~cheap key test
        for (i = ka.length - 1; i >= 0; i--) {
            if (ka[i] != kb[i])
            return false;
        }
        //equivalent values for every corresponding key, and
        //~~~possibly expensive deep test
        for (i = ka.length - 1; i >= 0; i--) {
            key = ka[i];
            if (!deepEqual(a[key], b[key], opts)) return false;
        }
        return typeof a === typeof b;
    }

.. raw:: html

   </details>
   </br>


Instructions
------------

- First, index the package ``pkg:npm/deep-equal@1.0.1``::

    /api/collect/?purl=pkg:npm/deep-equal@1.0.1

- Scan ``index.js`` from ``pkg:npm/deep-equal@1.0.1`` with ScanCode toolkit::

    scancode --info index.js --json index.js-results.json

- Visit ``/api/matching/`` and POST a new matching request.

.. note::
    Whether you follow this tutorial and previous instructions using cURL or
    Python script, the final results should be the same.

.. code-block:: bash

    api_url="http://localhost/api/matching/"
    content_type="Content-Type: application/json"
    upload_file="upload_file=@/path/to/index.js-results.json"
    curl -X POST "$api_url" -H "$content_type" -F "$upload_file"

- When the match has completed, the results can be seen at ``/api/matching/<uuid>/results``

