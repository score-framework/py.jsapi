# Copyright © 2015 STRG.AT GmbH, Vienna, Austria
#
# This file is part of the The SCORE Framework.
#
# The SCORE Framework and all its parts are free software: you can redistribute
# them and/or modify them under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation which is in the
# file named COPYING.LESSER.txt.
#
# The SCORE Framework and all its parts are distributed without any WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. For more details see the GNU Lesser General Public
# License.
#
# If you have not received a copy of the GNU Lesser General Public License see
# http://www.gnu.org/licenses/.
#
# The License-Agreement realised between you as Licensee and STRG.AT GmbH as
# Licenser including the issue of its valid conclusion and its pre- and
# post-contractual effects is governed by the laws of Austria. Any disputes
# concerning this License-Agreement including the issue of its valid conclusion
# and its pre- and post-contractual effects are exclusively decided by the
# competent court, in whose district STRG.AT GmbH has its registered seat, at
# the discretion of STRG.AT GmbH also the competent court, in whose district the
# Licensee has his registered seat, an establishment or assets.

import inspect
import logging
import os
import sys
import textwrap
import traceback

from score.init import (
    ConfiguredModule, parse_dotted_path, parse_list, parse_bool)


log = logging.getLogger(__name__)


defaults = {
    'endpoints': [],
    'expose': False,
}


def init(confdict, ctx_conf, js_conf):
    """
    Initializes this module acoording to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`endpoints` :faint:`[default=list()]`
        A :func:`list <score.init.parse_list>` of :func:`dotted paths
        <score.init.parse_dotted_path>` pointing to any amount of
        :class:`Endpoints <.Endpoint>`. The registered functions of these
        Endpoints will be available in javascript.

    :confkey:`expose` :faint:`[default=False]`
        Whether security critical data may be exposed through the API. This
        value should be left at its default value in production, but may be
        switched to `True` during development to receive Exceptions and
        stacktraces in the browser console.
    """
    conf = dict(defaults.items())
    conf.update(confdict)
    endpoints = list(map(parse_dotted_path, parse_list(conf['endpoints'])))
    expose = parse_bool(conf['expose'])

    @js_conf.virtjs('jsapi.js')
    def api():
        op_defs = []
        op_funcs = []
        ep_defs = []
        for endpoint in endpoints:
            args = ''
            if endpoint._js_args:
                args = ', ' + ', '.join(endpoint._js_args)
            ep_defs.append("new Endpoint.{type}('{name}'{args});".
                format(name=endpoint.name, type=endpoint.type, args=args))
            for funcname in sorted(endpoint.ops):
                func = endpoint.ops[funcname]
                minargs = 0
                maxargs = 0
                argnames = []
                for name, param in inspect.signature(func).parameters.items():
                    if name == 'ctx':
                        continue
                    argnames.append(name)
                    maxargs += 1
                    if param.default == inspect.Parameter.empty:
                        minargs += 1
                op_def = """
                    {name}: {0}
                        name: "{name}",
                        endpointId: "{endpoint}",
                        minargs: {minargs},
                        maxargs: {maxargs},
                        argnames: [{argnames}],
                    {1}
                """.format(
                    '{', '}', name=funcname, endpoint=endpoint.name,
                    minargs=minargs, maxargs=maxargs,
                    argnames=', '.join(map(lambda x: '"%s"' % x, argnames)))
                op_defs.append(
                    textwrap.indent(textwrap.dedent(op_def).strip(), ' ' * 16))
                doc = ''
                if func.__doc__:
                    doc = textwrap.dedent(func.__doc__).strip()
                    doc = doc.replace('*/', '* /')
                    doc = doc.replace('\n', '\n *')
                    doc = '/**\n * %s\n */\n' % doc
                args = ''
                if argnames:
                    args = ', ' + ', '.join(argnames)
                op_func = """
                    {name}: function(self{args}) {0}
                        var args = [];
                        for (var i = 1; i < arguments.length; i++) {0}
                            args.push(arguments[i])
                        {1}
                        var promise = self._call('{name}', args);
                        self._flush();
                        return promise;
                    {1}
                """.format('{', '}', doc=doc, name=funcname, args=args,
                           argnames=', '.join(argnames))
                op_funcs.append(
                    textwrap.indent(doc, ' ' * 8) +
                    textwrap.indent(textwrap.dedent(op_func).strip(), ' ' * 8))
        op_defs = ',\n\n'.join(op_defs).strip()
        op_funcs = ',\n\n'.join(op_funcs).strip()
        ep_defs = ',\n\n'.join(ep_defs)
        return api_tpl % (op_defs, op_funcs, ep_defs)
    return ConfiguredJsapiModule(ctx_conf, endpoints, expose)


class ConfiguredJsapiModule(ConfiguredModule):
    """
    This module's :class:`configuration class
    <score.init.ConfiguredModule>`.
    """

    def __init__(self, ctx_conf, endpoints, expose):
        super().__init__(__package__)
        self.ctx_conf = ctx_conf
        self.endpoints = endpoints
        self.expose = expose


def exc2json(excinfo):
    """
    Converts exception info (as returned by :func:`sys.exc_info`) into a
    3-tuple that can be converted into a json string by python's :mod:`json`
    library. It will consist of the exception name, the message and the stack
    trace as provided by :meth:`traceback.extract_tb`::

        ['ZeroDivisionError', 'division by zero', [<traceback>]]
    """
    try:
        trace = traceback.extract_tb(excinfo[2])
    except KeyError:
        trace = None
    else:
        while trace and 'score/jsapi/__init__.py' in trace[0][0]:
            trace = trace[1:]
    return [
        excinfo[0].__name__,
        str(excinfo[1]),
        trace,
    ]


class Endpoint:
    """
    An endpoint capable of handling requests from javascript.
    """

    def __init__(self, name):
        self.name = name
        self.ops = {}

    def op(self, func):
        """
        Registers an operation with this Endpoint. It will be available with the
        same name and the same number of arguments in javascript. Note that
        javascript has no support for keyword arguments and :ref:`keyword-only
        parameters <python:keyword-only_parameter>` will confuse this function.
        """
        name = func.__name__
        if name in self.ops:
            raise ValueError('Operation "%s" already registered' % name)
        for argname in inspect.signature(func).parameters:
            if argname != 'ctx':
                raise ValueError("First argument must be the context 'ctx'")
            break
        self.ops[name] = func
        return func

    def call(self, ctx, name, arguments):
        """
        Calls function with given *name* and the given `list` of *arguments*.
        """
        return self.ops[name](ctx, *arguments)

    @property
    def _js_args(self):
        return []


class UrlEndpoint(Endpoint):
    """
    An Endpoint, which can be accessed via AJAX from javascript.
    """

    type = 'URL'

    def __init__(self, name, *, method="POST"):
        super().__init__(name)
        self.url = '/jsapi/' + name
        self.method = method

    def handle(self, jsapi_conf, requests, *, Context=None):
        """
        Handles all functions calls passed with a request.

        The function requires the :class:`configured score.jsapi module
        <.ConfiguredJsapiModule>` as its *jsapi_conf* parameter. It will be used
        to create Contexts for each request. It is possible to provide a
        different *Context* class, though.

        The provided *requests* variable needs to be a list of "calls", where
        each call is a json-encoded list containing the function name as first
        entry, and its arguments as the rest of the list. Example value for
        *requests* with a call to an addition and a division::

            ['["add",40,2]',
             '["divide",42,0]']

        The return value will be a list with two elements, one containing
        success values, the other containing results::

            [[True, False], [42, None]]

        If the module was configured to expose exception information, the `None`
        value will instead be the exception info as provided by
        :func:`exc2json`.

        The input and output is already in the correct format for communication
        with the javascript part, so the result can be sent as
        "application/json"-encoded response to the calling javascript function.
        See the pyramid implementation for example usage of this function.
        """
        if not Context:
            Context = jsapi_conf.ctx_conf.Context
        results = [[], []]
        for r in requests:
            args = r[:]
            try:
                success = True
                name = args[0]
                args.pop(0)
                with Context() as ctx:
                    result = self.call(ctx, name, args)
            except Exception as e:
                success = False
                if jsapi_conf.expose:
                    result = exc2json(sys.exc_info())
                elif isinstance(e, SafeException):
                    result = exc2json([type(e), str(e)])
                else:
                    result = None
            results[0].append(success)
            results[1].append(result)
        return results

    @property
    def _js_args(self):
        return ['"%s"' % self.url, '"%s"' % self.method]


class SafeException(Exception):
    """
    An Exception type, which indicates that the exception is safe to be
    transmitted to the client—even in production. The javascript API will reject
    the call promise with a 2-tuple containing the exception type name and its
    message.

    Example in python …

    .. code-block:: python

        class ZeroDivision(SafeException):

            def __init__(self):
                super().__init__('Cannot divide by zero')

        @endpoint.op
        def divide(dividend, divisor):
            if not divisor:
                raise ZeroDivision()
            return dividend / divisor

    … and javascript:

    .. code-block:: javascript

        api.divide(1, 0).then(function(result) {
            console.log('1 / 0 = ' + result);
        }).catch(function(msg) {
            console.error('Error (' + msg[0] + '): +  msg[1]);
            // will output:
            //   Error (ZeroDivision): Cannot divide by zero
        });

    """


here = os.path.abspath(os.path.dirname(__file__))
file = os.path.join(here, 'api.js.tpl')
api_tpl = open(file).read()
