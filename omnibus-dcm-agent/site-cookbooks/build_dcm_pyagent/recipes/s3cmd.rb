
package "python"
package "python-setuptools"
#package "python-distutils-extra"
package "python-dateutil"


remote_file "#{Chef::Config[:file_cache_path]}/master.tar.gz" do
  source node['s3cmd']['url']
  mode "0644"
end

bash "install-s3cmd" do
  user "root"
  cwd Chef::Config[:file_cache_path]
  code <<-EOH
  tar xzvf master.tar.gz
  cd s3cmd-master
  python setup.py install
  EOH
end

template "/root/.s3cfg" do
  source "s3cfg.erb"
  variables(
    :access_key =>  node['s3cmd']['access_key'],
    :secret_key =>  node['s3cmd']['secret_key'],
    :gpg_passphrase =>  node['s3cmd']['gpg_passphrase'],
    :bucket_location =>  node['s3cmd']['bucket_location'],
    :https =>  node['s3cmd']['https'],
    :encrypt =>  node['s3cmd']['encrypt']
  )
  owner "root"
  group "root"
  mode 0600
end
