import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 10 }, // Ramp up
    { duration: '1m', target: 20 },  // Stay at 20 users
    { duration: '30s', target: 0 },  // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.1'],    // Error rate under 10%
  },
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8080';

export default function () {
  // Health check
  let healthResponse = http.get(`${BASE_URL}/health`);
  check(healthResponse, {
    'health check status is 200': (r) => r.status === 200,
    'health check returns healthy': (r) => JSON.parse(r.body).status === 'healthy',
  });

  // Version endpoint
  let versionResponse = http.get(`${BASE_URL}/version`);
  check(versionResponse, {
    'version endpoint status is 200': (r) => r.status === 200,
    'version contains build info': (r) => JSON.parse(r.body).hasOwnProperty('version'),
  });

  // Root endpoint
  let rootResponse = http.get(`${BASE_URL}/`);
  check(rootResponse, {
    'root endpoint status is 200': (r) => r.status === 200,
    'root returns API message': (r) => JSON.parse(r.body).message.includes('Liquid Hive'),
  });

  sleep(1);
}