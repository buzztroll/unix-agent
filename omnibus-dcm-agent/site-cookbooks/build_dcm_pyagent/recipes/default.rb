bash "build_agent" do
  action :run
  timeout 36000
  cwd "/home/vagrant/dcm-agent/"
  code <<-EOH
    bundle install
    h=`hostname`
    mkdir -p pkg/$h
    outputdir=`pwd`/pkg/$h
    bin/omnibus build --override=package_dir:$outputdir dcm-agent
  EOH
end
