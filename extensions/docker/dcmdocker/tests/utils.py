import collections
import os

import dcm.agent.plugins.api.pages as pages


def get_docker_conf_obj():
        docker_url = 'http+unix://var/run/docker.sock'
        if 'DOCKER_HOST' in os.environ:
            docker_url = os.environ['DOCKER_HOST']

        def parse_fake(opt_list):
            pass

        try:
            docker_tls = os.environ['DOCKER_TLS_VERIFY'] == "1"
        except:
            docker_tls = False

        ca_cert_path = None
        client_cert_path = None
        client_key_path = None
        verify = False
        if docker_tls:
            try:
                ca_cert_path = os.path.join(
                    os.environ['DOCKER_CERT_PATH'], 'ca.pem')
                client_cert_path = os.path.join(
                    os.environ['DOCKER_CERT_PATH'], 'cert.pem')
                client_key_path = os.path.join(
                    os.environ['DOCKER_CERT_PATH'], 'key.pem')
                verify = True
            except:
                pass

        FakeConf = collections.namedtuple(
            "FakeConf", ["docker_base_url",
                         "docker_version",
                         "docker_timeout",
                         "docker_tls",
                         "docker_cert_verify",
                         "docker_client_cert_path",
                         "docker_client_key_path",
                         "docker_ca_cert_path",
                         "parse_config_files",
                         "page_monitor"])
        return FakeConf(docker_url, "1.12", 60,
                        docker_tls,
                        verify,
                        client_cert_path,
                        client_key_path,
                        ca_cert_path,
                        parse_fake,
                        pages.PageMonitor())
