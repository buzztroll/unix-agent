import os
import subprocess
from setuptools import setup, find_packages
import sys

Version = "0.9.1"


def get_diff_tag():
    try:
        basedir = os.path.dirname(os.path.expanduser(sys.argv[0]))
        if not basedir.strip():
            basedir = None
        p = subprocess.Popen("git rev-parse HEAD",
                             cwd=basedir,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdoutdata, stderrdata) = p.communicate()
        rc = p.wait()
        if rc != 0:
            return ""
        version = "-" + stdoutdata.strip()

        p = subprocess.Popen("git diff",
                             cwd=basedir,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdoutdata, stderrdata) = p.communicate()
        rc = p.wait()
        if rc == 0 and stdoutdata:
            version = version + "-diff"
        return version
    except Exception:
        return ""


setup(name='dcm-agent',
      version=Version+get_diff_tag(),
      description="Agent for DCM run VMs",
      author="Dell Software Group",
      author_email="support@enstratius.com",
      url="http://www.enstratius.com/",
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              "dcm-agent=dcm.agent.cmd.service:main",
              "dcm-agent-configure=dcm.agent.cmd.configure:main",
              "dcm-agent-gen-docs=dcm.agent.cmd.gen_docs:main",
          ],
      },
      include_package_data=True,
      install_requires=["pysqlite == 2.6.3",
                        "pyyaml == 3.10",
                        "ws4py == 0.3.2",
                        "psutil == 1.2.1",
                        "apache-libcloud == 0.14.1",
                        "SQLAlchemy == 0.9.4",
                        "clint == 0.3.7"],

      package_data={"dcm.agent": ["dcm/agent/scripts/*",
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
      ]
      )
