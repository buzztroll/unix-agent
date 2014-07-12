bash "build_agent" do
  action :run
  timeout 360000

  code <<-EOH

    h=`hostname -s`
    outputdir=/agent/pkg/$h
    pkg_name=`/tmp/distro.sh | awk '{ print $1 }'`
    ext_name=`/tmp/distro.sh | awk '{ print $2 }'`

    local_pkg=`ls -tC1 $outputdir/*.$ext_name 2> /dev/null | head -n 1`

    s3cmd put $local_pkg s3://#{node['dcm']['release_bucket']}/$pkg_name.$ext_name
  EOH
end
