define("lib/score/jsapi", ["lib/score/oop", "lib/bluebird"], function(oop, BPromise) {

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

    var Endpoint = oop.Class({
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

    Endpoint.URL = oop.Class({
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
                    request.open('GET', self.url + data.join('&'));
                    request.send();
                } else {
                    request.open(self.method, self.url);
                    request.setRequestHeader("Content-Type", "application/json");
                    request.send(JSON.stringify(requests));
                }
            });
        }

    });

    var Queue = oop.Class({
        __name__: 'JsApi__Queue',

        __init__: function(self) {
            self.queuedRequests = [];
            self.flushDeferred = null;
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
                return endpoint.send(payload).then(function(results) {
                    for (var i = 0; i < requests.length; i++) {
                        var success = results[0][i];
                        var result = results[1][i];
                        if (success) {
                            requests[i].resolve(result);
                        } else {
                            if (result && result[2]) {
                                var args = [];
                                for (var j = 1; j < requests[i].data.length; j++) {
                                    args.push(requests[i].data[j]);
                                }
                                var msg = '\nTraceback (most recent call last):\n';
                                for (var j = 0; j < result[2].length; j++) {
                                    var frame = result[2][j];
                                    msg += '  File "' + frame[0] +
                                           '", line "' + frame[1] +
                                           '", in ' + frame[2] + '\n';
                                    msg += '    ' + frame[3] + '\n';
                                }
                                msg += '\n' + result[0] + ': ' + result[1] + '\n'
                                console.error('Error in jsapi call', requests[i].data[0], args, msg);
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

    var JsApi = oop.Class({
        __name__: 'JsApi',

        __static__: {

            ops: {

                %s

            }

        },

        __init__: function(self) {
            self.queue = new Queue();
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

    return new JsApi();

});
