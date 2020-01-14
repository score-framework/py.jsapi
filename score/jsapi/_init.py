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

import abc
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


VALID_FORMATS = ('umd', 'es6')


defaults = {
    'endpoints': [],
    'expose': False,
    'js.format': 'umd',
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
    if conf['js.format'] not in VALID_FORMATS:
        raise ConfigurationError(
            'score.jsapi', 'Invalid js.format "%s"' % (conf['js.format'],))
    return ConfiguredJsapiModule(ctx, tpl, http, endpoints, expose,
                                 conf['js.format'], conf['serve.outdir'])


js_keywords = (
    'abstract', 'arguments', 'boolean', 'break', 'byte', 'case', 'catch',
    'char', 'class', 'const', 'continue', 'debugger', 'default', 'delete',
    'do', 'double', 'else', 'enum', 'eval', 'export', 'extends', 'false',
    'final', 'finally', 'float', 'for', 'function', 'goto', 'if', 'implements',
    'import', 'in', 'instanceof', 'int', 'interface', 'let', 'long', 'native',
    'new', 'null', 'package', 'private', 'protected', 'public', 'return',
    'short', 'static', 'super', 'switch', 'synchronized', 'this', 'throw',
    'throws', 'transient', 'true', 'try', 'typeof', 'var', 'void', 'volatile',
    'while', 'with', 'yield',)


def _make_api(endpoint):
    def api(ctx):
        if endpoint.method == "POST":
            if ctx.http.request.content_type != 'application/json':
                ctx.http.response.status = '400 Invalid Content-Type'
                return ctx.http.response
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

    _exceptions_map = None

    def __init__(self, jsapi):
        self.conf = jsapi

    def iter_paths(self):
        here = os.path.dirname(__file__)
        rootdir = os.path.join(here, 'tpl', self.conf.js_format)
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
            return self.render_jsapi()
        elif path == 'score/jsapi/exceptions.js':
            return self.render_exceptions()
        here = os.path.dirname(__file__)
        file = os.path.join(here, 'tpl', self.conf.js_format,
                            path[len('score/jsapi/'):])
        if os.path.exists(file):
            return True, file
        for endpoint in self.conf.endpoints.values():
            enpoint_path = 'score/jsapi/endpoints/%s.js' % (endpoint.name,)
            if path == enpoint_path:
                return False, endpoint.render_js(self.conf)
        raise TemplateNotFound(path)

    @property
    def exceptions_map(self):
        if self._exceptions_map is None:
            self._exceptions_map = OrderedDict()

            def add_subclasses(cls):
                parent = cls.__name__
                if cls == SafeException:
                    parent = None
                for exc in cls.__subclasses__():
                    self._exceptions_map[exc.__name__] = parent
                    add_subclasses(exc)
            add_subclasses(SafeException)
        return self._exceptions_map

    @abc.abstractmethod
    def render_jsapi(self):
        pass

    @abc.abstractmethod
    def render_exceptions(self):
        pass


class JsapiUmdTemplateLoader(JsapiTemplateLoader):

    jsapi_template = textwrap.dedent('''
        /* eslint-disable */
        /* tslint:disable */
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
        /* eslint-disable */
        /* tslint:disable */
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

    def render_jsapi(self):
        dependencies = ['./jsapi/unified', './jsapi/exceptions'] + [
            './jsapi/endpoints/%s' % name
            for name in self.conf.endpoints]
        return False, (self.jsapi_template % (
            json.dumps(dependencies),
            ', '.join('require("%s")' % dep for dep in dependencies)
        ))

    def render_exceptions(self):
        return False, (self.exceptions_template % (
            json.dumps(self.exceptions_map)))


class JsapiEs6TemplateLoader(JsapiTemplateLoader):

    jsapi_template = textwrap.dedent('''
        /* eslint-disable */
        /* tslint:disable */
        import Jsapi from './unified';

        import * as endpoints from './endpoints';
        import * as exceptions from './exceptions';

        export * from './exceptions';

        export const jsapi = new Jsapi([%s], [%s]);

        export default jsapi;
    ''').lstrip()

    exceptions_template = textwrap.dedent('''
        /* eslint-disable */
        /* tslint:disable */
        import Exception from './exception';

        %s
    ''').lstrip()

    endpoints_template = textwrap.dedent('''
        /* eslint-disable */
        /* tslint:disable */
        %s
    ''').lstrip()

    def iter_paths(self):
        yield from (path for path in super().iter_paths()
                    if path != 'score/jsapi.js')
        yield 'score/jsapi/endpoints/index.js'
        yield 'score/jsapi/index.js'

    def load(self, path):
        if path == 'score/jsapi/index.js':
            return self.render_jsapi()
        if path == 'score/jsapi/endpoints/index.js':
            return self.render_endpoints()
        return super().load(path)

    def render_endpoints(self):
        return False, (self.endpoints_template % (
            '\n'.join(
                'export * from \'./%s\';' % (name,)
                for name in self.conf.endpoints)))

    def render_jsapi(self):
        return False, (self.jsapi_template % (
            ', '.join('endpoints.%s' % (name,)
                      for name in self.conf.endpoints),
            ', '.join('exceptions.%s' % (name,)
                      for name in self.exceptions_map),
        ))

    def render_exceptions(self):
        definitions = '\n'.join(
            "export const %s = Exception.define('%s', %s);" % (
                name, name, parent if parent else 'null')
            for name, parent in self.exceptions_map.items())
        return False, (self.exceptions_template % (definitions))


class ConfiguredJsapiModule(ConfiguredModule):
    """
    This module's :class:`configuration class <score.init.ConfiguredModule>`.

    The object also provides a worker for :mod:`score.serve`, which will
    dump all javascript files generated by this module into a folder that was
    configured as `serve.outdir`.
    """

    def __init__(self, ctx, tpl, http, endpoints, expose,
                 js_format, serve_outdir):
        super().__init__(__package__)
        self.ctx = ctx
        self.tpl = tpl
        self.http = http
        self.expose = expose
        self.js_format = js_format
        self.serve_outdir = serve_outdir
        self.endpoints = OrderedDict()
        for endpoint in endpoints:
            self.add_endpoint(endpoint)
        if js_format == 'umd':
            self.tpl_loader = JsapiUmdTemplateLoader(self)
        else:
            self.tpl_loader = JsapiEs6TemplateLoader(self)
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
                self.conf.build(self.conf.serve_outdir)

        return {'watcher': Worker(self)}

    def build(self, target_folder):
        for path in self.tpl_loader.iter_paths():
            reduced_path = path[len('score/'):]
            file = os.path.join(target_folder, reduced_path)
            os.makedirs(os.path.dirname(file), exist_ok=True)
            open(file, 'w').write(self.tpl.render(path))
