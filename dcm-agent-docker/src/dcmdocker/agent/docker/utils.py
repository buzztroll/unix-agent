from dcm.agent import jobs
import dcm.agent.docker.utils as docker_utils
from docker import errors


import docker
import dcm.agent.exceptions as exceptions


class DCMDockerException(exceptions.AgentPluginOperationException):
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


def get_docker_container(docker_conn, container_name):
    return docker_conn.containers(trunc=True, latest=False, since=None,
                                  before=None, limit=-1)


class DockerJob(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DockerJob, self).__init__(
            conf, job_id, items_map, name, arguments)
        try:
            self.docker_conn = docker_utils.get_docker_connection(self.conf)
        except errors.DockerException as docker_ex:
            raise DCMDockerConnectionException(conf.docker_base_url,
                                               conf.docker_version,
                                               docker_ex.message)

