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
        define(['./endpoint', './exception'], factory);
    } else if (typeof module === 'object' && module.exports) {
        // Node. Does not work with strict CommonJS, but
        // only CommonJS-like environments that support module.exports,
        // like Node.
        module.exports = factory(require('./endpoint'), require('./exception'));
    } else {
        // Browser globals (root is window)
        root.score.jsapi.Queue = factory(root.score.jsapi.Endpoint, root.score.jsapi.Exception);
    }
})(this, function(Endpoint, Exception) {

    var defer = function() {
        var resolve, reject;
        var promise = new Promise(function(res, rej) {
            resolve = res;
            reject = rej;
        });
        return {
            promise: promise,
            resolve: resolve,
            reject: reject,
        };
    };

    var Queue = function() {
        this.queuedRequests = [];
        this.flushDeferred = null;
    };

    Queue.prototype = Object.create(Object.prototype);

    Queue.prototype.queue = function(data, endpoint) {
        var request = defer();
        request.data = data;
        request.endpoint = endpoint;
        this.queuedRequests.push(request);
        return request.promise;
    };

    Queue.prototype.flush = function() {
        var self = this;
        // return existing flush promise, if there is one
        if (this.flushDeferred) {
            return this.flushDeferred.promise;
        }
        // do we have any requests to flush?
        if (!this.queuedRequests.length) {
            // TODO: No IE support for Promise.resolve()
            return Promise.resolve();
        }
        this.flushDeferred = defer();
        // wait until current code block is finished before sending the
        // request to the server, we might receive some more requests.
        window.setTimeout(function() {
            self._flush();
        }, 1);
        return this.flushDeferred.promise;
    };

    Queue.prototype._flush = function() {
        var self = this;
        // map transport name to its requests
        var requests = {};
        for (var i = 0; i < self.queuedRequests.length; i++) {
            var r = self.queuedRequests[i];
            if (!(r.endpoint.name in requests)) {
                requests[r.endpoint.name] = [];
            }
            requests[r.endpoint.name].push(r);
        }
        // send each endpoint's requests
        var send = function(endpoint, requests) {
            var payload = [];
            for (var i = 0; i < requests.length; i++) {
                payload.push(requests[i].data);
            }
            return endpoint.send(payload).then(function(responses) {
                for (var i = 0; i < responses.length; i++) {
                    var response = responses[i],
                        success = response.success,
                        result = response.result;
                    if (success) {
                        requests[i].resolve(result);
                    } else {
                        if (result && result.trace) {
                            var args = ['Error in jsapi call', requests[i].data[0], '('];
                            for (var j = 1; j < requests[i].data.length; j++) {
                                if (j != 1) {
                                    args.push(',');
                                }
                                args.push(requests[i].data[j]);
                            }
                            args.push(')');
                            args.push("\n" + excformat(result));
                            console.error.apply(console, args);
                        }
                        if (result) {
                            if (result.type in Exception.classes) {
                                result = Exception.classes[result.type](result.message);
                            } else {
                                result = new Exception(result.message);
                            }
                        } else {
                            result = new Exception();
                        }
                        requests[i].reject(result);
                    }
                }
            }).catch(function(error) {
                for (var i = 0; i < requests.length; i++) {
                    requests[i].reject(error);
                };
            });
        };
        var promises = [];
        for (var endpointName in requests) {
            promises.push(send(Endpoint.get(endpointName), requests[endpointName]));
        }
        // TODO: No IE support for Promise.all()
        var promise = Promise.all(promises);
        // store instance variables and reset object state
        var flushDeferred = self.flushDeferred;
        self.queuedRequests = [];
        self.flushDeferred = null;
        // resolve flushDeferred once the flush is complete
        promise.then(function() {
            flushDeferred.resolve();
        });
        return promise;
    };

    return Queue;

});
