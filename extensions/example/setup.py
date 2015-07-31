from setuptools import setup, find_packages

g_version = "0.1"

setup(name='dcmagentexampleplugins',
      version=g_version,
      description="Example plugins for the DCM Agent",
      author="Dell Software Group",
      author_email="support@enstratius.com",
      url="http://www.enstratius.com/",
      packages=find_packages(),
      install_requires=[],
      include_package_data=True,
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
