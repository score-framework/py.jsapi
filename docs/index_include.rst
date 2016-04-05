.. module:: score.jsapi
.. role:: faint
.. role:: confkey

***********
score.jsapi
***********

Introduction
============

This module provides a convenient API for exposing python functions into
Javascript. This can be done by defining endpoints (methods of communication
between javascript and python) and assigning exposed functions to them:

.. code-block:: python

    from jsapi import UrlEndpoint

    math = UrlEndpoint('math')

    @math.op
    def add(num1, num2):
        return num1 + num2

    jsapi.init({'endpoints': [math]})

The functions exposed this way can be easily accessed in javascript:

.. code-block:: javascript

    require('lib/score/jsapi', function(api) {
        api.add(40, 2).then(function(result) {
            console.log('40 + 2 = ' + result);
        });
    });

.. todo::

    Add documentation of javascript API, especially the values available in
    error handlers in regard to "expose" configuration.

Configuration
=============

.. autofunction:: init

.. autoclass:: ConfiguredJsapiModule

.. autoclass:: Endpoint

    .. automethod:: op

    .. automethod:: call

.. autoclass:: UrlEndpoint

    .. automethod:: handle

.. autoclass:: SafeException
