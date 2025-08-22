Title: ATLAS Infrastructure Deployment Recovery
Severity: P1
Symptoms: K8s services not responding, pods in crash loop, missing PVCs
Detection: Prometheus alerts, kubectl get pods showing errors
Mitigation: 
1. Check namespace: `kubectl get ns atlas`
2. Check pods: `kubectl get pods -n atlas`
3. Check PVCs: `kubectl get pvc -n atlas`
4. Restart deployments: `kubectl rollout restart deployment -n atlas`
5. Check logs: `kubectl logs -n atlas -l app.kubernetes.io/part-of=atlas-system`

Root cause: Common issues include:
- Missing StorageClass or insufficient disk space
- Resource limits exceeded (check ResourceQuota)
- Network policy blocking traffic
- Missing secrets or misconfigured environment variables

Investigation steps:
1. Verify storage: `kubectl get storageclass atlas-storage`
2. Check resource usage: `kubectl top pods -n atlas`
3. Validate manifests: `kubeval infra/k8s/manual/*.yaml`
4. Test network connectivity between services

Recovery procedures:
1. If storage issues: Re-create PVCs or adjust StorageClass
2. If resource issues: Update ResourceQuota or optimize pod requests/limits
3. If networking issues: Review NetworkPolicy rules
4. If config issues: Update ConfigMaps and restart affected pods

Prevention:
- Regular backup of persistent data
- Monitor disk usage and resource consumption
- Validate manifests in CI/CD pipeline
- Test disaster recovery procedures monthly

Postmortem: Document in docs/postmortems/YYYY-MM-DD-infrastructure-failure.md