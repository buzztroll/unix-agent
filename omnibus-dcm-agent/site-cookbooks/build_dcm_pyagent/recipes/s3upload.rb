bash "build_agent" do
  action :run
  timeout 36000
  if platform_family?("rhel")
     user "root"
  end
  code <<-EOH

    h=`hostname -s`
    outputdir=/agent/pkg/$h
    pkg_name=`/tmp/distro.sh`

  EOH
end
