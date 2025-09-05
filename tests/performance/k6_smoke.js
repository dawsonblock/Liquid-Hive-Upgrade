import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = { vus: 1, duration: '10s' };

export default function () {
  const url = __ENV.TARGET_URL || 'http://localhost:8000/healthz';
  const res = http.get(url);
  check(res, { 'status is 2xx': (r) => r.status >= 200 && r.status < 300 });
  sleep(1);
}
