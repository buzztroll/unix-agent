name "ec2-ami-tools"
default_version "1.5.7"

dependency "rsync"
dependency "ruby"
dependency "openssl"

source url: "http://s3.amazonaws.com/ec2-downloads/ec2-ami-tools-#{version}.zip",
       md5: "bbf565e0cea97e1b79d75d85778e0fc0"

relative_path "ec2-ami-tools-#{version}"

build do
  command "cp -r . #{install_dir}/ec2-ami-tools"
end
