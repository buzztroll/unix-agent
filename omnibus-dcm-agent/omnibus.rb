#
# This file is used to configure the dcm-agent project. It contains
# come minimal configuration examples for working with Omnibus. For a full list
# of configurable options, please see the documentation for +omnibus/config.rb+.
#

# Build internally
# ------------------------------
# By default, Omnibus uses system folders (like +/var+ and +/opt+) to build and
# cache compontents. If you would to build everything internally, you can
# uncomment the following options. This will prevent the need for root
# permissions in most cases. You will also need to update the dcm-agent
# project configuration to build at +./local/omnibus/build+ instead of
# +/opt/dcm-agent+
#
# Uncomment this line to change the default base directory to "local"
# -------------------------------------------------------------------
# base_dir './local'
#
# Alternatively you can tune the individual values
# ------------------------------------------------
# cache_dir              './local/omnibus/cache'
# install_path_cache_dir './local/omnibus/cache/install_path'
# source_dir             './local/omnibus/src'
# build_dir              './local/omnibus/build'
# package_dir            './local/omnibus/pkg'
# package_tmp            './local/omnibus/pkg-tmp'

# Enable S3 asset caching
# ------------------------------
#use_s3_caching false
#s3_access_key  'XXXXX'
#s3_secret_key  'XXXXXX'
#s3_bucket      'testvms'

# Customize compiler bits
# ------------------------------
# solaris_compiler 'gcc'
# build_retries 5
