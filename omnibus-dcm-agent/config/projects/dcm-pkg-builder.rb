name "dcm-pkg-builder"
maintainer "Dell Software Group"
homepage "http://www.enstratius.com/"

install_dir     "/opt/dcm-pkg-builder"
build_version "0.1.0" # SEARCH_TOKEN do not delete
build_iteration 1

# creates required build directories
dependency "preparation"

# dcm-agent dependencies/components
dependency "zlib"
dependency "sqlite"
dependency "python"
dependency "pip"
dependency "virtualenv"
dependency "pyyaml"
dependency "ruby"
dependency "rubygems"

# version manifest file
dependency "version-manifest"

exclude "\.git*"
exclude "bundler\/git"
