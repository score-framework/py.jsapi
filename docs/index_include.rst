.. module:: score.jsapi
.. role:: confkey
.. role:: confdefault

***********
score.jsapi
***********

This module provides a convenient API for exposing python functions into
javascript. The humble intent of this module is to make basic communication
between a javascript client and a score server as easy as possible. It is not
meant to provide means for constructing APIs which can be accessed by
outsiders.


Quickstart
==========

Create an :class:`endpoint <Endpoint>`:

.. code-block:: python

    from score.jsapi import UrlEndpoint

    math = UrlEndpoint('math')

Annotate all python functions that you want to expose with your endpoint's
:meth:`op <Endpoint.op>` property:

.. code-block:: python

    @math.op
    def add(ctx, num1, num2):
        return num1 + num2

    @math.op
    def divide(ctx, dividend, divisor):
        return dividend / divisor

Initialize the module and configure it to use your newly defined endpoint
object:

.. code-block:: ini

    [score.init]
    modules =
        ...
        score.jsapi

    [jsapi]
    endpoint = path.to.your.endpoint
    # Important: the next value exposes internal information, like stack
    # traces, for debuggin purposes. On production systems, this value should
    # be omitted or set to False!
    expose = True

Your functions can now be accessed through the auto-generated javascript files:

.. code-block:: jinja

    <script>
        // assuming an AMD environment where all javascript
        // is loaded automatically:
        require(['score.jsapi'], function(api) {
            api.add(40, 2).then(function(result) {
                console.log('40 + 2 = ' + result);
            });
            api.divide(40, 0).catch(function(error) {
                console.error(error);
            });
        });
    </script>

Configuration
=============

.. autofunction:: init

Details
=======

Javascript access
-----------------

All auto-generated javascript is wrapped in a UMD_ block, which means that you
can access everything in your favorite manner:

.. code-block:: javascript

    // AMD
    require(['score/jsapi'], function(api) {
        api.add(40, 2).then(...);
    });

    // CommonJS
    var api = require('score/jsapi');
    api.add(40, 2).then(...);

    // browser globals
    var api = score.jsapi.unified;
    api.add(40, 2).then(...);

You can retrieve a list of all javascript files using the configured jsapi
object's tpl_loader member, which is a
:class:`template loader <score.tpl.loader.Loader>` for :mod:`score.tpl`. The
templates provided by the loader are in the correct order to be included by
your javascript loader without causing any dependency errors:

>>> list(jsapi.tpl_loader.iter_paths())
['score/jsapi/exception.js',
 'score/jsapi/excformat.js',
 'score/jsapi/endpoint.js',
 'score/jsapi/queue.js',
 'score/jsapi/unified.js',
 'score/jsapi/endpoint/url.js',
 'score/jsapi/endpoints/math.js',
 'score/jsapi/exceptions.js',
 'score/jsapi.js']

.. _UMD: https://github.com/umdjs/umd

Exceptions
----------

This module will not send python exceptions to the javascript by default. If an
unexpected error occurs, the promise will be rejected with an instance of this
module's Exception class, which extends javascript's builtin Error_ class, but
does not contain an error message by default:

.. code-block:: javascript

    api.divide(1, 0).then(function(result) {
        // we're dividing by zero, so this block will never be executed
    }).catch(function(error) {
        console.log(error.message);  // will log the empty string
    });

.. _Error: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error

These conservative defaults were chosen to prevent accidental information leaks
during production. You can enable exception logging manually, if you want to
(see the next section).

For cases, where you want to pass exception information from python to
javascript, you need to define `SafeExceptions <SafeException>`:

.. code-block:: python

    from score.jsapi import SafeException

    class MyZeroDivisionException(SafeException):

        def __init__(self, dividend):
            super().__init__('Trying to divide %d by 0' % (dividend,))

    @math.op
    def divide(ctx, dividend, divisor):
        try:
            return dividend / divisor
        except ZeroDivisionError:
            raise MyZeroDivisionException(dividend)

You can then handle these exceptions in your javascript client:

.. code-block:: javascript

    api.divide(1, 0).then(function(result) {
        // we're dividing by zero, so this block will never be executed
    }).catch(function(error) {
        console.log(error.message);  // "Trying to divide 1 by 0"
    });

All SafeException subclasses detected during initialization will also be
exposed to javascript. This allows usage like the following:

.. code-block:: javascript

    api.divide(1, 0).then(function(result) {
        // we're dividing by zero, so this block will never be executed
    }).catch(function(error) {
        if (error instanceof api._exceptions.MyZeroDivisionException) {
            alert("Cannot divide by 0")
        } else {
            throw error;
        }
    });


Exposing debugging information
------------------------------

The configuration value `expose` will send stack traces from the python backend
to the javascript client and log them into the browser console:

.. code-block:: javascript

    api.divide(1, 0).then(function(result) {
        // we're dividing by zero, so this block will never be executed
        // 
        // instead, the console will contain the python stack trace, even if
        // this is not a SafeException:
        //
        //   Error in jsapi call divide ( 1 , 0 ) 
        //   Traceback (most recent call last):
        //     File "/path/to/math.py", line "3", in divide
        //       return dividend / divisor
        //   
        //   ZeroDivisionError: division by zero
    });


Versioning
----------

After deploying an application using score.jsapi, the maintenance work will
require you to alter the implementation of a python function at some point. You
can achieve this in a backward-compatible manner by creating versions of your
functions:

.. code-block:: python

    @math.op
    def divide(ctx, dividend, divisor):
        return dividend / divisor

    @divide.version(2)
    def divide(ctx, dividend, divisor):
        try:
            return dividend / divisor
        except ZeroDivisionError:
            raise MyZeroDivisionException(dividend)

The javascrtipt client will always call the latest version it knows of by
default. This means that older javascript clients will keep accessing the
initial version of the function, while newer clients will use version 2 of your
function.

All version names are converted to string internally to determine the ordering
of your versions. The initial implementation always has the empty string as
version name, which will always cause it be regarded as the first version after
sorting through the version strings.


Preroutes
---------

It is also possible to register a callback, that will be invoked before *each*
operation. This is the best method of checking authorization, for example. The
preroute receives the :class:`score.ctx.Context` object as its sole argument:

.. code-block:: python

    @quest.op
    def get_name_of_enchanter(ctx):
        return 'Tim'

    @quest.preroute
    def preroute(ctx):
        if not ctx.permits('cross-bridge'):
            raise AuthorizationException('None shall pass!')


API
===

Configuration
-------------

.. autofunction:: init

.. autoclass:: ConfiguredJsapiModule

    .. attribute:: tpl_loader

        An instance of :class:`score.tpl.loader.Loader`, that provides all
        templates required to use this module in the correct order.

Endpoints
---------

.. autoclass:: Endpoint

    .. automethod:: op

    .. automethod:: preroute

    .. automethod:: call

.. autoclass:: UrlEndpoint

    .. automethod:: handle

.. autoclass:: SafeException
