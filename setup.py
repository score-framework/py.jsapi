import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

setup(
    name='score.jsapi',
    version='0.3.7',
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
        'score.jsapi': ['api.js.tpl'],
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
)
