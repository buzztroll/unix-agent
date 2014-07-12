template "/tmp/distro.sh" do
  source "distro.sh.erb"
  variables(
  )
  owner node['omnibus']['build_user']
  group node['omnibus']['build_user']
  mode 0755
end

bash "build_agent" do
  action :run
  timeout 36000
  cwd "/tmp"
  user "root"
  group "root"
  code <<-EOH
    set -e
    export PATH=/opt/chef/embedded/bin:$PATH
    cp -r /agent/omnibus-dcm-agent /tmp/dcm-agent
    cd /tmp/dcm-agent
    rm -rf /tmp/dcm-agent/bin/*
    rm -rf /tmp/dcm-agent/.bundle
    h=`hostname -s`
    mkdir -p /agent/pkg/$h
    outputdir=/agent/pkg/$h
    /opt/chef/embedded/bin/bundle install --binstubs
    /opt/chef/embedded/bin/bundle install
    /tmp/dcm-agent/bin/omnibus build --override=package_dir:$outputdir dcm-agent
  EOH
end
