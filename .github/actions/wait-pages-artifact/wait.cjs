'use strict';

class ArtifactReadinessError extends Error {}

function transient(error) {
  const status = Number(error?.status ?? error?.statusCode ??
    /Failed request: \((\d+)\)/.exec(error?.message || '')?.[1]);
  return status === 408 || status === 429 || (status >= 500 && status <= 599) ||
    ['ECONNRESET', 'ETIMEDOUT', 'EAI_AGAIN', 'ENOTFOUND', 'ECONNREFUSED'].includes(error?.code);
}

function bounded(operation, milliseconds) {
  let timer;
  return Promise.race([
    operation,
    new Promise((_, reject) => {
      timer = setTimeout(() => reject(new ArtifactReadinessError(
        'Radar upload did not become visible before the deadline. Previous publication retained.')),
        milliseconds);
    }),
  ]).finally(() => clearTimeout(timer));
}

async function waitForArtifact({client, artifactId, artifactName = 'github-pages',
  timeoutMs = 120000, intervalMs = 3000, now = () => Date.now(),
  pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms)), log = () => {}}) {
  if (!/^[1-9]\d*$/.test(String(artifactId || '')) ||
      !/^[a-zA-Z0-9_-]{1,100}$/.test(artifactName) ||
      !Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 300000 ||
      !Number.isInteger(intervalMs) || intervalMs < 1 || intervalMs > 10000) {
    throw new ArtifactReadinessError('Invalid artifact readiness inputs. Deployment was not started.');
  }
  const deadline = now() + timeoutMs;
  let confirmations = 0;
  let polls = 0;
  while (now() < deadline) {
    const remaining = deadline - now();
    try {
      const result = await bounded(client.listArtifacts(), remaining);
      if (!result || !Array.isArray(result.artifacts)) {
        throw new ArtifactReadinessError('Invalid artifact service response. Deployment was not started.');
      }
      const matches = result.artifacts.filter((artifact) => artifact.name === artifactName);
      if (matches.length > 1) {
        throw new ArtifactReadinessError('Multiple radar uploads have the same name. Deployment was not started.');
      }
      const expected = matches.length === 1 && String(matches[0].id) === String(artifactId) &&
        Number.isFinite(matches[0].size) && matches[0].size > 0 && matches[0].expired !== true;
      confirmations = expected ? confirmations + 1 : 0;
      // Two consecutive reads cover propagation to the same service that the
      // official deploy-pages action will query immediately after this action.
      if (confirmations >= 2 && now() < deadline) {
        log('The exact radar upload is visible to the Pages artifact service. Ready to deploy.');
        return;
      }
    } catch (error) {
      confirmations = 0;
      if (error instanceof ArtifactReadinessError) throw error;
      if (!transient(error)) {
        throw new ArtifactReadinessError('Artifact service verification failed. Deployment was not started.');
      }
    }
    polls++;
    if (polls === 1 || polls % 5 === 0) {
      log('Waiting for GitHub to recognize the completed radar upload...');
    }
    const delay = Math.min(intervalMs, deadline - now());
    if (delay > 0) await pause(delay);
  }
  throw new ArtifactReadinessError(
    'Radar upload did not become visible before the deadline. Previous publication retained.');
}
module.exports = { waitForArtifact, ArtifactReadinessError };
