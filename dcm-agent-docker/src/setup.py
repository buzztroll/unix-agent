from setuptools import setup, find_packages


setup(name='dcm-agent-docker',
      version="0.1",
      description="Docker extensions for dcm agent",
      author="Dell Software Group",
      author_email="support@enstratius.com",
      url="http://www.enstratius.com/",
      packages=find_packages(),

      include_package_data=True,
      install_requires=["docker-py == 0.5.0",
                        "dcm-agent == 0.9.3"],

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
