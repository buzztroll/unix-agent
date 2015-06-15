name "ossec"
default_version "2.9.0"

# until 2.9 is released we can use the git version
source git: "https://github.com/ossec/ossec-hids.git"

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
      mode: 0644,
      vars: {}
end
