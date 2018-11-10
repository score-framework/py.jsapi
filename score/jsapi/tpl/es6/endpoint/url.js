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

import Endpoint from './base';

export class UrlEndpoint extends Endpoint {

    constructor(name, operations, url, method) {
        super(name, operations);
        this.url = url;
        this.method = method || 'POST';
    }

    send(requests) {
        if (this.method == 'GET') {
            return this.sendEach(requests);
        } else {
            return this.sendBulk(requests);
        }
    }

    sendBulk(requests) {
        return new Promise((resolve, reject) => {
            const request = new XMLHttpRequest();
            request.onreadystatechange = function() {
                if (request.readyState !== 4) {
                    return;
                }
                if (request.status === 200) {
                    resolve(JSON.parse(request.responseText));
                }
                const msg = 'Received unexpected status code ' +
                    request.status + ': ' + request.statusText;
                reject(new Error(msg));
                return;
            };
            if (this.method === 'GET') {
                const data = [];
                for (let i = 0; i < requests.length; i++) {
                    data.push('requests[]=' + encodeURIComponent(JSON.stringify(requests[i])));
                }
                request.open('GET', this.url + '?' + data.join('&'));
                request.send();
            } else {
                request.open(this.method, this.url);
                request.setRequestHeader("Content-Type", "application/json");
                request.send(JSON.stringify(requests));
            }
        });
    };

    sendEach(requests) {
        return Promise.all(requests.map((request) => {
            return this.sendBulk([request]).then((result) => {
                return result[0];
            });
        }));
    };

}

export default UrlEndpoint;
