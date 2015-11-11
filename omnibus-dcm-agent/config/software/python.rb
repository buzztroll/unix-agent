#
# Copyright:: Copyright (c) 2013-2014 Chef Software, Inc.
# License:: Apache License, Version 2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

name "python"
default_version "3.5.0"

dependency "readline"
dependency "sqlite"
dependency "gdbm"
dependency "ncurses"
dependency "zlib"
dependency "openssl"
dependency "bzip2"

source :url => "http://python.org/ftp/python/#{version}/Python-#{version}.tgz",
       :md5 => 'a56c0c0b45d75a0ec9c6dee933c41c36'

relative_path "Python-#{version}"

LIB_PATH = %W(#{install_dir}/embedded/lib #{install_dir}/embedded/lib64 #{install_dir}/embedded/libexec #{install_dir}/lib #{install_dir}/lib64 #{install_dir}/libexec)

env = {
  "CFLAGS" => "-I#{install_dir}/embedded/include -O3 -g -pipe",
  "LDFLAGS" => "-Wl,-rpath,#{LIB_PATH.join(',-rpath,')} -L#{LIB_PATH.join(' -L')} -I#{install_dir}/embedded/include",
  "CPPFLAGS" => "-I#{install_dir}/embedded/include",
}

build do
  command ["./configure",
           "--prefix=#{install_dir}/embedded",
           "--enable-shared",
           "--with-dbmliborder=gdbm"].join(" "), :env => env
  command "make", :env => env
  command "make install", :env => env

  # There exists no configure flag to tell Python to not compile readline support :(
  block do
    FileUtils.rm_f(Dir.glob("#{install_dir}/lib/python3.4/lib-dynload/dbm.*"))
  end
end