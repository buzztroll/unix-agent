import docker
import docker.errors as errors
import docker.tls
import dcm.agent.config as config

import dcm.agent.plugins.api.base as plugin_base


class DCMDockerException(Exception):
    pass


class DCMDockerConnectionException(DCMDockerException):
    message = "Failed to connect to docker at %(url)s version %(version)s" \
              ": %(docker_msg)s"
    def __init__(self, url, version, docker_msg):
        super(DCMDockerConnectionException, self.message % locals())


def get_docker_connection(conf):
    tls = False
    if conf.docker_tls:
        client_cert = None
        if conf.docker_client_cert_path and conf.docker_client_key_path:
            client_cert=(conf.docker_client_cert_path,
                         conf.docker_client_key_path)

        ca_cert = None
        if conf.docker_ca_cert_path:
           ca_cert = conf.docker_ca_cert_path

        tls = docker.tls.TLSConfig(verify=conf.docker_cert_verify,
                                   client_cert=client_cert,
                                   ca_cert=ca_cert)

    c = docker.Client(base_url=conf.docker_base_url,
                      version=conf.docker_version,
                      timeout=conf.docker_timeout,
                      tls=tls)
    return c


class DockerJob(plugin_base.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DockerJob, self).__init__(
            conf, job_id, items_map, name, arguments)
        parse_docker_options(conf)
        try:
            self.docker_conn = get_docker_connection(self.conf)
        except errors.DockerException as docker_ex:
            raise 


def parse_docker_options(conf):
    if getattr(conf, "docker_base_url", None) is None:
        option_list = [
            config.ConfigOpt("docker", "base_url", str,
                             default="http+unix://var/run/docker.sock",
                             options=None,
                             help_msg="The docker hostname."),
            config.ConfigOpt("docker", "version", str, default='1.12',
                             options=None,
                             help_msg="The docker API version."),
            config.ConfigOpt("docker", "tls", bool, default=False,
                             options=None,
                             help_msg="Use TLS or not."),
            config.ConfigOpt("docker", "cert_verify", bool, default=False,
                             options=None,
                             help_msg="Validate the cert or not."),
            config.ConfigOpt("docker", "ca_cert", str, default=False,
                             options=None,
                             help_msg="Path to the ca certificate."),
            config.ConfigOpt("docker", "client_cert_path", str, default=False,
                             options=None,
                             help_msg="Path to the client certificate."),
            config.ConfigOpt("docker", "client_key_path", str, default=False,
                             options=None,
                             help_msg="Path to the client key."),
            config.ConfigOpt("docker", "timeout", int, default=30, options=None,
                             help_msg="The docker timeout."),
        ]
        conf.parse_config_files(option_list)
