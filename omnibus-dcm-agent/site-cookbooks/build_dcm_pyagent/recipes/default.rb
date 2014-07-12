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
  user node['omnibus']['build_user']
  group node['omnibus']['build_user']
  code <<-EOH
    export PATH=/opt/chef/embedded/bin:$PATH
    cp -r /agent/omnibus-dcm-agent /tmp/dcm-agent
    cd /tmp/dcm-agent
    rm -rf /tmp/dcm-agent/bin/*
    rm -rf /tmp/dcm-agent/.bundle
    h=`hostname -s`
    mkdir -p /agent/pkg/$h
    outputdir=/agent/pkg/$h
    bundle install --binstubs
    bundle install
    bin/omnibus build --override=package_dir:$outputdir dcm-agent
  EOH
end
