import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

setup(
    name='score.jsapi',
    version='0.1',
    description='Javascript API generator of The SCORE Framework',
    long_description=README,
    author='strg.at',
    author_email='score@strg.at',
    url='http://score-framework.org',
    keywords='score framework web javascript rpc api',
    packages=['score.jsapi'],
    install_requires=[
        'score.init',
        'score.ctx',
        'score.js',
    ],
)
