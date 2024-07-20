import logging
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def load_kube_config():
    try:
        config.load_kube_config()
        logger.info("Kubeconfig loaded successfully")
    except Exception as e:
        logger.error("Failed to load kubeconfig", exc_info=True)
        return


def list_pods():
    v1 = client.CoreV1Api()
    try:
        logger.info("Listing pods in all namespaces")
        ret = v1.list_pod_for_all_namespaces()
        for pod in ret.items:
            logger.info(
                f"Namespace: {pod.metadata.namespace}, Pod name: {pod.metadata.name}"
            )
            for container_status in pod.status.container_statuses:
                image = container_status.image
                image_id = container_status.image_id
                logger.info(
                    f"Container name: {container_status.name}, Container image: {image}, Image ID: {image_id}"
                )
    except ApiException as e:
        logger.error(
            "Exception when calling CoreV1Api->list_pod_for_all_namespaces",
            exc_info=True,
        )


def main():
    setup_logging()
    load_kube_config()
    list_pods()


if __name__ == "__main__":
    main()
