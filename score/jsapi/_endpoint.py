import inspect
import logging
from .exc2json import exc2json
import sys
import time

log = logging.getLogger('score.jsapi')


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
            if argname in ('self', 'cls'):
                continue
            if argname != 'ctx':
                raise ValueError("First argument must be the context 'ctx'")
            break
        self.ops[name] = func
        return func

    def call(self, name, arguments, ctx_members={}):
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
            with self.conf.ctx_conf.Context() as ctx:
                for member, value in ctx_members.items():
                    setattr(ctx, member, value)
                return True, self.ops[name](ctx, *arguments)
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

    def _js_args(self, conf):
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

    def handle(self, requests, ctx_members={}):
        """
        Handles all functions calls passed with a request.

        The provided *requests* variable needs to be a list of "calls", where
        each call is a json-encoded list containing the function name as first
        entry, and its arguments as the rest of the list. Example value for
        *requests* with a call to an addition and a division::

            ['["add",40,2]',
             '["divide",42,0]']

        The return value will be a list with two elements, one containing
        success values, the other containing results::

            [[True, False], [42, None]]

        See :meth:`Endpoint.call` for details on the result values, especially
        the explanation of the `None` value, above.

        The input and output is already in the correct format for communication
        with the javascript part, so the result can be sent as
        "application/json"-encoded response to the calling javascript function.
        See the pyramid implementation for example usage of this function.
        """
        responses = []
        for r in requests:
            name = r[0]
            args = r[1:]
            if log.isEnabledFor(logging.DEBUG):
                start = time.time()
            success, result = self.call(name, args, ctx_members=ctx_members)
            if log.isEnabledFor(logging.DEBUG):
                log.debug(
                    'Handled call to `%s` in %dms: %s',
                    name,
                    1000 * (time.time() - start),
                    'success' if success else 'error',
                )
            responses.append({
                'success': success,
                'result': result,
            })
        return responses

    def _js_args(self, conf):
        return ['"%s"' % self.conf.http.url(None, 'score.jsapi:' + self.name),
                '"%s"' % self.method]


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
