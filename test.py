import json
import logging
import main
import requests
import requests_mock
import unittest
from unittest.mock import patch, MagicMock
from main import (
    construct_json,
    extract_digest,
    extract_tag,
    list_cron_jobs,
    list_pods,
    load_kube_config,
    remove_tag,
    send_json_to_endpoint,
    setup_logging,
    unique_dicts_by_keys,
)
from kubernetes.client.rest import ApiException


def test_valid_digest():
    image_reference = "docker.io/library/busybox@sha256:141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47"
    assert (
        extract_digest(image_reference)
        == "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47"
    )


def test_no_digest():
    image_reference = "docker.io/library/busybox:latest"
    assert extract_digest(image_reference) is None


def test_invalid_format():
    image_reference = "docker.io/library/busybox@sha1:12345"
    assert extract_digest(image_reference) is None


def test_empty_input_digest_to_be_extracted():
    image_reference = ""
    assert extract_digest(image_reference) is None


def test_no_sha256_prefix():
    image_reference = "docker.io/library/busybox@abc123"
    assert extract_digest(image_reference) is None


def test_valid_tag():
    image_reference = "docker.io/library/busybox:latest"
    assert extract_tag(image_reference) == "latest"


def test_no_tag_to_be_extracted():
    image_reference = "docker.io/library/busybox"
    assert extract_tag(image_reference) is None


def test_invalid_format_tag():
    image_reference = "docker.io/library/busybox:invalid@format"
    assert extract_tag(image_reference) == "invalid@format"


def test_empty_input_tag_to_be_extracted():
    image_reference = ""
    assert extract_tag(image_reference) is None


def test_no_colon():
    image_reference = "docker.io/library/busybox"
    assert extract_tag(image_reference) is None


def test_remove_valid_tag():
    image_reference = "docker.io/library/busybox:latest"
    assert remove_tag(image_reference) == "docker.io/library/busybox"


def test_remove_tag_with_version():
    image_reference = "docker.io/library/busybox:v1.0"
    assert remove_tag(image_reference) == "docker.io/library/busybox"


def test_no_tag():
    image_reference = "docker.io/library/busybox"
    assert remove_tag(image_reference) == "docker.io/library/busybox"


def test_empty_input():
    image_reference = ""
    assert remove_tag(image_reference) == ""


def test_tag_with_colon():
    image_reference = "docker.io/library/busybox:latest:extra"
    assert remove_tag(image_reference) == "docker.io/library/busybox:latest"


def test_unique_dicts():
    dicts = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 1, "name": "Alice"},
        {"id": 3, "name": "Charlie"},
    ]
    keys = ["id"]
    expected = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]
    assert unique_dicts_by_keys(dicts, keys) == expected


def test_unique_dicts_multiple_keys():
    dicts = [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 1, "name": "Alice", "age": 25},
        {"id": 2, "name": "Bob", "age": 30},
        {"id": 2, "name": "Bob", "age": 35},
    ]
    keys = ["id", "name"]
    expected = [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 30},
    ]
    assert unique_dicts_by_keys(dicts, keys) == expected


def test_no_duplicates():
    dicts = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    keys = ["id"]
    expected = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    assert unique_dicts_by_keys(dicts, keys) == expected


def test_empty_list():
    dicts = []
    keys = ["id"]
    assert unique_dicts_by_keys(dicts, keys) == []


def test_empty_dicts():
    dicts = [{}, {}, {}]
    keys = []
    expected = [{}]
    assert unique_dicts_by_keys(dicts, keys) == expected


def test_non_existent_key():
    dicts = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    keys = ["non_existent_key"]
    expected = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    assert unique_dicts_by_keys(dicts, keys) == expected


def test_construct_json_single_entry():
    images = [
        {
            "image": "docker.io/library/busybox",
            "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
            "tag": "1.28",
        }
    ]
    expected_json = json.dumps(
        [
            {
                "name": "docker.io/library/busybox",
                "digestSha256": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                "tag": "1.28",
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
        ],
        indent=2,
    )
    result_json = construct_json(images)
    assert result_json == expected_json


def test_construct_json_multiple_entries():
    images = [
        {
            "image": "docker.io/library/busybox",
            "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
            "tag": "1.28",
        },
        {
            "image": "docker.io/library/alpine",
            "digest": "b1f2a2b8c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
            "tag": "3.12",
        },
    ]
    expected_json = json.dumps(
        [
            {
                "name": "docker.io/library/busybox",
                "digestSha256": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                "tag": "1.28",
                "account": {
                    "environment": "dev",
                    "id": 123,
                    "name": "hello",
                    "owner": "world",
                    "project": "some-project",
                    "provider": "aws",
                    "team": "some-team",
                },
            },
            {
                "name": "docker.io/library/alpine",
                "digestSha256": "b1f2a2b8c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
                "tag": "3.12",
                "account": {
                    "environment": "dev",
                    "id": 123,
                    "name": "hello",
                    "owner": "world",
                    "project": "some-project",
                    "provider": "aws",
                    "team": "some-team",
                },
            },
        ],
        indent=2,
    )
    result_json = construct_json(images)
    assert result_json == expected_json


def test_construct_json_empty_list():
    images = []
    expected_json = json.dumps([], indent=2)
    result_json = construct_json(images)
    assert result_json == expected_json


def test_construct_json_missing_keys():
    images = [
        {
            "image": "docker.io/library/busybox"
            # 'digest' and 'tag' are missing
        }
    ]
    expected_json = json.dumps(
        [
            {
                "name": "docker.io/library/busybox",
                "digestSha256": None,  # None should be reflected as null in JSON
                "tag": None,  # None should be reflected as null in JSON
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
        ],
        indent=2,
    )
    result_json = construct_json(images)
    assert result_json == expected_json


class TestListPods(unittest.TestCase):
    @patch("main.client.CoreV1Api")
    def test_list_pods(self, mock_core_v1_api):
        # Create mock objects
        mock_pod = MagicMock()
        mock_pod.metadata.namespace = "default"
        mock_pod.metadata.name = "test-pod"

        mock_container_status = MagicMock()
        mock_container_status.name = "test-container"
        mock_container_status.image = "docker.io/library/busybox:1.28"
        digest = (
            "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47"
        )
        mock_container_status.image_id = (
            "docker.io/library/busybox@sha256:" + digest
        )
        mock_pod.status.container_statuses = [mock_container_status]

        mock_core_v1_api.return_value.list_pod_for_all_namespaces.return_value.items = [
            mock_pod
        ]

        expected_output = [
            {
                "image": "docker.io/library/busybox",
                "digest": digest,
                "tag": "1.28",
            }
        ]

        result = list_pods()

        self.assertEqual(result, expected_output)

    @patch("main.client.CoreV1Api")
    def test_list_pods_api_exception(self, mock_core_v1_api):
        # Mock the CoreV1Api to raise an ApiException
        mock_core_v1_api.return_value.list_pod_for_all_namespaces.side_effect = ApiException(
            "API Exception"
        )

        # Check if the function handles the exception gracefully and returns an empty list
        result = list_pods()

        self.assertEqual(result, [])


class TestListCronJobs(unittest.TestCase):
    @patch("main.client.CoreV1Api")
    @patch("main.client.BatchV1Api")
    def test_list_cron_jobs(self, mock_batch_v1_api, mock_core_v1_api):
        # Create mock objects for the job and pod template
        mock_job = MagicMock()
        mock_job.metadata.namespace = "default"
        mock_job.metadata.name = "test-job"

        mock_container = MagicMock()
        mock_container.name = "test-container"
        mock_container.image = "docker.io/library/busybox:1.28"

        mock_job.spec.template.spec.containers = [mock_container]

        # Mocking the BatchV1Api response for jobs
        mock_batch_v1_api.return_value.list_job_for_all_namespaces.return_value.items = [
            mock_job
        ]

        # Create a mock pod object with container statuses
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"

        mock_container_status = MagicMock()
        mock_container_status.name = "test-container"
        mock_container_status.image = "docker.io/library/busybox:1.28"
        digest = (
            "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47"
        )
        mock_container_status.image_id = (
            "docker.io/library/busybox@sha256:" + digest
        )

        mock_pod.status.container_statuses = [mock_container_status]

        # Mocking the CoreV1Api response for pods
        mock_core_v1_api.return_value.list_namespaced_pod.return_value.items = [
            mock_pod
        ]

        expected_output = [
            {
                "image": "docker.io/library/busybox",
                "digest": digest,
                "tag": "1.28",
            }
        ]

        result = list_cron_jobs()

        self.assertEqual(result, expected_output)

    @patch("main.client.CoreV1Api")
    @patch("main.client.BatchV1Api")
    def test_list_cron_jobs_api_exception(
        self, mock_batch_v1_api, mock_core_v1_api
    ):
        # Mock the BatchV1Api to raise an ApiException
        mock_batch_v1_api.return_value.list_job_for_all_namespaces.side_effect = ApiException(
            "API Exception"
        )

        # Check if the function handles the exception gracefully and returns an empty list
        result = list_cron_jobs()

        self.assertEqual(result, [])


class TestLoadKubeConfig(unittest.TestCase):
    @patch("main.config.load_kube_config")
    @patch("main.logger")  # Patch the logger object
    def test_load_kube_config_success(self, mock_logger, mock_load_kube_config):
        # Mock the load_kube_config method to succeed
        mock_load_kube_config.return_value = None

        # Call the function
        load_kube_config()

        # Check that the logger info method was called with the success message
        mock_logger.info.assert_called_with("Kubeconfig loaded successfully")

    @patch("main.config.load_kube_config")
    @patch("main.logger")  # Patch the logger object
    def test_load_kube_config_failure(self, mock_logger, mock_load_kube_config):
        # Mock the load_kube_config method to raise an exception
        mock_load_kube_config.side_effect = Exception("Load kubeconfig failed")

        # Call the function
        load_kube_config()

        # Check that the logger error method was called with the failure message
        mock_logger.error.assert_called_with(
            "Failed to load kubeconfig: '%s'",
            "Load kubeconfig failed",
            exc_info=True,
        )


class TestSetupLogging(unittest.TestCase):
    @patch("logging.basicConfig")
    def test_setup_logging(self, mock_basic_config):
        # Call the setup_logging function
        setup_logging()

        # Extract the actual call parameters
        args, kwargs = mock_basic_config.call_args

        # Check if the logging level, format, and handlers are as expected
        self.assertEqual(kwargs.get("level"), logging.INFO)
        self.assertEqual(
            kwargs.get("format"),
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Check if handlers list contains a StreamHandler
        handlers = kwargs.get("handlers", [])
        self.assertEqual(len(handlers), 1)
        self.assertIsInstance(handlers[0], logging.StreamHandler)


class TestMainFunction(unittest.TestCase):
    @patch("main.send_json_to_endpoint")
    @patch("main.setup_logging")
    @patch("main.load_kube_config")
    @patch("main.list_pods")
    @patch("main.list_cron_jobs")
    @patch("main.unique_dicts_by_keys")
    @patch("main.construct_json")
    def test_main(
        self,
        mock_construct_json,
        mock_unique_dicts_by_keys,
        mock_list_cron_jobs,
        mock_list_pods,
        mock_load_kube_config,
        mock_setup_logging,
        mock_send_json_to_endpoint,
    ):
        # Mock return values for functions called in main()
        mock_list_pods.return_value = [
            {
                "image": "docker.io/library/busybox",
                "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                "tag": "1.28",
            }
        ]
        mock_list_cron_jobs.return_value = [
            {
                "image": "docker.io/library/busybox",
                "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                "tag": "1.28",
            }
        ]
        mock_unique_dicts_by_keys.return_value = [
            {
                "image": "docker.io/library/busybox",
                "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                "tag": "1.28",
            }
        ]
        mock_construct_json.return_value = """
{
  "image": "docker.io/library/busybox",
  "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
  "tag": "1.28"
}
"""

        # Call the main function
        main.main()

        # Verify that setup_logging was called
        mock_setup_logging.assert_called_once()

        # Verify that load_kube_config was called
        mock_load_kube_config.assert_called_once()

        # Verify that list_pods was called
        mock_list_pods.assert_called_once()

        # Verify that list_cron_jobs was called
        mock_list_cron_jobs.assert_called_once()

        # Verify that unique_dicts_by_keys was called with the expected arguments
        mock_unique_dicts_by_keys.assert_called_once_with(
            [
                {
                    "image": "docker.io/library/busybox",
                    "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                    "tag": "1.28",
                },
                {
                    "image": "docker.io/library/busybox",
                    "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                    "tag": "1.28",
                },
            ],
            ["image", "digest", "tag"],
        )

        # Verify that construct_json was called with the expected arguments
        mock_construct_json.assert_called_once_with(
            [
                {
                    "image": "docker.io/library/busybox",
                    "digest": "141c253bc4c3fd0a201d32dc1f493bcf3fff003b6df416dea4f41046e0f37d47",
                    "tag": "1.28",
                }
            ]
        )

        mock_send_json_to_endpoint.assert_called_once_with(
            mock_construct_json.return_value
        )


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class TestSendJsonToEndpoint(unittest.TestCase):

    def setUp(self):
        # Setup logging
        setup_logging()

    @requests_mock.Mocker()
    def test_send_json_success(self, mock):
        url = "http://localhost:5000/endpoint"
        mock.post(url, json={"message": "success"}, status_code=200)

        with self.assertLogs(logger, level="INFO") as log:
            send_json_to_endpoint('{"key": "value"}')

        # Check that the request was made with correct parameters
        self.assertTrue(mock.called)
        request = mock.request_history[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, url)
        self.assertEqual(request.json(), {"key": "value"})

        # Check the logs
        self.assertIn("Request was successful.", log.output[0])
        self.assertIn("Response JSON: {'message': 'success'}", log.output[1])

    @requests_mock.Mocker()
    def test_send_json_http_error_400(self, mock):
        url = "http://localhost:5000/endpoint"
        mock.post(url, status_code=400)

        with self.assertLogs(logger, level="ERROR") as log:
            send_json_to_endpoint('{"key": "value"}')

        # Check the logs for error message
        self.assertIn("HTTP error occurred:", log.output[0])

    @requests_mock.Mocker()
    def test_send_json_http_error_500(self, mock):
        url = "http://localhost:5000/endpoint"
        mock.post(url, status_code=500)

        with self.assertLogs(logger, level="ERROR") as log:
            send_json_to_endpoint('{"key": "value"}')

        # Check the logs for error message
        self.assertIn("Internal Server Error occurred:", log.output[0])

    @requests_mock.Mocker()
    def test_send_json_connection_error(self, mock):
        url = "http://localhost:5000/endpoint"
        mock.register_uri(
            "POST",
            url,
            exc=requests.exceptions.ConnectionError("Connection error"),
        )

        with self.assertLogs(logger, level="ERROR") as log:
            send_json_to_endpoint('{"key": "value"}')

        # Check the logs for error message
        self.assertIn(
            "Error connecting to the endpoint: Connection error", log.output[0]
        )

    @requests_mock.Mocker()
    def test_send_json_timeout(self, mock):
        url = "http://localhost:5000/endpoint"
        mock.register_uri(
            "POST", url, exc=requests.exceptions.Timeout("Timeout error")
        )

        with self.assertLogs(logger, level="ERROR") as log:
            send_json_to_endpoint('{"key": "value"}')

        # Check the logs for error message
        self.assertIn("Request timed out: Timeout error", log.output[0])

    @requests_mock.Mocker()
    def test_send_json_request_exception(self, mock):
        url = "http://localhost:5000/endpoint"
        mock.register_uri(
            "POST",
            url,
            exc=requests.exceptions.RequestException("Request exception"),
        )

        with self.assertLogs(logger, level="ERROR") as log:
            send_json_to_endpoint('{"key": "value"}')

        # Check the logs for error message
        self.assertIn(
            "An error occurred while sending the request: Request exception",
            log.output[0],
        )

    @requests_mock.Mocker()
    def test_send_json_unexpected_exception(self, mock):
        url = "http://localhost:5000/endpoint"
        mock.register_uri("POST", url, exc=Exception("Unexpected error"))

        with self.assertLogs(logger, level="ERROR") as log:
            send_json_to_endpoint('{"key": "value"}')

        # Check the logs for error message
        self.assertIn(
            "An unexpected error occurred: Unexpected error", log.output[0]
        )
