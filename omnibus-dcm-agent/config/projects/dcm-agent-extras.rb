#
# Copyright 2015 YOUR NAME
#
# All Rights Reserved.
#

name "dcm-agent-extras"
maintainer "DCM"
homepage "https://enstratius.com"

install_dir "/opt/#{name}"

build_version "0.2.1" # SEARCH_TOKEN do not delete
#build_version Omnibus::BuildVersion.semver
build_iteration 1

# Creates required build directories
dependency "preparation"

# dcm-agent-extras dependencies/components
dependency "puppet-gem"

# Version manifest file
dependency "version-manifest"

exclude "**/.git"
exclude "**/bundler/git"
