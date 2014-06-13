bash "build_agent" do
  action :run
  timeout 36000
  if platform_family?("rhel")
     user "root"
  end
  code <<-EOH
    export PATH=/opt/chef/embedded/bin:$PATH
    cp -r /home/vagrant/dcm-agent /tmp/dcm-agent
    cd /tmp/dcm-agent
    rm -rf bin/*
    rm -rf .bundle
    h=`hostname -s`
    mkdir -p /agent/pkg/$h
    outputdir=/agent/pkg/$h
    bundle install --binstubs
    bundle install
    bin/omnibus build --override=package_dir:$outputdir dcm-agent
  EOH
end
