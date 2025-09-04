# Deploy

- Prereqs: Helm, kubectl, External Secrets Operator, Prometheus Operator.
- Install:
  helm upgrade --install liquid-hive deploy/helm/liquid-hive \
    --namespace liquid-hive --create-namespace \
    --set unifiedRuntime.image.repository=ghcr.io/ORG/liquid-hive-unified-runtime \
    --set unifiedRuntime.image.tag=1.0.0
- Verify:
  kubectl -n liquid-hive get pods,svc,hpa,pdb
  kubectl -n liquid-hive logs deploy/liquid-hive-unified-runtime
