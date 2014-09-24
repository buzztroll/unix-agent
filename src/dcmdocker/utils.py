from dcm.agent import jobs, config
from docker import errors
import docker


class DCMDockerException(Exception):
    pass


class DCMDockerConnectionException(DCMDockerException):
    message = "Failed to connect to docker at %(url)s version %(version)s" \
              ": %(docker_msg)s"
    def __init__(self, url, version, docker_msg):
        super(DCMDockerConnectionException, self.message % locals())


def get_docker_connection(conf):
    c = docker.Client(conf.docker_base_url,
                      conf.docker_version,
                      conf.docker_timeout)
    return c


class DockerJob(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DockerJob, self).__init__(
            conf, job_id, items_map, name, arguments)
        parse_docker_options(conf)
        try:
            self.docker_conn = get_docker_connection(self.conf)
        except errors.DockerException as docker_ex:
            raise 
#DCMDockerConnectionException(conf.docker_base_url,
 #                                              conf.docker_version,
  #                                             docker_ex.message)


def parse_docker_options(conf):
    if getattr(conf, "docker_host", None) is None:
        option_list = [
            config.ConfigOpt("docker", "host", str,
                             default="http+unix://var/run/docker.sock",
                             options=None,
                             help_msg="The docker hostname."),
            config.ConfigOpt("docker", "version", str, default='1.12',
                             options=None,
                             help_msg="The docker API version."),
            config.ConfigOpt("docker", "timeout", int, default=30, options=None,
                             help_msg="The docker timeout."),
        ]
        conf.parse_config_files(option_list)

