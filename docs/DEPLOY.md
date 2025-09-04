# Deploy

- Prereqs: Helm, kubectl, External Secrets Operator, Prometheus Operator.
- Namespace:
  - Chart has `namespaceCreate: false` by default. Using `--create-namespace` with Helm is recommended.
  - Alternatively, set `--set namespaceCreate=true` to let the chart create Namespace/Quota/LimitRange.
- Install:
  helm upgrade --install liquid-hive deploy/helm/liquid-hive \
    --namespace liquid-hive --create-namespace \
    --set unifiedRuntime.image.repository=ghcr.io/ORG/liquid-hive-unified-runtime \
    --set unifiedRuntime.image.tag=1.0.0
- Metrics:
  - ServiceMonitor is disabled by default. Enable with:
    helm upgrade --install liquid-hive deploy/helm/liquid-hive \
      --namespace liquid-hive \
      --set monitoring.serviceMonitor.enabled=true
- Verify:
  kubectl -n liquid-hive get pods,svc,hpa,pdb
  kubectl -n liquid-hive logs deploy/liquid-hive-unified-runtime
