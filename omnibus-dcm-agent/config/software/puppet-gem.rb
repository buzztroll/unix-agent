name "puppet-gem"
default_version "3.7.4"

dependency "ruby"
dependency "rubygems"
dependency "facter-gem"

build do
  command "#{install_dir}/embedded/bin/gem install hiera -n #{install_dir}/embedded/bin --no-rdoc --no-ri -v '~> 1.0'"
  command "#{install_dir}/embedded/bin/gem install puppet -n #{install_dir}/bin --no-rdoc --no-ri -v 3.7.4"

  mkdir "#{install_dir}/puppetconf"
  erb source: "puppet.conf.erb",
      dest: "#{install_dir}/puppetconf/puppet.conf.template",
      mode: 0644,
      vars: { install_dir: install_dir }

end