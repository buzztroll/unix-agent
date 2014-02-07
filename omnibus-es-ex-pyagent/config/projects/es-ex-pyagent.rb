
name "es-ex-pyagent"
maintainer "Dell Software Group"
homepage "http://www.enstratius.com/"

replaces        "es-ex-pyagent"
install_path    "/opt/es-ex-pyagent"
build_version   Omnibus::BuildVersion.new.semver
build_iteration 1

# creates required build directories
dependency "preparation"

# es-ex-pyagent dependencies/components
dependency "python"
dependency "pip"
dependency "pyyaml"
dependency "es-ex-pyagent"

# version manifest file
dependency "version-manifest"

exclude "\.git*"
exclude "bundler\/git"
