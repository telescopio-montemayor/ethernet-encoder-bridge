import os
from setuptools import find_packages, setup

from lx200_encoder_bridge import __version__


with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='lx200-encoder-bridge',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'attrs',
        'aiohttp',
        'requests',
        'pyyaml',
        'munch',
        'python-socketio[asyncio_client]'
    ],
    dependency_links=[
        'git+https://github.com/telescopio-montemayor/python-lx200'
    ],
    license='AGPL-3.0',
    description='Small utility to translate lx200 commands into calls to https://github.com/telescopio-montemayor/ethernet-encoder-servo',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://github.com/telescopio-montemayor/lx200-encoder-bridge',
    author='Adrián Pardini',
    author_email='github@tangopardo.com.ar',
    entry_points={
        'console_scripts': [
            'lx200-bridge=lx200_encoder_bridge:main'
        ]
    },
    classifiers=[
        'Environment :: Web Environment',
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Telecommunications Industry',
        'Intended Audience :: Education',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Communications',
        'Topic :: Education',
        'Topic :: Scientific/Engineering :: Astronomy'
    ],
    keywords='astronomy, telescope, lx200, encoder',
)
