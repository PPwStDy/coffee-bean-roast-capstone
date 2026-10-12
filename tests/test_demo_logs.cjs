const { test } = require('node:test');
const assert = require('node:assert/strict');
require('../service/static/demo/log-tools.js');
const { parse, summarize, serverDuration } = globalThis.RoastLogTools;

test('mixed Uvicorn output retains structured events and reports ignored lines', () => {
  const result = parse('INFO: Startup complete\n{"event":"http_request","status":200,"request_id":"abc"}\n{"event":"occlusion_guard_rejection","pixel_std":0}\nnot JSON');
  assert.equal(result.records.length, 2);
  assert.equal(result.records[0].request_id, 'abc');
  assert.equal(result.ignored, 2);
  assert.deepEqual(summarize(result.records), { events:2, requests:1, errors:0, guards:1 });
});
test('Azure escaped JSON unwraps safely; malformed nested logs are counted', () => {
  const result = parse(JSON.stringify([{Log_s:JSON.stringify({event:'http_request',status:422})},{Log_s:'{broken'},{irrelevant:1}]));
  assert.equal(result.records[0].status, 422);
  assert.equal(result.ignored, 2);
});
test('response observations identify optical rejection without counting other 422s', () => {
  const records = [{event:'http_request',status:422,response:{detail:{error:'Optical Occlusion / Specular Glare Detected'}}},{event:'http_request',status:422,response:{detail:'Malformed schema'}}];
  assert.deepEqual(summarize(records),{events:2,requests:2,errors:2,guards:1});
});
test('server timing is absent rather than zero when no header was supplied', () => {
  assert.equal(serverDuration('app;dur=42.73'),42.73);
  assert.equal(serverDuration('cache;dur=1, app;dur=7'),7);
  assert.equal(serverDuration(null),null);
});
test('large logs retain the latest 1000 events and plain text never becomes an event', () => {
  const result = parse(JSON.stringify(Array.from({length:1002},(_,i)=>({event:'http_request',request_id:String(i)}))));
  assert.equal(result.records.length,1000);
  assert.equal(result.records[0].request_id,'2');
  assert.equal(result.truncated,2);
  assert.equal(parse('<script>alert(1)</script>').records.length,0);
});
