import os
from distutils.command.build import build

from django.core import management
from setuptools import find_packages, setup

from pretix_authorize_net import __version__


try:
    with open(os.path.join(os.path.dirname(__file__), 'README.rst'), encoding='utf-8') as f:
        long_description = f.read()
except:
    long_description = ''


class CustomBuild(build):
    def run(self):
        management.call_command('compilemessages', verbosity=1)
        build.run(self)


cmdclass = {
    'build': CustomBuild
}


setup(
    name='pretix-authorize-net',
    version=__version__,
    description='Authorize.net payment provider plugin',
    long_description=long_description,
    url='https://github.com/trysten/pretix-authorize-net',
    author='trysten',
    author_email='trysten@sleepyowl.com',
    license='Apache',

    install_requires=[],
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    cmdclass=cmdclass,
    entry_points="""
[pretix.plugin]
pretix_authorize_net=pretix_authorize_net:PretixPluginMeta
""",
)
