import traceback
import textwrap
import json


def exc2json(excinfo, untrace=[]):
    """
    Converts exception info (as returned by :func:`sys.exc_info`) into a
    3-tuple that can be converted into a json string by python's :mod:`json`
    library. It will consist of the exception name, the message and the stack
    trace as provided by :func:`traceback.extract_tb`::

        {
            type: 'ZeroDivisionError',
            message: 'division by zero',
            trace: [
                [<filename>, <lineno>, <line>],
                ...
            ]
        }

    It is possible to omit the last value of *excinfo*, effectively reducing the
    generated exception description to a class name and a message.

    The optional parameter *untrace* contains file names that will be removed
    from the beginning of the stack trace.
    """
    trace = None
    if len(excinfo) > 2:
        trace = traceback.extract_tb(excinfo[2])
        untrace.append(__file__)
        while trace and any(skip for skip in untrace if skip in trace[0][0]):
            trace = trace[1:]
    trace = list(map(lambda frame: (frame[0], frame[1], frame[2], frame[3]),
                     trace))
    return {
        'type': excinfo[0].__name__,
        'message': str(excinfo[1]),
        'trace': trace,
    }


def gen_excformat_js(ctx, requirejs_name=None):
    """
    Generates a javascript function that can convert the return value of of a
    exc2json call to a human-readable stack trace. The resulting string will
    look a lot like the original python stack trace.

    The returned javascript file contains a requirejs definition. It is possible
    to set an explicit define name by passing a *requirejs_name* string.
    """
    if requirejs_name:
        requirejs_name = '%s, ' % json.dump(requirejs_name)
    else:
        requirejs_name = ''
    return textwrap.dedent('''
        define(%sfunction() {
            return function excformat(exc) {
                if (typeof exc.trace === 'undefined') {
                    return exc.type + ': ' + exc.message
                }
                var msg = 'Traceback (most recent call last):\\n';
                for (var j = 0; j < exc.trace.length; j++) {
                    var frame = exc.trace[j];
                    msg += '  File "' + frame[0] +
                        '", line "' + frame[1] +
                        '", in ' + frame[2] + '\\n';
                    msg += '    ' + frame[3] + '\\n';
                }
                msg += '\\n' + exc.type + ': ' + exc.message;
                return msg;
            }
        });
    ''' % requirejs_name).strip()
