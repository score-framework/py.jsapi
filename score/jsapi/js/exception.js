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
/* eslint-disable */
/* tslint:disable */

// Universal Module Loader
// https://github.com/umdjs/umd
// https://github.com/umdjs/umd/blob/v1.0.0/returnExports.js
(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(factory);
    } else if (typeof module === 'object' && module.exports) {
        // Node. Does not work with strict CommonJS, but
        // only CommonJS-like environments that support module.exports,
        // like Node.
        module.exports = factory();
    } else {
        // Browser globals (root is window)
        root.score = root.score || {};
        root.score.jsapi = root.score.jsapi || {};
        root.score.jsapi.Exception = factory();
    }
})(this, function() {

    var Exception = function(message) {
        Error.call(this);
        this.message = message || '';
        this.stack = (new Error()).stack;
    };

    Exception.classes = {};

    Exception.define = function(name, parentName) {
        var NewException = function(message) {
            if (parentName) {
                Exception.classes[parentName].call(this, message);
            } else {
                Exception.call(this, message);
            }
        };
        NewException.prototype = Object.create(Exception.prototype);
        NewException.prototype.name = name;
        Exception.classes[name] = NewException;
        for (var i = 0; i < Exception.defineCallbacks.length; i++)  {
            Exception.defineCallbacks[i](name, NewException);
        }
        return NewException;
    };

    Exception.defineCallbacks = [];

    Exception.onDefine = function(callback) {
        Exception.defineCallbacks.push(callback);
    };

    Exception.prototype = Object.create(Error.prototype);

    Exception.prototype.name = 'JsapiException';

    return Exception;

});
