name "dcm-agent"
default_version "0.9.10"

dependency "python"
dependency "pip"

build do
  source_path = "/agent"
  ve_version = #{build_version}
  ve_path = "#{install_dir}/embedded/agentve"
  build_env = {
    "PATH" => "/#{install_dir}/embedded/bin:#{ENV['PATH']}",
    "LDFLAGS" => "-L/#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
    "LD_RUN_PATH" => "#{install_dir}/embedded/lib",
    "CFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include/",
  }
  command "#{install_dir}/bin/virtualenv --no-site-packages #{ve_path}", :env => build_env
  command ". #{ve_path}/bin/activate; pip install -I --build #{project_dir} -r #{source_path}/src/requirements.txt", :env => build_env
  command ". #{ve_path}/bin/activate; pip install -I --build #{project_dir} -r #{source_path}/src/test-requirements.txt", :env => build_env
  command ". #{ve_path}/bin/activate; cd #{source_path}/src; #{ve_path}/bin/python setup.py install", :env => build_env
  command ". #{ve_path}/bin/activate; pip install -I --build #{project_dir} -r #{source_path}/extensions/docker/requirements.txt", :env => build_env
  command ". #{ve_path}/bin/activate; pip install -I --build #{project_dir} -r #{source_path}/extensions/docker/test-requirements.txt", :env => build_env
  command ". #{ve_path}/bin/activate; cd #{source_path}/extensions/docker; #{ve_path}/bin/python setup.py install", :env => build_env
  command "ln -s #{ve_path}/bin/dcm-agent-configure /opt/dcm-agent/embedded/bin/dcm-agent-configure", :env => build_env
end
