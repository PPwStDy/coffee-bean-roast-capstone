import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 5 },  // Ramp-up to 5 concurrent VUs
    { duration: '20s', target: 10 }, // Sustained load at 10 VUs
    { duration: '10s', target: 0 },  // Ramp-down
  ],
  thresholds: {
    'http_req_duration{status:200}': ['p(95)<120', 'p(99)<250'], // SLO Thresholds
    'http_req_failed': ['rate<0.01'],                              // Error rate < 1%
  },
};

// Base64 1x1 dummy JPEG header or realistic synthetic image payload
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';

export default function () {
  const payload = JSON.stringify({
    image_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}/predict/base64`, payload, params);

  // Optical occlusion deliberate rejection or 200 OK
  check(res, {
    'status is valid (200 or 422)': (r) => r.status === 200 || r.status === 422,
    'latency within budget': (r) => r.timings.duration < 250,
  });

  sleep(0.05);
}
