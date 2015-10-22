require 'digest'
name "ossec"
default_version "2.8.2"


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

  %x[wget -O /tmp/ossec-hids-2.8.2.tar.gz -U ossec http://www.ossec.net/files/ossec-hids-2.8.2.tar.gz]
  %x[wget -O /tmp/ossec.txt -U ossec http://www.ossec.net/files/ossec-hids-2.8.2-checksum.txt]

  checksum_file = Digest::MD5.hexdigest(File.read('/tmp/ossec-hids-2.8.2.tar.gz'))
  lines = File.readlines('/tmp/ossec.txt')
  line = lines.select { |lines| lines[/#{"MD5"}/i] }
  check_line = line[0].split(" ")
  checksum_check = check_line[1]

  if checksum_file != checksum_check then
    puts "Checksum did not match...exiting."
    exit 1
  end

  %x[tar -zxvf /tmp/ossec-hids-2.8.2.tar.gz -C /tmp]
  command '/tmp/ossec-hids-2.8.2/install.sh', env: build_env

  erb source: "ossec.conf.erb",
      dest: "#{dst_path}/etc/ossec.conf",
      mode: 0644,
      vars: { dst_path: dst_path }
end
