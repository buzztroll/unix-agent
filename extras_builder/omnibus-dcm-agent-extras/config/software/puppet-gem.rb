name "puppet-gem"
default_version "3.7.4"

dependency "ruby"
dependency "rubygems"
dependency "facter-gem"

build do
  command "#{install_dir}/embedded/bin/gem install hiera -n #{install_dir}/embedded/bin --no-rdoc --no-ri -v '~> 1.0'"
  command "#{install_dir}/embedded/bin/gem install puppet -n #{install_dir}/bin --no-rdoc --no-ri -v 3.7.4"
end
