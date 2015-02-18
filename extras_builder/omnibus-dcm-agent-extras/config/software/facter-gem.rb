name "facter-gem"
default_version "1.7.1"

dependency "ruby"
dependency "rubygems"

build do
  command "#{install_dir}/embedded/bin/gem install facter -n #{install_dir}/bin --no-rdoc --no-ri -v 1.7.1"
end
