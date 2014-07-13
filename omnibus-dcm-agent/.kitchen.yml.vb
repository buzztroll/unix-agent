driver:
  name: vagrant
  customize:
    cpus: 2
    memory: 2048

driver_config:
  require_chef_omnibus: latest

provisioner:
  name: chef_solo
  require_chef_omnibus: latest

platforms:
  - name: ubuntu-10.04
    run_list: apt::default
  - name: ubuntu-10.04-i386
    run_list: apt::default
  - name: ubuntu-12.04
    run_list: apt::default
  - name: ubuntu-12.04-i386
    run_list: apt::default
  - name: ubuntu-13.10
    run_list: apt::default
  - name: ubuntu-13.10-i386
    run_list:
    - apt::default
    - recipe[git::source]
  - name: centos-5.10-i386
    run_list:
      - yum-epel::default
      - recipe[git::source]
  - name: centos-5.10
    run_list:
      - yum-epel::default
      - recipe[git::source]
  - name: debian-7.2.0
    run_list: apt::default
    driver_config:
        box: agent-debian-720
  - name: debian-7.2.0-i386
    run_list: apt::default
    driver_config:
        box: agent-debian-720-i386
  - name: debian-6.0.8
    driver_config:
      require_chef_omnibus: true
      box: agent-debian-608
    run_list:
    - recipe[apt]
  - name: debian-6.0.8-i386
    run_list: apt::default
    driver_config:
        box: agent-debian-608-i386

suites:
  - name: default
    run_list:
      - recipe[build-essential]
      - omnibus::default
      - "recipe[build_dcm_pyagent::s3cmd]"
      - "recipe[build_dcm_pyagent::gitcheckout]"
      - "recipe[build_dcm_pyagent::default]"
      - "recipe[build_dcm_pyagent::s3upload]"

#    attributes:
#      omnibus:
#        build_user:  vagrant
#        build_dir:   /home/vagrant/dcm-agent
#        install_dir: /opt/dcm-agent
