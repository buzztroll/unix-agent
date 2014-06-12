bash "build_agent" do
  action :run
  timeout 36000
  cwd "/home/vagrant/dcm-agent/"
  code <<-EOH
    export PATH=/opt/chef/embedded/bin:$PATH
    cp -r /home/vagrant/dcm-agent /tmp/dcm-agent
    cd /tmp/dcm-agent
    rm -rf bin/*
    bundle install --binstubs
    rm -rf .bundle
    /opt/chef/embedded/bin/bundle install
    h=`hostname`
    mkdir -p /agent/pkg/$h
    outputdir=/agent/pkg/$h
    bin/omnibus build --override=package_dir:$outputdir dcm-agent
  EOH
end
