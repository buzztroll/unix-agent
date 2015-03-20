name "sqlite"
version "3.8.8.3"

dependency "libxslt"

version_tag = version.split('.').map { |part| '%02d' % part.to_i }.join[1..-1]
year = "2014"

source :url => "http://www.sqlite.org/#{year}/sqlite-autoconf-#{version_tag}.tar.gz",
       :md5 => "3cba9fa0b00f07eb189fc1b546e66d9d"

relative_path "sqlite-autoconf-#{version_tag}"

env = {
  "LDFLAGS" => "-Wl,-rpath,#{install_dir}/embedded/lib -L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
  "CFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
  "LD_RUN_PATH" => "#{install_dir}/embedded/lib"
}

build do
  command "./configure --prefix=#{install_dir}/embedded --disable-readline", :env => env
  command "make -j #{max_build_jobs}", :env => env
  command "make install"
end