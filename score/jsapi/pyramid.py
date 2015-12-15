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

"""
This package :ref:`integrates <framework_integration>` the module with
pyramid_.

.. _pyramid: http://docs.pylonsproject.org/projects/pyramid/en/latest/
"""
import json


def init(confdict, configurator, ctx_conf, js_conf):
    """
    Apart from calling the :func:`base initializer <score.db.init>`, this
    function will also register URLs for all configured :class:`UrlEndpoints
    <UrlEndpoint>`.
    """
    import score.jsapi
    jsapi_conf = score.jsapi.init(confdict, ctx_conf, js_conf)
    for endpoint in jsapi_conf.endpoints:
        if not isinstance(endpoint, score.jsapi.UrlEndpoint):
            continue
        name = endpoint.name
        route_name = 'score.jsapi:' + name
        api = _make_api(endpoint)
        configurator.add_route(route_name, endpoint.url)
        configurator.add_view(api, route_name=route_name)
    return jsapi_conf


def _make_api(endpoint):
    def api(request):
        if endpoint.method == "POST":
            assert request.content_type == 'application/json'
            requests = json.loads(str(request.body, request.charset))
        else:
            requests = map(json.loads, request.GET.getall('requests[]'))
        results = endpoint.handle(requests, {'request': request})
        request.response.content_type = 'application/json; charset=UTF-8'
        request.response.json = results
        return request.response
    return api
