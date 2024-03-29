# Copyright © 2015-2018 STRG.AT GmbH, Vienna, Austria
# Copyright © 2018-2020 Necdet Can Ateşman <can@atesman.at>, Vienna, Austria
#
# This file is part of the The SCORE Framework.
#
# The SCORE Framework and all its parts are free software: you can redistribute
# them and/or modify them under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation which is in
# the file named COPYING.LESSER.txt.
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
# the discretion of STRG.AT GmbH also the competent court, in whose district
# the Licensee has his registered seat, an establishment or assets.

import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

setup(
    name='score.jsapi',
    version='0.4.20',
    description='Javascript API generator of The SCORE Framework',
    long_description=README,
    author='strg.at',
    author_email='score@strg.at',
    url='http://score-framework.org',
    keywords='score framework web javascript rpc api',
    packages=['score', 'score.jsapi'],
    namespace_packages=['score'],
    package_dir={
        'score.jsapi': 'score/jsapi',
    },
    package_data={
        'score.jsapi': [
            'tpl/umd/unified.js',
            'tpl/umd/exception.js',
            'tpl/umd/endpoint.js',
            'tpl/umd/queue.js',
            'tpl/umd/endpoint/url.js',
            'tpl/umd/excformat.js',
            'tpl/es6/unified.js',
            'tpl/es6/exception.js',
            'tpl/es6/queue.js',
            'tpl/es6/endpoint/index.js',
            'tpl/es6/endpoint/url.js',
            'tpl/es6/endpoint/base.js',
            'tpl/es6/excformat.js',
        ]
    },
    zip_safe=False,
    license='LGPL',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Pyramid',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General '
            'Public License v3 or later (LGPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: JavaScript',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    install_requires=[
        'score.init >= 0.3',
        'score.ctx >= 0.3',
    ],
    entry_points={
        'score.cli': [
            'jsapi = score.jsapi.cli:main',
        ],
    },
)
