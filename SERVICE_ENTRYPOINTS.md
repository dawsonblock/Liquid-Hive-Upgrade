# 🎯 LIQUID HIVE SERVICE ENTRYPOINTS - CANONICAL MAPPING

## 📋 SERVICE ARCHITECTURE

| Service | Entrypoint | Port | Supervisor | Docker | Description |
|---------|------------|------|------------|--------|-------------|
| **Main API** | `apps.api.main:app` | 8001 | ✅ backend | api | Core FastAPI backend |
| **Feedback API** | `services.feedback_api.main:app` | 8091 | ✅ feedback_api | feedback-api | Feedback collection service |
| **Oracle API** | `services.oracle_api.main:app` | 8092 | ✅ oracle_api | oracle-api | Oracle decision engine |
| **Frontend** | `yarn start` | 3000 | ✅ frontend | frontend | React + TypeScript UI |
| **MongoDB** | `mongod` | 27017 | ✅ mongodb | mongodb | Database service |

## 🔧 SUPERVISOR CONFIGURATION

Current supervisor setup in `/etc/supervisor/conf.d/supervisord.conf`:

```ini
[program:backend]
command=/root/.venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8001
directory=/app

[program:frontend]  
command=yarn start
directory=/app/frontend

[program:feedback_api]
command=/root/.venv/bin/uvicorn services.feedback_api.main:app --host 0.0.0.0 --port 8091
directory=/app

[program:oracle_api]
command=/root/.venv/bin/uvicorn services.oracle_api.main:app --host 0.0.0.0 --port 8092  
directory=/app

[program:mongodb]
command=/usr/bin/mongod --bind_ip_all
```

## 🐳 DOCKER COMPOSE REQUIREMENTS

To match supervisor configuration, docker-compose.yaml needs:

1. **Port Alignment**: Use same ports as supervisor (8001, 8091, 8092, 3000)
2. **Build Contexts**: Point to correct Dockerfiles and contexts
3. **Environment Variables**: Ensure consistent configuration
4. **Service Dependencies**: Proper startup order and health checks

## 🎯 CURRENT STATUS

✅ **All Services Running**: 5/5 supervisor services operational  
✅ **Port Mapping Clear**: No conflicts between services  
✅ **Entrypoints Defined**: Each service has clear Python module path  
✅ **Health Checks Working**: All services respond to health endpoints  

## 🔧 NEXT ACTION

Update docker-compose.yaml to match this canonical service mapping.