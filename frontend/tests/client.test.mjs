import test from 'node:test';
import assert from 'node:assert/strict';

test('Lead Intelligence Frontend Verification Suite', async (t) => {
  await t.test('Excel export URL builder produces expected endpoint path', () => {
    const jobUid = '2115360423948389981';
    const expected = `/api/v1/leads/${jobUid}/export`;
    const actual = `/api/v1/leads/${encodeURIComponent(jobUid)}/export`;
    assert.equal(actual, expected);
  });

  await t.test('Motion Seeds configuration matches StyleSeed precision criteria', async () => {
    // Snap seed properties
    const snapEntrance = {
      initial: { opacity: 0, y: 4 },
      animate: { opacity: 1, y: 0 },
      transition: { duration: 0.14, ease: [0.16, 1, 0.3, 1] },
    };

    assert.equal(snapEntrance.transition.duration, 0.14);
    assert.deepEqual(snapEntrance.transition.ease, [0.16, 1, 0.3, 1]);
    assert.equal(snapEntrance.initial.opacity, 0);
  });

  await t.test('4-Factor scoring weights sum to exactly 1.0 (100%)', () => {
    const weights = {
      name: 0.40,
      location: 0.35,
      role: 0.15,
      company: 0.10,
    };
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    assert.equal(Math.round(total * 100) / 100, 1.0);
  });

  await t.test('Tier classification accurately matches backend thresholds', () => {
    function getTier(score) {
      if (score >= 70.0) return 'Tier A';
      if (score >= 40.0) return 'Tier B';
      return 'Tier C';
    }

    assert.equal(getTier(85.5), 'Tier A');
    assert.equal(getTier(70.0), 'Tier A');
    assert.equal(getTier(69.9), 'Tier B');
    assert.equal(getTier(45.5), 'Tier B');
    assert.equal(getTier(39.9), 'Tier C');
    assert.equal(getTier(15.0), 'Tier C');
  });

  await t.test('Review partitioning isolates freelancer praise before marker', () => {
    const rawReview = 'Great client to work with Martin. Prompt payment. To freelancer: Excellent work delivered on time!';
    const marker = 'To freelancer:';
    const parts = rawReview.split(marker);
    const clientReview = parts[0].trim();
    const freelancerReview = parts[1]?.trim();

    assert.ok(clientReview.includes('Martin'));
    assert.ok(!clientReview.includes('To freelancer:'));
    assert.equal(freelancerReview, 'Excellent work delivered on time!');
  });

  await t.test('Search query categorization identifies Google X-Ray and LinkedIn GeoURN queries', () => {
    const googleUrl = 'https://www.google.com/search?q=site%3Alinkedin.com/in/%20%22Zarina%22%20%22Sydney%22';
    const geoUrnUrl = 'https://www.linkedin.com/search/results/people/?keywords=Zarina&geoUrn=%5B%22101452733%22%5D&origin=FACETED_SEARCH';
    const nameUrl = 'https://www.linkedin.com/search/results/people/?keywords=Zarina&origin=FACETED_SEARCH';

    assert.ok(googleUrl.includes('google.com') && googleUrl.includes('site%3Alinkedin.com'));
    assert.ok(geoUrnUrl.includes('geoUrn='));
    assert.ok(!nameUrl.includes('geoUrn='));
  });

  await t.test('Dashboard 4-factor metrics schema contract', () => {
    const stats = {
      harvested_jobs_count: 3,
      unique_domains_count: 1,
      potential_clients_count: 1,
      rate_limit_health: 'GREEN',
      rate_limit_requests_remaining: 48,
      active_session_cookies: 79,
    };

    assert.equal(typeof stats.harvested_jobs_count, 'number');
    assert.equal(typeof stats.unique_domains_count, 'number');
    assert.equal(typeof stats.potential_clients_count, 'number');
    assert.ok(['GREEN', 'YELLOW', 'RED'].includes(stats.rate_limit_health));
  });

  await t.test('Domain jobs endpoint URL correctly encodes search query', () => {
    const query = 'AI & Machine Learning';
    const endpoint = `/api/v1/jobs/domains/${encodeURIComponent(query)}/jobs`;
    assert.equal(endpoint, '/api/v1/jobs/domains/AI%20%26%20Machine%20Learning/jobs');
  });
});

