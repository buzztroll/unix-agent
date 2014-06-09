from setuptools import setup, find_packages

Version=0.2

setup(name='dcm-agent',
      version=Version,
      description="Agent for DCM run VMs",
      author="Dell Software Group",
      author_email="enstratius@XXXCHANGETHISdell.com",
      url="http://www.enstratius.com/",
      packages=find_packages(),
       entry_points = {
        'console_scripts': [
            "dcm-agent=dcm.agent.cmd.service:main",
            "dcm-agent-configure=dcm.agent.cmd.configure:main",
        ],

      },
      include_package_data = True,
      install_requires = ["pysqlite == 2.6.3",
                          "pyyaml == 3.10",
                          "ws4py == 0.3.2",
                          "psutil == 1.2.1",
                          "apache-libcloud == 0.14.1",
                          "SQLAlchemy == 0.9.4"],

      package_data = {"dcm.agent": ["dcm/agent/scripts/*",
                                    "dcm/agent/etc/*"],
                      "dcm.agent.tests": ["dcm/agent/tests/etc/*"]},

      classifiers=[
          "Development Status :: 4 - Beta",
          "Environment :: Console",
          "Intended Audience :: System Administrators",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python",
          "Topic :: System :: Clustering",
          "Topic :: System :: Distributed Computing"
          ],
     )
