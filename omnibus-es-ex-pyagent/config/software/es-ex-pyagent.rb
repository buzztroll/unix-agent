name "es-ex-pyagent"
version "3.10"

dependency "python"
dependency "pip"

build do
  build_env = {
    "PATH" => "/#{install_dir}/embedded/bin:#{ENV['PATH']}",
    "LDFLAGS" => "-L/#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
    "LD_RUN_PATH" => "#{install_dir}/embedded/lib",
    "CFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include/",
  }
  command "#{install_dir}/embedded/bin/pip install -I --build #{project_dir} -r /agent/src/requirements.txt", :env => build_env
  command "#{install_dir}/embedded/bin/pip install -I --build #{project_dir} -r /agent/src/test-requirements.txt", :env => build_env
  command "cd /agent/src; #{install_dir}/embedded/bin/python setup.py install", :env => build_env
  command "#{install_dir}/embedded/bin/dcm-agent-configure  -I -v -p /tmp", :env => build_env
end
