name "virtualenv"
default_version "13.0.0"

dependency "python"
dependency "pip"

build do
  command "#{install_dir}/embedded/bin/pip install -I --build #{project_dir} --install-option=\"--install-scripts=#{install_dir}/embedded/bin\" #{name}==#{version}"
end