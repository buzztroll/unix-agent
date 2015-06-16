name "ossec"
default_version "2.8.2"

# until 2.9 is released we can use the git version
source url: "http://www.ossec.net/files/ossec-hids-2.8.2.tar.gz",
       md5: "3036d5babc96216135759338466e1f79"

relative_path "ossec-hids"

build do
  source_path = "/agent"
  dst_path = "/opt/ossec"
  build_env = {
    "USER_NO_STOP" => "y",
    "USER_ENABLE_EMAIL" => "n",
    "USER_DIR" => dst_path,
    "USER_INSTALL_TYPE" => "local",
    "USER_LANGUAGE" => "en",
    "USER_ENABLE_SYSCHECK" => "y",
    "USER_ENABLE_ROOTCHECK" => "y",
    "USER_ENABLE_ACTIVE_RESPONSE" => "n"
  }
  command "#{source_path}/install.sh", :env => build_env

  erb source: "ossec.conf.erb",
      dest: "#{dst_path}/etc/ossec.conf",
      mode: 0644
end