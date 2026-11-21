'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { waitForArtifact, ArtifactReadinessError } = require('./wait.cjs');
const visible = { artifacts: [{id: 123, name: 'github-pages', size: 4096}] };

function harness(responses, overrides = {}) {
  let clock = 0, calls = 0;
  const logs = [];
  const options = {artifactId: '123', timeoutMs: 100, intervalMs: 10,
    now: () => clock, pause: async (ms) => {clock += ms;}, log: (line) => logs.push(line),
    client: {listArtifacts: async () => {
      const response = responses[Math.min(calls++, responses.length - 1)];
      if (response instanceof Error) throw response;
      return response;
    }}, ...overrides};
  return { run: () => waitForArtifact(options), calls: () => calls, logs };
}

test('empty metadata immediately after upload retries until the exact ID is visible', async () => {
  const h = harness([{artifacts: []}, {artifacts: []}, visible, visible]);
  await h.run();
  assert.equal(h.calls(), 4);
});
test('already visible uploads still get two separate confirmations', async () => {
  const h = harness([visible]);await h.run();assert.equal(h.calls(), 2);
});
test('an old upload with the same name is never mistaken for this upload', async () => {
  const h = harness([{artifacts: [{id: 122, name: 'github-pages', size: 4096}]}, visible]);
  await h.run();assert.equal(h.calls(), 3);
});
test('a disappearing upload resets the consecutive confirmation count', async () => {
  const h = harness([visible, {artifacts: []}, visible, visible]);
  await h.run();assert.equal(h.calls(), 4);
});
test('unrelated artifacts, empty/expired uploads cannot allow deployment', async () => {
  for (const artifact of [{id: 123,name:'other',size:4096},
    {id:123,name:'github-pages',size:0}, {id:123,name:'github-pages',size:4096,expired:true}]) {
    await assert.rejects(harness([{artifacts:[artifact]}]).run(), /deadline/);
  }
});
test('persistent absence stops at a bounded deadline and preserves the old publication', async () => {
  const h = harness([{artifacts: []}]);
  await assert.rejects(h.run(), /Previous publication retained/);
  assert.equal(h.calls(), 10);
});
test('temporary API and connection errors are retried', async () => {
  for (const error of [Object.assign(new Error(), {status:503}),
    Object.assign(new Error(), {status:429}), Object.assign(new Error(), {code:'ECONNRESET'}),
    new Error('Failed request: (502)')]) {
    const h = harness([error, visible]);await h.run();assert.equal(h.calls(), 3);
  }
});
test('permission errors fail immediately without exposing raw responses', async () => {
  const h = harness([Object.assign(new Error('SECRET_RUNTIME_TOKEN'), {status:403})]);
  await assert.rejects(h.run(), (error) => error instanceof ArtifactReadinessError &&
    !error.message.includes('SECRET_RUNTIME_TOKEN'));
  assert.equal(h.calls(), 1);assert.ok(!h.logs.join(' ').includes('SECRET_RUNTIME_TOKEN'));
});
test('duplicate names and malformed responses stop without deployment', async () => {
  for(const response of [{artifacts:[...visible.artifacts,...visible.artifacts]}, {}, null]) {
    const h = harness([response]);await assert.rejects(h.run(),ArtifactReadinessError);
    assert.equal(h.calls(),1);
  }
});
test('invalid IDs fail before any network request', async () => {
  for (const artifactId of ['',undefined,'0','123/other','abc']) {
    const h = harness([visible],{artifactId});await assert.rejects(h.run(),ArtifactReadinessError);
    assert.equal(h.calls(),0);
  }
});
test('a stalled artifact request is bounded even if the SDK never resolves', async () => {
  const h = harness([], {timeoutMs:20, now:()=>Date.now(),
    client:{listArtifacts:()=>new Promise(()=>{})}});
  await assert.rejects(h.run(),/deadline/);
});

test('the installed official client exposes the same runtime artifact API as deploy-pages', async () => {
  const { DefaultArtifactClient } = await import('@actions/artifact');
  assert.equal(typeof DefaultArtifactClient.prototype.listArtifacts,'function');
});
