import os
import setuptools


Version = "0.1"

basepath = os.path.dirname(__file__)

install_requires = [
        "pyyaml == 3.10",
        ]

tests_require = install_requires + [
        ]

setuptools.setup(name='enstratiusagent',
      version=Version,
      description='Agent for Enstraius run VMs.',
      author='Dell',
      author_email='enstratius@XXXCHANGETHISdell.com',
      url='http://www.enstratius.com/',
      packages=[ 'dcm', 'dcm.agent',],

      include_package_data = True,
      package_data = {},
      long_description="""
      """,
      license="Apache2",
      install_requires = install_requires,
      tests_require=tests_require,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Topic :: System :: Clustering',
          'Topic :: System :: Distributed Computing',
          ],
     )
