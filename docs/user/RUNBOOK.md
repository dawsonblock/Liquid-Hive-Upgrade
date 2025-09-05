# Runbook

Incident triage:
- Check alerts in Grafana/Alertmanager.
- kubectl -n liquid-hive get events,pods
- Inspect OTEL traces and /metrics.

Rollback:
- helm rollback liquid-hive <REV>

Scale:
- Adjust HPA values and resource requests/limits in values.yaml.

Secrets:
- Verify ExternalSecret status: kubectl -n liquid-hive get externalsecret,secret
