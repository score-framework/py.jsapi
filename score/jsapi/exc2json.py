# Copyright © 2015-2018 STRG.AT GmbH, Vienna, Austria
# Copyright © 2018-2019 Necdet Can Ateşman <can@atesman.at>, Vienna, Austria
#
# This file is part of the The SCORE Framework.
#
# The SCORE Framework and all its parts are free software: you can redistribute
# them and/or modify them under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation which is in
# the file named COPYING.LESSER.txt.
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
# the discretion of STRG.AT GmbH also the competent court, in whose district
# the Licensee has his registered seat, an establishment or assets.


import traceback


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

    It is possible to omit the last value of *excinfo*, effectively reducing
    the generated exception description to a class name and a message.

    The optional parameter *untrace* contains file names that will be removed
    from the beginning of the stack trace.
    """
    trace = None
    if len(excinfo) > 2:
        trace = traceback.extract_tb(excinfo[2])
        untrace.append(__file__)
        while trace and any(skip for skip in untrace if skip in trace[0][0]):
            trace = trace[1:]
        trace = list(map(
            lambda frame: (frame[0], frame[1], frame[2], frame[3]), trace))
    return {
        'type': excinfo[0].__name__,
        'message': str(excinfo[1]),
        'trace': trace,
    }
