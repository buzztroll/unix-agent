git "/agent" do
  repository node['dcm']['git_repo']
  revision node['dcm']['git_branch']
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
