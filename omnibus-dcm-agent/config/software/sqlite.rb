name "sqlite"
version "3.8.8.3"

dependency "libxslt"

#version_tag = version.split('.').map { |part| '%02d' % part.to_i }.join[1..-1]
version_tag = "3080803"
year = "2015"

source :url => "http://www.sqlite.org/#{year}/sqlite-autoconf-#{version_tag}.tar.gz",
       :md5 => "51272e875879ee893e51070b07c33888"

relative_path "sqlite-autoconf-#{version_tag}"

env = {
  "LDFLAGS" => "-Wl,-rpath,#{install_dir}/embedded/lib -L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
  "CFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
  "LD_RUN_PATH" => "#{install_dir}/embedded/lib"
}

build do
  command "./configure --prefix=#{install_dir}/embedded --disable-readline", :env => env
  command "make", :env => env
  command "make install"
end
