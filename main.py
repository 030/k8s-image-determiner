import json
import logging
import requests
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import re


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
        logger.error("Failed to load kubeconfig: '%s'", str(e), exc_info=True)
        return


def extract_digest(image_reference) -> str:
    pattern = r"sha256:([a-f0-9]{64})"
    match = re.search(pattern, image_reference)
    if match:
        digest = match.group(1)
        return digest
    else:
        return None


def extract_tag(image_reference) -> str:
    pattern = r":([^:]+)$"
    match = re.search(pattern, image_reference)
    if match:
        tag = match.group(1)
        return tag
    else:
        return None


def remove_tag(image_reference) -> str:
    pattern = r"(:[^:]+)$"
    clean_reference = re.sub(pattern, "", image_reference)
    return clean_reference


def unique_dicts_by_keys(dicts, keys):
    if not any(all(k in d for k in keys) for d in dicts):
        return dicts
    seen = set()
    unique = []
    for d in dicts:
        composite_key = tuple(d.get(k, None) for k in keys)
        if composite_key not in seen:
            seen.add(composite_key)
            unique.append(d)
    return unique


def list_pods() -> dict:
    v1 = client.CoreV1Api()
    dict_list = []
    try:
        logger.info("Listing pods in all namespaces")
        ret = v1.list_pod_for_all_namespaces()
        for pod in ret.items:
            logger.debug(
                f"Namespace: {pod.metadata.namespace}, Pod name: {pod.metadata.name}"
            )
            for container_status in pod.status.container_statuses:
                image = container_status.image
                image_id = container_status.image_id
                logger.debug(
                    f"Container name: {container_status.name}, Container image: {image}, Image ID: {image_id}"
                )
                tag = extract_tag(image)
                image = remove_tag(image)
                image_id = extract_digest(image_id)
                new_dict = {"image": image, "digest": image_id, "tag": tag}
                dict_list.append(new_dict)
    except ApiException as e:
        logger.error(
            "Exception when calling CoreV1Api->list_pod_for_all_namespaces: '%s'",
            str(e),
            exc_info=True,
        )
    logger.info("Unique container images and their digests:")
    return dict_list


def list_cron_jobs() -> dict:
    batch_v1 = client.BatchV1Api()
    core_v1 = client.CoreV1Api()
    dict_list = []
    try:
        logger.info("Listing Jobs in all namespaces")
        jobs = batch_v1.list_job_for_all_namespaces()
        for job in jobs.items:
            logger.debug(
                f"Namespace: {job.metadata.namespace}, Job name: {job.metadata.name}"
            )
            pod_template = job.spec.template
            for container in pod_template.spec.containers:
                logger.debug(
                    f"  Container name: {container.name}, Container image: {container.image}"
                )
                job_selector = f"job-name={job.metadata.name}"
                pods = core_v1.list_namespaced_pod(
                    namespace=job.metadata.namespace,
                    label_selector=job_selector,
                )
                for pod in pods.items:
                    for container_status in pod.status.container_statuses:
                        if container_status.name == container.name:
                            image = container_status.image
                            image_id = container_status.image_id
                            logger.debug(
                                f"    Pod name: {pod.metadata.name}, Image digest: {image_id}"
                            )
                            tag = extract_tag(image)
                            image = remove_tag(image)
                            image_id = extract_digest(image_id)
                            new_dict = {
                                "image": image,
                                "digest": image_id,
                                "tag": tag,
                            }
                            dict_list.append(new_dict)
    except ApiException as e:
        logger.error(
            "Exception when calling BatchV1beta1Api->list_cron_job_for_all_namespaces: '%s'",
            str(e),
            exc_info=True,
        )
    logger.info("Unique container images and their digests:")
    return dict_list


def construct_json(images: dict) -> str:
    json_data = json.dumps(
        [
            {
                "name": item.get("image"),
                "digestSha256": item.get("digest"),
                "tag": item.get("tag"),
                "account": {
                    "environment": "dev",
                    "id": 123,
                    "name": "hello",
                    "owner": "world",
                    "project": "some-project",
                    "provider": "aws",
                    "team": "some-team",
                },
            }
            for item in images
        ],
        indent=2,
    )
    logger.debug("JSON data: " + json_data)
    return json_data


def send_json_to_endpoint(json_string):
    url = "http://localhost:5000/endpoint"

    try:
        response = requests.post(
            url, data=json_string, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)

        # Log success
        logger.info("Request was successful.")
        logger.info("Response JSON: %s", response.json())
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 500:
            logger.error("Internal Server Error occurred: %s", http_err)
        else:
            logger.error("HTTP error occurred: %s", http_err)
    except requests.exceptions.ConnectionError as conn_err:
        logger.error("Error connecting to the endpoint: %s", conn_err)
    except requests.exceptions.Timeout as timeout_err:
        logger.error("Request timed out: %s", timeout_err)
    except requests.exceptions.RequestException as req_err:
        logger.error("An error occurred while sending the request: %s", req_err)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)


def main():
    setup_logging()
    load_kube_config()
    pod_images = list_pods()
    cron_job_images = list_cron_jobs()
    pod_images.extend(cron_job_images)
    unique_pod_images = unique_dicts_by_keys(
        pod_images, ["image", "digest", "tag"]
    )
    json_string = construct_json(unique_pod_images)
    print(json_string)
    send_json_to_endpoint(json_string)


if __name__ == "__main__":
    main()
