require 'digest'
name "ossec"

default_version "2.8.3"

source url: "https://bintray.com/artifact/download/ossec/ossec-hids/ossec-hids-2.8.3.tar.gz",
       md5: "bcf783c2273805e2a4c2112011fafb83"

relative_path "ossec-hids-2.8.3"

build do
  dst_path = "#{install_dir}/ossec"
  build_env = {
    "USER_CLEANINSTALL" => "y",
    "USER_NO_STOP" => "y",
    "USER_ENABLE_EMAIL" => "n",
    "USER_DIR" => dst_path,
    "USER_INSTALL_TYPE" => "local",
    "USER_LANGUAGE" => "en",
    "USER_ENABLE_SYSCHECK" => "y",
    "USER_ENABLE_ROOTCHECK" => "y",
    "USER_ENABLE_ACTIVE_RESPONSE" => "n"
  }

  command './install.sh', env: build_env

  erb source: "ossec.conf.erb",
      dest: "#{dst_path}/etc/ossec.conf",
      mode: 0644,
      vars: { dst_path: dst_path }

  erb source: "ossec.initd.erb",
      dest: "/etc/init.d/dcm-ossec",
      mode: 0755,
      vars: {}
end
