
name "dcm-agent"
maintainer "Dell Software Group"
homepage "http://www.enstratius.com/"

replaces        "dcm-agent"
install_path    "/opt/dcm-agent"
build_version   Omnibus::BuildVersion.new.semver
build_iteration 1

# creates required build directories
dependency "preparation"

# dcm-agent dependencies/components
dependency "python"
dependency "pip"
dependency "pyyaml"
dependency "dcm-agent"

# version manifest file
dependency "version-manifest"

exclude "\.git*"
exclude "bundler\/git"
