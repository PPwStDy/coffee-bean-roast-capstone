import http from 'k6/http';
import encoding from 'k6/encoding';
import { check } from 'k6';

const images = ['Dark', 'Green', 'Light', 'Medium'].map(
  name => encoding.b64encode(open(`../tests/fixtures/${name}.png`, 'b'))
);
const slo = JSON.parse(open('../monitoring/slo.json'));

export const options = {
  scenarios: { warm: { executor: 'shared-iterations', vus: 2, iterations: 1000, maxDuration: '30m' } },
  thresholds: {
    http_req_duration: [`p(95)<=${slo.warm_p95_ms}`, `p(99)<=${slo.warm_p99_ms}`],
    http_req_failed: ['rate==0'],
    checks: ['rate==1'],
  },
};

const BASE_URL = __ENV.TARGET_URL;

export default function () {
  const payload = JSON.stringify({
    image_base64: images[__ITER % images.length],
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}/predict/base64`, payload, params);

  check(res, {
    'valid prediction': r => {
      if (r.status !== 200) return false;
      const body = r.json();
      const probabilities = Object.values(body.probabilities);
      return probabilities.length === 4
        && probabilities.every(p => Number.isFinite(p) && p >= 0 && p <= 1)
        && body.predicted_class_id >= 0 && body.predicted_class_id < 4
        && r.headers['X-Model-Version'] === body.model_version;
    },
  });
}
