git "/agent" do
  user node['omnibus']['build_user']
  repository "git@github.com:buzztroll/es-ex-pyagent.git"
  revision "buzztroll_master"
  action :sync
  destination "/tmp/agent"
end

bash "build_agent" do
  action :run
  user "root"
  code <<-EOH

    mv /tmp/agent /
    chown -R #{node['omnibus']['build_user']}:#{node['omnibus']['build_user']} /agent
  EOH
end
