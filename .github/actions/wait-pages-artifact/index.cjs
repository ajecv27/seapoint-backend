'use strict';
const { performance } = require('node:perf_hooks');
const { waitForArtifact, ArtifactReadinessError } = require('./wait.cjs');

async function main() {
  const { DefaultArtifactClient } = await import('@actions/artifact');
  const seconds = Number(process.env['INPUT_TIMEOUT-SECONDS'] || '120');
  if (!Number.isInteger(seconds) || seconds < 1 || seconds > 300) {
    throw new ArtifactReadinessError('Invalid artifact readiness timeout.');
  }
  // A JavaScript action receives the same run-scoped runtime credentials and
  // Results service URL as deploy-pages. A REST-only check would test a
  // different index and could miss the upload/deploy visibility race.
  await waitForArtifact({
    client: new DefaultArtifactClient(),
    artifactId: process.env['INPUT_ARTIFACT-ID'],
    artifactName: process.env['INPUT_ARTIFACT-NAME'] || 'github-pages',
    timeoutMs: seconds * 1000,
    now: () => performance.now(),
    log: (message) => console.log(message),
  });
}

main().catch((error) => {
  // Do not print raw SDK responses, signed URLs or runtime credentials.
  console.error(error instanceof ArtifactReadinessError ? error.message :
    'Could not verify the uploaded radar artifact. Previous radar publication retained.');
  process.exit(1);
});
