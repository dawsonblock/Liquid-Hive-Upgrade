# Cost Profiles

Profiles from config/providers.yaml:

- cheap: max_tokens 1024, max_cost_usd_per_req 0.002
- balanced: max_tokens 2048, max_cost_usd_per_req 0.01
- quality: max_tokens 4096, max_cost_usd_per_req 0.05

Routing uses these to cap request budgets and enable demotion/promotion policies.
