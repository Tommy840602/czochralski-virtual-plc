import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = (__ENV.BASE_URL || 'https://plc.tommy-huang.dev').replace(/\/$/, '');
const profile = (__ENV.PROFILE || 'baseline').toLowerCase();

const profiles = {
  smoke: { executor: 'constant-vus', vus: 1, duration: '10s' },
  baseline: {
    executor: 'ramping-vus',
    startVUs: 1,
    stages: [
      { duration: '15s', target: 5 },
      { duration: '30s', target: 5 },
      { duration: '15s', target: 10 },
      { duration: '30s', target: 10 },
      { duration: '10s', target: 0 },
    ],
  },
  breakpoint: {
    executor: 'ramping-vus',
    startVUs: 1,
    stages: [
      { duration: '30s', target: 200 },
      { duration: '30s', target: 200 },
      { duration: '30s', target: 500 },
      { duration: '30s', target: 500 },
      { duration: '30s', target: 1000 },
      { duration: '30s', target: 1000 },
      { duration: '30s', target: 2000 },
      { duration: '30s', target: 2000 },
      { duration: '60s', target: 5000 },
      { duration: '30s', target: 5000 },
      { duration: '30s', target: 0 },
    ],
    gracefulRampDown: '10s',
  },
};

if (!profiles[profile]) throw new Error(`Unsupported PROFILE: ${profile}`);
const breakpoint = profile === 'breakpoint';

export const options = {
  discardResponseBodies: true,
  scenarios: { readonly: profiles[profile] },
  thresholds: {
    checks: ['rate>0.99'],
    http_req_failed: breakpoint
      ? [{ threshold: 'rate<0.01', abortOnFail: true, delayAbortEval: '10s' }]
      : ['rate<0.01'],
    http_req_duration: breakpoint
      ? [{ threshold: 'p(95)<3000', abortOnFail: true, delayAbortEval: '15s' }, 'p(99)<5000']
      : ['p(95)<1500', 'p(99)<3000'],
  },
};

export default function () {
  const paths = profile === 'smoke' ? ['/', '/api/livez', '/api/readyz'] : ['/', '/api/livez'];
  for (const path of paths) {
    const response = http.get(`${baseUrl}${path}`, { tags: { endpoint: path }, timeout: '10s' });
    check(response, { [`PLC ${path} returns 200`]: (res) => res.status === 200 });
  }
  sleep(1);
}
