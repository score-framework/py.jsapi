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
        define(['./queue', './endpoint', './exception'], factory);
    } else if (typeof module === 'object' && module.exports) {
        // Node. Does not work with strict CommonJS, but
        // only CommonJS-like environments that support module.exports,
        // like Node.
        module.exports = factory(require('./queue'), require('./endpoint'), require('./exception'));
    } else {
        // Browser globals (root is window)
        root.score.jsapi.unified = factory(root.score.jsapi.Queue, root.score.jsapi.Endpoint, root.score.jsapi.Exception);
    }
})(this, function(Queue, Endpoint, Exception) {

    var queue = new Queue();

    var Jsapi = {

        _ops: {},

        _exceptions: {},

        _call: function(func, version, args) {
            if (!(func in Jsapi._ops)) {
                throw new Error("Undefined operation '" + func + "'");
            }
            var op = Jsapi._ops[func];
            if (typeof args == 'undefined') {
                args = version;
                version = op.version;
            }
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
            var request = [func, version];
            for (var i = 0; i < args.length; i++) {
                if (typeof args[i] === 'undefined') {
                    throw new Error("Error in invocation of operation " + func + ": Argument '" + op.argnames[i] + "' is undefined");
                }
                request.push(args[i]);
            }
            return queue.queue(request, op.endpoint);
        },

        _flush: function() {
            return queue.flush();
        }

    };

    var registerOperation = function(endpoint, operation) {
        Jsapi[operation.name] = function() {
            var args = Array.prototype.slice.call(arguments);
            var promise = Jsapi._call(operation.name, args);
            Jsapi._flush();
            return promise;
        };
        Jsapi._ops[operation.name] = {
            name: operation.name,
            version: operation.version,
            minargs: operation.minargs,
            maxargs: operation.maxargs,
            argnames: operation.argnames,
            endpoint: endpoint,
        };
    };

    var registerEndpoint = function(endpoint) {
        for (var i = 0; i < endpoint.operations.length; i++) {
            registerOperation(endpoint, endpoint.operations[i]);
        }
    };

    for (var name in Endpoint.instances) {
        registerEndpoint(Endpoint.instances[name]);
    }

    Endpoint.onCreate(registerEndpoint);

    var registerException = function(name, exception) {
        Jsapi._exceptions[name] = exception;
    };

    for (var name in Exception.classes) {
        registerException(name, Exception.classes[name]);
    }

    Exception.onDefine(registerException);

    return Jsapi;

});
