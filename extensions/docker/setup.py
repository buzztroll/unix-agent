from setuptools import setup, find_packages

g_version = "0.2"

setup(name='dcmdocker',
      version=g_version,
      description="Docker extensions for the dcm-agent",
      author="Dell Software Group",
      author_email="support@enstratius.com",
      url="http://www.enstratius.com/",
      packages=find_packages(),
      install_requires=["docker-py == 1.3.1"],
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
