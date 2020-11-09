import logging
import os
from typing import List

import oyaml
from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.config import load_incluster_config, load_kube_config
from requests.packages.urllib3 import disable_warnings

from . import PersistencePlugin

disable_warnings()

logging.getLogger("kubernetes.client.rest").setLevel(logging.INFO)


def _load_kubernetes_config():
    if os.environ.get("KUBERNETES_SERVICE_HOST") is not None:
        load_incluster_config()
    else:
        load_kube_config()


class ConfigmapPersistencePlugin(PersistencePlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        _load_kubernetes_config()
        self._kubernetes_client = client.CoreV1Api()
        self._configmap_name = self.read_config_value('configmap_name')
        self._configmap_namespace = self.read_config_value('configmap_namespace')

    @staticmethod
    def required_configs() -> List[str]:
        return ['configmap_name', 'configmap_namespace']

    def _create_configmap(self):
        configmap = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=dict(name=self._configmap_name),
            data=dict()
        )
        self._kubernetes_client.create_namespaced_config_map(self._configmap_namespace, configmap)

    def read_state(self):
        try:
            data = self._kubernetes_client.read_namespaced_config_map(self._configmap_name, self._configmap_namespace, pretty=False, exact=False, export=True).data
            if data and 'yaml_data' in data:
                return oyaml.safe_load(data['yaml_data'])
            else:
                return {}
        except ApiException as e:
            if e.status == 404:
                self._create_configmap()
                return {}
            else:
                self.logger.critical(f"Error while reading state from configmap '{self._configmap_name}' in namespace '{self._configmap_namespace}'")
                raise e

    def persist_state(self, state):
        try:
            self._kubernetes_client.patch_namespaced_config_map(self._configmap_name, self._configmap_namespace, {'data': {"yaml_data": oyaml.safe_dump(state)}})
        except ApiException as e:
            self.logger.error(f"Error while writing state to configmap '{self._configmap_name}' in namespace '{self._configmap_namespace}': {str(e)}")
