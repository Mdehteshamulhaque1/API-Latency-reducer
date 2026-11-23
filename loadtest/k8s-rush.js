import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    rush: {
      executor: 'ramping-arrival-rate',
      startRate: 20,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { target: 50, duration: '1m' },
        { target: 150, duration: '1m' },
        { target: 150, duration: '3m' },
        { target: 0, duration: '30s' },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8085/api/v1/health');
  check(res, {
    'status 200': (r) => r.status === 200,
    'db healthy': (r) => r.status === 200 && r.json('database') === 'healthy',
  });
}