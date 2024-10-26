#!/bin/bash -e

readonly kind_binary=~/go/bin/kind
readonly kind_cluster_name=kind-k8s-image-determiner
readonly kind_command=${1}
readonly kind_version=0.24.0
# Check whether a k8s_version if supported by KIND:
# https://hub.docker.com/r/kindest/node/tags
readonly kubernetes_version=v1.31.1

install() {
  if ! ${kind_binary} --version | grep -q ${kind_version}; then
    go install sigs.k8s.io/kind@v${kind_version}
  fi
}

createCluster() {
  if ! ${kind_binary} get clusters | grep -q ${kind_cluster_name}; then
    ${kind_binary} create cluster \
      --image kindest/node:${kubernetes_version} \
      --name ${kind_cluster_name}
  fi
}

deleteCluster() {
  if [[ ${kind_command} == "delete" ]]; then
    kind delete cluster -n ${kind_cluster_name}
  fi
}

main() {
  install
  createCluster
  deleteCluster
}

main
