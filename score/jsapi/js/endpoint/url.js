/**
 * Copyright © 2015-2017 STRG.AT GmbH, Vienna, Austria
 *
 * This file is part of the The SCORE Framework.
 *
 * The SCORE Framework and all its parts are free software: you can redistribute
 * them and/or modify them under the terms of the GNU Lesser General Public
 * License version 3 as published by the Free Software Foundation which is in the
 * file named COPYING.LESSER.txt.
 *
 * The SCORE Framework and all its parts are distributed without any WARRANTY;
 * without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. For more details see the GNU Lesser General Public
 * License.
 *
 * If you have not received a copy of the GNU Lesser General Public License see
 * http://www.gnu.org/licenses/.
 *
 * The License-Agreement realised between you as Licensee and STRG.AT GmbH as
 * Licenser including the issue of its valid conclusion and its pre- and
 * post-contractual effects is governed by the laws of Austria. Any disputes
 * concerning this License-Agreement including the issue of its valid conclusion
 * and its pre- and post-contractual effects are exclusively decided by the
 * competent court, in whose district STRG.AT GmbH has its registered seat, at
 * the discretion of STRG.AT GmbH also the competent court, in whose district the
 * Licensee has his registered seat, an establishment or assets.
 */

// Universal Module Loader
// https://github.com/umdjs/umd
// https://github.com/umdjs/umd/blob/v1.0.0/returnExports.js
(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['../endpoint'], factory);
    } else if (typeof module === 'object' && module.exports) {
        // Node. Does not work with strict CommonJS, but
        // only CommonJS-like environments that support module.exports,
        // like Node.
        module.exports = factory(require('../endpoint'));
    } else {
        // Browser globals (root is window)
        root.score.jsapi.UrlEndpoint = factory(root.score.jsapi.Endpoint);
    }
})(this, function(Endpoint) {

    UrlEndpoint = function(name, operations, url, method) {
        this.url = url;
        this.method = method || 'POST';
        Endpoint.call(this, name, operations);
    };

    UrlEndpoint.prototype = Object.create(Endpoint.prototype);

    UrlEndpoint.prototype.send = function(requests) {
        var self = this;
        return new Promise(function(resolve, reject) {
            var request = new XMLHttpRequest();
            request.onreadystatechange = function() {
                if (request.readyState !== 4) {
                    return;
                }
                if (request.status === 200) {
                    resolve(JSON.parse(request.responseText));
                }
                msg = 'Received unexpected status code ' +
                    request.status + ': ' + request.statusText;
                reject(new Error(msg));
                return;
            };
            if (self.method === 'GET') {
                var data = [];
                for (var i = 0; i < requests.length; i++) {
                    data.push('requests[]=' + encodeURIComponent(JSON.stringify(requests[i])));
                }
                request.open('GET', self.url + '?' + data.join('&'));
                request.send();
            } else {
                request.open(self.method, self.url);
                request.setRequestHeader("Content-Type", "application/json");
                request.send(JSON.stringify(requests));
            }
        });
    };

    return UrlEndpoint;

});
