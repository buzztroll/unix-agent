template "/tmp/distro.sh" do
  source "distro.sh.erb"
  variables(
  )
  owner node['omnibus']['build_user']
  group node['omnibus']['build_user']
  mode 0755
end


bash "copy_agent_code" do
  action :run
  timeout 36000
  cwd "/tmp"
  user "root"
  group "root"
  code <<-EOH
    cp -r /agent/omnibus-dcm-agent /tmp/dcm-agent
    rm -rf /tmp/dcm-agent/bin/*
    rm -rf /tmp/dcm-agent/.bundle
  EOH
end

template "/tmp/dcm-agent/omnibus.rb" do
  source "omnibus.rb.erb"
  variables(
    :access_key =>  node['s3cmd']['access_key'],
    :secret_key =>  node['s3cmd']['secret_key'],
    :cache_bucket => node['dcm']['cache_bucket']
  )
  owner "root"
  group "root"
  mode 0600
end

bash "build_agent" do
  action :run
  timeout 36000
  cwd "/tmp/dcm-agent"
  user "root"
  group "root"
  code <<-EOH
    set -e
    export PATH=/opt/chef/embedded/bin:$PATH
    cd /tmp/dcm-agent
    h=`hostname -s`
    mkdir -p /agent/pkg/$h
    outputdir=/agent/pkg/$h
    /opt/chef/embedded/bin/bundle install --binstubs
    /opt/chef/embedded/bin/bundle install
    /tmp/dcm-agent/bin/omnibus build --override=package_dir:$outputdir dcm-agent
  EOH
end
