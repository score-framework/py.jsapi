/**
 * Copyright © 2015-2017 STRG.AT GmbH, Vienna, Austria
 * Copyright © 2018 Necdet Can Ateşman, Vienna, Austria
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
/* eslint-disable */
/* tslint:disable */

import { Queue } from './queue';

export class Jsapi {

    constructor(endpoints, exceptions) {
        this._ops = {};
        this._exceptions = {};
        this._queue = new Queue();
        endpoints.forEach(endpoint => {
            for (let i = 0; i < endpoint.operations.length; i++) {
                const operation = endpoint.operations[i]
                this[operation.name] = function() {
                    const args = Array.prototype.slice.call(arguments);
                    const promise = this._call(operation.name, args);
                    this._flush();
                    return promise;
                };
                this._ops[operation.name] = {
                    name: operation.name,
                    version: operation.version,
                    minargs: operation.minargs,
                    maxargs: operation.maxargs,
                    argnames: operation.argnames,
                    endpoint: endpoint,
                };
            }
        });
        exceptions.forEach(exception => {
            this._exceptions[exception.prototype.name] = exception;
        });
    }

    _call(func, version, args) {
        if (!(func in this._ops)) {
            throw new Error("Undefined operation '" + func + "'");
        }
        const op = this._ops[func];
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
        const request = [func, version];
        for (let i = 0; i < args.length; i++) {
            if (typeof args[i] === 'undefined') {
                throw new Error("Error in invocation of operation " + func + ": Argument '" + op.argnames[i] + "' is undefined");
            }
            request.push(args[i]);
        }
        return this._queue.queue(request, op.endpoint);
    }

    _flush() {
        return this._queue.flush();
    }

};

export default Jsapi;
