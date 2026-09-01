/**
 * Reflow TypeScript SDK Quickstart Example.
 * Demonstrates: API key auth, content ingest, publication creation with idempotency key, and job polling.
 */

import { ReflowClient } from '../../packages/typescript-sdk/src/index';

async function runQuickstart() {
  const apiKey = process.env.REFLOW_API_KEY || 'reflow_live_quickstart_key';
  const client = new ReflowClient({ apiKey, baseUrl: 'http://localhost:8000/api/v1' });

  console.log('1. Creating text content item...');
  const content = await client.content.createText(
    'TypeScript SDK Quickstart Post',
    'Reflow TypeScript SDK brings strongly typed API access to web applications and Node.js microservices.'
  );
  console.log(`   Created Content ID: ${content.id}`);

  console.log('2. Creating publication payload with Idempotency-Key...');
  const pub = await client.publications.create(
    {
      content_id: content.id,
      platform: 'LINKEDIN',
      post_type: 'TEXT',
      caption: 'Automated release via Reflow TypeScript SDK!',
    },
    `ts_quickstart_${content.id}`
  );
  console.log(`   Created Publication ID: ${pub.id}`);

  console.log('3. Triggering platform publication dispatch...');
  const dispatch = await client.publications.publish(pub.id);
  console.log(`   Dispatch Job Enqueued: ${dispatch.job_id}`);

  console.log('4. Polling async job completion...');
  const job = await client.jobs.wait(dispatch.job_id, 10000, 1000);
  console.log(`   Job Status: ${job.status}`);

  console.log('Reflow TypeScript SDK Quickstart Workflow Completed Successfully!');
}

runQuickstart().catch((err) => {
  console.error('Quickstart Error:', err);
  process.exit(1);
});
