# k8s-image-determiner

<https://kind.sigs.k8s.io/>

```bash
kind_version=0.23.0; if ! ~/go/bin/kind --version | grep $kind_version; then go install sigs.k8s.io/kind@v${kind_version}; fi
```

```bash
~/go/bin/kind create cluster --image kindest/node:v1.30.2
```

Install [kubectl](https://kubernetes.io/docs/tasks/tools/).

```bash
kubectl get po --all-namespaces
```

```bash
~/go/bin/kind delete cluster
```
