# Copyright © 2015-2018 STRG.AT GmbH, Vienna, Austria
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

import inspect
import json
import logging
import os
import textwrap
from collections import OrderedDict

from score.init import (
    ConfigurationError, ConfiguredModule, parse_bool, parse_dotted_path,
    parse_list)
from score.tpl import TemplateNotFound
from score.tpl.loader import Loader

from ._endpoint import SafeException, UrlEndpoint

log = logging.getLogger(__name__)


defaults = {
    'endpoints': [],
    'expose': False,
    'serve.outdir': None,
}


def init(confdict, ctx, tpl, http):
    """
    Initializes this module acoording to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`endpoint` :confdefault:`None`
        Optional single endpoint value that can be provided for convenience.
        See `endpoints`, below, for details.

    :confkey:`endpoints` :confdefault:`list()`
        A :func:`list <score.init.parse_list>` of :func:`dotted paths
        <score.init.parse_dotted_path>` pointing to any amount of
        :class:`Endpoints <.Endpoint>`. The registered functions of these
        Endpoints will be available in javascript.

    :confkey:`expose` :confdefault:`False`
        Whether security critical data may be exposed through the API. This
        value should be left at its default value in production, but may be
        switched to `True` during development to receive Exceptions and
        stacktraces in the browser console.

    :confkey:`serve.outdir` :confdefault:`None`
        A folder, where this module's :mod:`score.serve` worker will dump all
        javascript files required to make use of this module in a javascript
        environment.

    """
    conf = dict(defaults.items())
    conf.update(confdict)
    endpoints = list(map(parse_dotted_path, parse_list(conf['endpoints'])))
    if 'endpoint' in conf:
        endpoints.append(parse_dotted_path(conf['endpoint']))
    expose = parse_bool(conf['expose'])
    if conf['serve.outdir'] and not os.path.isdir(conf['serve.outdir']):
        raise ConfigurationError(
            'score.jsapi', 'Configured serve.outdir does not exist')
    return ConfiguredJsapiModule(ctx, tpl, http, endpoints, expose,
                                 conf['serve.outdir'])


js_keywords = (
    'abstract', 'arguments', 'boolean', 'break', 'byte', 'case', 'catch',
    'char', 'class*', 'const', 'continue', 'debugger', 'default', 'delete',
    'do', 'double', 'else', 'enum*', 'eval', 'export*', 'extends*', 'false',
    'final', 'finally', 'float', 'for', 'function', 'goto', 'if', 'implements',
    'import*', 'in', 'instanceof', 'int', 'interface', 'let', 'long', 'native',
    'new', 'null', 'package', 'private', 'protected', 'public', 'return',
    'short', 'static', 'super*', 'switch', 'synchronized', 'this', 'throw',
    'throws', 'transient', 'true', 'try', 'typeof', 'var', 'void', 'volatile',
    'while', 'with', 'yield',)


def _make_api(endpoint):
    def api(ctx):
        if endpoint.method == "POST":
            assert ctx.http.request.content_type == 'application/json'
            requests = json.loads(str(ctx.http.request.body,
                                      ctx.http.request.charset))
        else:
            requests = map(json.loads,
                           ctx.http.request.GET.getall('requests[]'))
        results = endpoint.handle(requests, {'http': ctx.http})
        ctx.http.response.content_type = 'application/json; charset=UTF-8'
        ctx.http.response.json = results
        return ctx.http.response
    return api


class JsapiTemplateLoader(Loader):

    jsapi_template = textwrap.dedent('''
        // Universal Module Loader
        // https://github.com/umdjs/umd
        // https://github.com/umdjs/umd/blob/v1.0.0/returnExports.js
        (function (root, factory) {
            if (typeof define === 'function' && define.amd) {
                // AMD. Register as an anonymous module.
                define(%s, factory);
            } else if (typeof module === 'object' && module.exports) {
                // Node. Does not work with strict CommonJS, but
                // only CommonJS-like environments that support module.exports,
                // like Node.
                module.exports = factory(%s);
            }
        })(this, function(UnifiedApi) {

            return UnifiedApi;

        });
    ''').lstrip()

    exceptions_template = textwrap.dedent('''
        // Universal Module Loader
        // https://github.com/umdjs/umd
        // https://github.com/umdjs/umd/blob/v1.0.0/returnExports.js
        (function (root, factory) {
            if (typeof define === 'function' && define.amd) {
                // AMD. Register as an anonymous module.
                define(['./exception'], factory);
            } else if (typeof module === 'object' && module.exports) {
                // Node. Does not work with strict CommonJS, but
                // only CommonJS-like environments that support module.exports,
                // like Node.
                module.exports = factory(require('./exception'));
            }
        })(this, function(Exception) {

            var definitions = %s;

            for (var name in definitions) {
                Exception.define(name, definitions[name]);
            }

        });
    ''').lstrip()

    def __init__(self, jsapi):
        self.conf = jsapi

    def iter_paths(self):
        here = os.path.dirname(__file__)
        rootdir = os.path.join(here, 'js')
        for base, dirs, files in os.walk(rootdir):
            dirs.sort()
            for filename in sorted(files):
                path = os.path.join(base, filename)
                yield 'score/jsapi/' + os.path.relpath(path, rootdir)
        for name in self.conf.endpoints:
            yield 'score/jsapi/endpoints/%s.js' % (name,)
        yield 'score/jsapi/exceptions.js'
        yield 'score/jsapi.js'

    def load(self, path):
        if path == 'score/jsapi.js':
            dependencies = ['./jsapi/unified', './jsapi/exceptions'] + [
                './jsapi/endpoints/%s' % name
                for name in self.conf.endpoints]
            return False, (self.jsapi_template % (
                json.dumps(dependencies),
                ', '.join('require("%s")' % dep for dep in dependencies)
            ))
        elif path == 'score/jsapi/exceptions.js':
            exceptions = {}

            def add_subclasses(cls):
                parent = cls.__name__
                if cls == SafeException:
                    parent = None
                for exc in cls.__subclasses__():
                    exceptions[exc.__name__] = parent
                    add_subclasses(exc)
            add_subclasses(SafeException)
            return False, (self.exceptions_template % (json.dumps(exceptions)))
        here = os.path.dirname(__file__)
        file = os.path.join(here, 'js', path[len('score/jsapi/'):])
        if os.path.exists(file):
            return True, file
        for endpoint in self.conf.endpoints.values():
            enpoint_path = 'score/jsapi/endpoints/%s.js' % (endpoint.name,)
            if path == enpoint_path:
                return False, endpoint.render_js(self.conf)
        raise TemplateNotFound(path)


class ConfiguredJsapiModule(ConfiguredModule):
    """
    This module's :class:`configuration class <score.init.ConfiguredModule>`.

    The object also provides a worker for :mod:`score.serve`, which will
    dump all javascript files generated by this module into a folder that was
    configured as `serve.outdir`.
    """

    def __init__(self, ctx, tpl, http, endpoints, expose, serve_outdir):
        super().__init__(__package__)
        self.ctx = ctx
        self.tpl = tpl
        self.http = http
        self.expose = expose
        self.serve_outdir = serve_outdir
        self.endpoints = OrderedDict()
        for endpoint in endpoints:
            self.add_endpoint(endpoint)
        self.tpl_loader = JsapiTemplateLoader(self)
        tpl.loaders['js'].append(self.tpl_loader)

    def add_endpoint(self, endpoint):
        assert not self._finalized
        for funcname in endpoint.ops:
            if funcname in js_keywords:
                raise ConfigurationError(
                    __package__,
                    'Exposed function `%s\'s name is '
                    'a reserved keyword in javascript' %
                    funcname)
            func = endpoint.ops[funcname]
            for name in inspect.signature(func).parameters:
                if name in js_keywords:
                    raise ConfigurationError(
                        __package__,
                        'Exposed function `%s\' has parameter `%s\', which is '
                        'a reserved keyword in javascript' %
                        (funcname, name))
        self.endpoints[endpoint.name] = endpoint
        endpoint.conf = self
        if isinstance(endpoint, UrlEndpoint):
            name = endpoint.name
            api = _make_api(endpoint)
            self.http.newroute('score.jsapi:' + name, endpoint.url)(api)

    def score_serve_workers(self):
        import score.serve
        if not self.serve_outdir:
            raise ConfigurationError(
                'score.jsapi', 'Cannot create Worker: No outdir configured')

        class Worker(score.serve.SimpleWorker):

            def __init__(self, conf):
                self.conf = conf

            def loop(self):
                for path in self.conf.tpl_loader.iter_paths():
                    reduced_path = path[len('score/'):]
                    file = os.path.join(self.conf.serve_outdir, reduced_path)
                    os.makedirs(os.path.dirname(file), exist_ok=True)
                    open(file, 'w').write(self.conf.tpl.render(path))

        return {'watcher': Worker(self)}
