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

import Endpoint from './endpoint';
import excformat from './excformat';
import Exception from './exception';

function defer() {
    let resolve, reject;
    const promise = new Promise(function(res, rej) {
        resolve = res;
        reject = rej;
    });
    return {
        promise: promise,
        resolve: resolve,
        reject: reject,
    };
};

export class Queue {

    constructor() {
        this.queuedRequests = [];
        this.flushDeferred = null;
        this._flush = this._flush.bind(this);
    }

    queue(data, endpoint) {
        const request = defer();
        request.data = data;
        request.endpoint = endpoint;
        this.queuedRequests.push(request);
        return request.promise;
    };

    flush() {
        // return existing flush promise, if there is one
        if (this.flushDeferred) {
            return this.flushDeferred.promise;
        }
        // do we have any requests to flush?
        if (!this.queuedRequests.length) {
            return Promise.resolve();
        }
        this.flushDeferred = defer();
        // wait until current code block is finished before sending the
        // request to the server, we might receive some more requests.
        window.setTimeout(this._flush);
        return this.flushDeferred.promise;
    };

    _flush() {
        // map transport name to its requests
        const requests = {};
        for (let i = 0; i < this.queuedRequests.length; i++) {
            const r = this.queuedRequests[i];
            if (!(r.endpoint.name in requests)) {
                requests[r.endpoint.name] = [];
            }
            requests[r.endpoint.name].push(r);
        }
        // send each endpoint's requests
        const send = function(endpoint, requests) {
            const payload = [];
            for (let i = 0; i < requests.length; i++) {
                payload.push(requests[i].data);
            }
            return endpoint.send(payload).then(function(responses) {
                for (let i = 0; i < responses.length; i++) {
                    const response = responses[i],
                        success = response.success;
                    let result = response.result;
                    if (success) {
                        requests[i].resolve(result);
                    } else {
                        if (result && result.trace) {
                            const desc = requests[i].data[0];
                            if (requests[i].data[1]) {
                                desc += '/' + requests[i].data[1];
                            }
                            const args = ['Error in jsapi call', desc, '('];
                            for (let j = 2; j < requests[i].data.length; j++) {
                                if (j != 2) {
                                    args.push(',');
                                }
                                args.push(requests[i].data[j]);
                            }
                            args.push(')');
                            args.push("\n" + excformat(result));
                            console.error.apply(console, args);  // eslint-disable-line no-console
                        }
                        if (result) {
                            if (result.type in Exception.classes) {
                                result = new Exception.classes[result.type](result.message);
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
                for (let i = 0; i < requests.length; i++) {
                    requests[i].reject(error);
                }
            });
        };
        const promises = [];
        for (const endpointName in requests) {
            promises.push(send(Endpoint.get(endpointName), requests[endpointName]));
        }
        const promise = Promise.all(promises);
        // store instance variables and reset object state
        const flushDeferred = this.flushDeferred;
        this.queuedRequests = [];
        this.flushDeferred = null;
        // resolve flushDeferred once the flush is complete
        promise.then(function() {
            flushDeferred.resolve();
        });
        return promise;
    };

};

export default Queue;
