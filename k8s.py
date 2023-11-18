import logging
from kubernetes import client, config
import os
from collections import Counter
import json


images_tags = []


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def list_pod_images():
    config.load_kube_config()

    v1 = client.CoreV1Api()
    logging.info("Listing pods with their images:")

    try:
        ret = v1.list_pod_for_all_namespaces(watch=False)

        for item in ret.items:
            for container in item.spec.containers:
                logging.info(f"Pod: {item.metadata.name}, Container Image: {container.image}")
                images_tags.append(container.image)

    except Exception as e:
        logging.error(f"Error: {e}")


def list_cronjob_images():
    config.load_kube_config()
    logging.info(f"Active host is {client.Configuration().host}")

    batch_v1beta1 = client.BatchV1Api()
    logging.info("Listing CronJobs:")

    try:
        cronjob_list = batch_v1beta1.list_cron_job_for_all_namespaces(watch=False)

        for cronjob in cronjob_list.items:
            template = cronjob.spec.job_template.spec.template
            for container in template.spec.containers:
                logging.info(f"CronJob: {cronjob.metadata.name}, Container Image: {container.image}")
                images_tags.append(container.image)
    except Exception as e:
        logging.error(f"Error: {e}")


def k8s():
    setup_logging()
    list_cronjob_images()
    list_pod_images()
    print(len(images_tags))
    unique_list = sorted(set(images_tags))
    print(len(unique_list))

    json_image = []

    for image in unique_list:
        parts = image.split(':')
        image = parts[0]
        tag = parts[1]
        print(image, tag)

        json_data = json.dumps({
            "name": image,
            "tag": tag,
            "grades": [92, 87, 95]
        })
        json_image.append(json_data)
        print(json_image)
