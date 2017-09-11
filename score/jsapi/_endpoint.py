import abc
import inspect
import logging
from .exc2json import exc2json
import sys
import time
import json
import functools

log = logging.getLogger('score.jsapi')


class EndpointOperation:
    """
    Wrapper class for operations registered on an endpoint.
    """

    def __init__(self, name, endpoint, callback, *,
                 version='', first_version=None):
        self.score_jsapi_op_name = name
        self.score_jsapi_op_version = str(version)
        self.__endpoint = endpoint
        if first_version:
            self.first_version = first_version
            self.first_version.__versions.append(self)
        else:
            self.first_version = self
            self.__versions = []
        # The next call will store the callback as self.__wrapped__
        functools.update_wrapper(self, callback)
        # Register this operation with the endpoint
        self.__endpoint._register_op(self)

    def __call__(self, *args, **kwargs):
        """
        Invoke wrapped callback.
        """
        return self.__wrapped__(*args, **kwargs)

    def score_jsapi_create_version(self, name):
        """
        Create a wrapper function for a newer version of this operation.

        The alias of this function is just `version`, so you can create newer
        versions of your operations with the following code:

        .. code-block:: python

            @endpoint.op
            def op():
                pass

            @op.version(2)
            def op():
                pass

        The version *name* will be converted to a string and increasing version
        numbers should be sortable as strings. Within these constraints, the
        following version names are valid:

        .. code-block:: python

            @op.version(2)
            def op():
                pass

            @op.version(3)
            def op():
                pass

            @op.version("3.1")
            def op():
                pass

        The following usage will not work as expected, since the version "ham"
        will be interpreted as an earlier version as "spam" (since
        "ham" < "spam") and the generated javascript will call the "spam"
        version by default (since it is considered the latest version because of
        that ordering):

        .. code-block:: python

            @op.version("spam")
            def op():
                pass

            @op.version("ham")
            def op():
                pass

        """
        def version_annotation(callback):
            return EndpointOperation(
                self.score_jsapi_op_name, self.__endpoint, callback,
                version=name, first_version=self.first_version)
        return version_annotation

    version = score_jsapi_create_version

    @property
    def score_jsapi_op_versions(self):
        return tuple(self.first_version.__versions)


class Endpoint(metaclass=abc.ABCMeta):
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
        return EndpointOperation(func.__name__, self, func)

    def _register_op(self, operation):
        """
        Registers an operation. This function is called from the constructor of
        :class:`EndpointOperation`.
        """
        name = operation.score_jsapi_op_name
        for argname in inspect.signature(operation).parameters:
            if argname in ('self', 'cls'):
                continue
            if argname != 'ctx':
                raise ValueError("First argument must be the context 'ctx'")
            break
        if name in self.ops:
            raise ValueError('Operation "%s" already registered' % name)
        self.ops[(name, operation.score_jsapi_op_version)] = operation

    def call(self, name, version, arguments, ctx_members={}):
        """
        Calls function with given *name* and the given `list` of *arguments*.

        It is also possible to set some :term:`context members <context member>`
        before calling the actual handler for the operation.

        Will return a tuple consisting of a boolean success indicator and the
        actual response. The response depends on two factors:

        - If the call was successfull (i.e. no exception), it will contain the
          return value of the function.
        - If a non-safe exception was caught (i.e. one that does not derive from
          :class:`SafeException`) and the module was configured to expose
          internal data (via the init configuration value "expose"), the
          response will consist of the json-convertible representation of the
          exception, which is achievede with the help of :func:`exc2json`
        - If a :class:`.SafeException` was caught and the module was configured
          *not* to expose internal data, it will convert the exception type and
          message only (again via :func:`exc2json`). Thus, the javascript part
          will not receive a stack trace.
        - The last case (non-safe exception, expose is `False`), the *result*
          part will be `None`.
        """
        try:
            with self.conf.ctx.Context() as ctx:
                for member, value in ctx_members.items():
                    setattr(ctx, member, value)
                return True, self.ops[(name, version)](ctx, *arguments)
        except Exception as e:
            if not isinstance(e, SafeException):
                log.exception(e)
            if self.conf.expose:
                result = exc2json(sys.exc_info(), [__file__])
            elif isinstance(e, SafeException):
                result = exc2json([type(e), str(e)])
            else:
                result = None
            return False, result

    def _render_ops_js(self):
        op_defs = []
        for key in sorted(self.ops):
            funcname, version = key
            func = self.ops[key]
            minargs = 0
            maxargs = 0
            argnames = []
            skipped_ctx = False
            for name, param in inspect.signature(func).parameters.items():
                if not skipped_ctx:
                    skipped_ctx = True
                    continue
                argnames.append(name)
                maxargs += 1
                if param.default == inspect.Parameter.empty:
                    minargs += 1
            op_defs.append({
                "name": funcname,
                "version": version,
                "minargs": minargs,
                "maxargs": maxargs,
                "argnames": argnames
            })
        return json.dumps(op_defs)

    @abc.abstractmethod
    def render_js(self, conf):
        return ''


class UrlEndpoint(Endpoint):
    """
    An Endpoint, which can be accessed via AJAX from javascript.
    """

    template = '''
        // Universal Module Loader
        // https://github.com/umdjs/umd
        // https://github.com/umdjs/umd/blob/v1.0.0/returnExports.js
        (function (root, factory) {
            if (typeof define === 'function' && define.amd) {
                // AMD. Register as an anonymous module.
                define(['../endpoint/url'], factory);
            } else if (typeof module === 'object' && module.exports) {
                // Node. Does not work with strict CommonJS, but
                // only CommonJS-like environments that support module.exports,
                // like Node.
                module.exports = factory(require('../endpoint/url'));
            } else {
                factory(root.score.jsapi.UrlEndpoint);
            }
        })(this, function(UrlEndpoint) {

            return new UrlEndpoint("%s", %s, "%s", "%s");

        });
    '''

    def __init__(self, name, *, method="POST"):
        super().__init__(name)
        self.url = '/jsapi/' + name
        self.method = method

    def handle(self, requests, ctx_members={}):
        """
        Handles all functions calls passed with a request.

        The provided *requests* variable needs to be a list of "calls", where
        each call is a list containing the function name as first entry, the
        version of the operation as second entry, and the arguments for the
        invocation as the rest of the list. Example value for *requests* with a
        call to the initial version of an addition function and a call to the
        second version of a division function::

            [["add", "", 40, 2],
             ["divide", "2", 42, 0]]

        The return value will be a list with two elements, one containing
        success values, the other containing results::

            [[True, False], [42, None]]

        See :meth:`Endpoint.call` for details on the result values, especially
        the explanation of the `None` value, above.

        The input and output is already in the correct format for communication
        with the javascript part, so the result can be sent as
        "application/json"-encoded response to the calling javascript function.
        """
        responses = []
        for r in requests:
            name = r[0]
            version = r[1]
            args = r[2:]
            if log.isEnabledFor(logging.DEBUG):
                start = time.time()
            success, result = self.call(
                name, version, args, ctx_members=ctx_members)
            if log.isEnabledFor(logging.DEBUG):
                desc = name
                if version is not None:
                    desc = '%s/v%s' % (name, version)
                log.debug(
                    'Handled call to `%s` in %dms: %s',
                    desc,
                    1000 * (time.time() - start),
                    'success' if success else 'error',
                )
            responses.append({
                'success': success,
                'result': result,
            })
        return responses

    def render_js(self, conf):
        url = conf.http.url(None, 'score.jsapi:' + self.name)
        return self.template % (
            self.name, self._render_ops_js(), url, self.method)


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
            console.error('Error (' + msg[0] + '): ' + msg[1]);
            // will output:
            //   Error (ZeroDivision): Cannot divide by zero
        });

    """
