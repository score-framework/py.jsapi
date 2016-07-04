// Copyright © 2015 STRG.AT GmbH, Vienna, Austria
//
// This file is part of the The SCORE Framework.
//
// The SCORE Framework and all its parts are free software: you can redistribute
// them and/or modify them under the terms of the GNU Lesser General Public
// License version 3 as published by the Free Software Foundation which is in the
// file named COPYING.LESSER.txt.
//
// The SCORE Framework and all its parts are distributed without any WARRANTY;
// without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
// PARTICULAR PURPOSE. For more details see the GNU Lesser General Public
// License.
//
// If you have not received a copy of the GNU Lesser General Public License see
// http://www.gnu.org/licenses/.
//
// The License-Agreement realised between you as Licensee and STRG.AT GmbH as
// Licenser including the issue of its valid conclusion and its pre- and
// post-contractual effects is governed by the laws of Austria. Any disputes
// concerning this License-Agreement including the issue of its valid conclusion
// and its pre- and post-contractual effects are exclusively decided by the
// competent court, in whose district STRG.AT GmbH has its registered seat, at
// the discretion of STRG.AT GmbH also the competent court, in whose district the
// Licensee has his registered seat, an establishment or assets.

define("%s", ["bluebird", "lib/score/js/excformat", "score.init", "score.oop"], function(BPromise, excformat, score) {

    var defer = function() {
        var resolve, reject;
        var promise = new BPromise(function(res, rej) {
            resolve = res;
            reject = rej;
        });
        return {
            promise: promise,
            resolve: resolve,
            reject: reject,
        };
    };

    var SafeException = score.oop.Class({
        __name__: 'SafeException',
        __parent__: score.oop.Exception
    });

    var Endpoint = score.oop.Class({
        __name__: 'JsApi__Endpoint',

        __static__: {

            instances: {},

            get: function(cls, id) {
                return Endpoint.instances[id];
            }

        },

        __init__: function(self, id) {
            self.id = id;
            Endpoint.instances[id] = self;
        },

        send: function(self, requests) {
            throw new Error('abstract function');
        }

    });

    Endpoint.URL = score.oop.Class({
        __name__: 'JsApi__Endpoint__URL',
        __parent__: Endpoint,

        __init__: function(self, id, url, method) {
            self.__super__(id);
            self.url = url;
            self.method = method || 'POST';
        },

        send: function(self, requests) {
            return new BPromise(function(resolve, reject) {
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
        }

    });

    var Queue = score.oop.Class({
        __name__: 'JsApi__Queue',

        __init__: function(self, api) {
            self.queuedRequests = [];
            self.flushDeferred = null;
            self.api = api;
        },

        queue: function(self, data, endpoint) {
            var request = defer();
            request.data = data;
            request.endpoint = endpoint;
            self.queuedRequests.push(request);
            return request.promise;
        },

        flush: function(self) {
            // return existing flush promise, if there is one
            if (self.flushDeferred) {
                return self.flushDeferred.promise;
            }
            // do we have any requests to flush?
            if (!self.queuedRequests.length) {
                return BPromise.resolve();
            }
            self.flushDeferred = defer();
            // wait until current code block is finished before sending the
            // request to the server, we might receive some more requests.
            window.setTimeout(function() {
                self._flush();
            }, 1);
            return self.flushDeferred.promise;
        },

        _flush: function(self) {
            // map transport id to its requests
            var requests = {};
            for (var i = 0; i < self.queuedRequests.length; i++) {
                var r = self.queuedRequests[i];
                if (!(r.endpoint.id in requests)) {
                    requests[r.endpoint.id] = [];
                }
                requests[r.endpoint.id].push(r);
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
                                if (result.type in self.api.exc) {
                                    result = self.api.exc[result.type](result.message);
                                } else {
                                    result = new score.oop.Exception(result.message);
                                }
                            } else {
                                result = new score.oop.Exception();
                            }
                            requests[i].reject(result);
                        }
                    }
                });
            };
            var promises = [];
            for (var endpointId in requests) {
                promises.push(send(Endpoint.get(endpointId), requests[endpointId]));
            }
            var promise = BPromise.all(promises);
            // store instance variables and reset object state
            var flushDeferred = self.flushDeferred;
            self.queuedRequests = [];
            self.flushDeferred = null;
            // resolve flushDeferred once the flush is complete
            promise.then(function() {
                flushDeferred.resolve();
            });
            return promise;
        }

    });

    var exc = {

        SafeException: SafeException

    };

    %s

    var JsApi = score.oop.Class({
        __name__: 'JsApi',

        __static__: {

            exc: exc,

            ops: {

                %s

            }

        },

        __init__: function(self) {
            self.queue = new Queue(self);
        },

        _call: function(self, func, args) {
            if (!(func in self.ops)) {
                throw new Error("Undefined operation '" + func + "'");
            }
            var op = self.ops[func];
            if (op.minargs == op.maxargs) {
                if (args.length != op.minargs) {
                    throw new Error("Invalid number of arguments for operation '" + func + "': Expected: " + op.minargs + ", Received: " + args.length);
                }
            } else {
                if (args.length < op.minargs) {
                    throw new Error("Too few arguments for operation " + func + ": Expected at least " + op.minargs + ", received: " + args.length);
                }
                if (args.length > op.maxargs) {
                    throw new Error("Too many arguments for operation " + func + ": Expected at most " + op.maxargs + ", received: " + args.length);
                }
            }
            var request = [func];
            for (var i = 0; i < args.length; i++) {
                if (typeof args[i] === 'undefined') {
                    throw new Error("Error in invocation of operation " + func + ": Argument '" + op.argnames[i] + "' is undefined");
                }
                request.push(args[i]);
            }
            return self.queue.queue(request, Endpoint.get(op.endpointId));
        },

        _flush: function(self, queueName) {
            return self.queue.flush();
        },

        %s

    });

    %s

    return JsApi;

});
