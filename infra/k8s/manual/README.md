This folder contains manually refined Kubernetes manifests generated from `kompose`.

Process:
1. Run `kompose convert -f compose.yaml -o infra/k8s/kompose-generated/`.
2. Copy or move edited manifests into this folder after converting Deployments->StatefulSet, adding PVCs, probes, and resources.
3. Validate with `kubeval` or `kubeconform` before committing.

Keep manual edits minimal and document changes in commit messages.
