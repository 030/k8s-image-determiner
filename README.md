# k8s-image-determiner

```bash
./test/script.sh
```

Cleanup:

```bash
./test/script.sh delete
```

Install [kubectl](https://kubernetes.io/docs/tasks/tools/).

```bash
kubectl get po --all-namespaces
```

Create a cronjob:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/website/main/content/en/examples/application/job/cronjob.yaml
```

```bash
K8S_IMAGE_DETERMINER_LOGGING_LEVEL=DEBUG python3 main.py
```

```bash
pytest --cov=main test.py --verbose --capture=no --cov-report term-missing
```

```bash
python3 mock_server.py
```
