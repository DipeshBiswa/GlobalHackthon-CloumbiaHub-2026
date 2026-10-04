// Run with: node --test frontend/review-sync.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "review-sync.js"), "utf8");
const { mergeBackendReviews, createReviewSync } = vm.runInNewContext(
  `${source}\n;({ mergeBackendReviews, createReviewSync });`,
);

function backendReview(overrides = {}) {
  return {
    date: "2025-06-08",
    rating: 4,
    favorite: "Nilipenda kahawa.",
    improvement: "Njia iwe wazi zaidi.",
    original_favorite: "I enjoyed the coffee.",
    original_improvement: "The path could be clearer.",
    ...overrides,
  };
}

function savedReview(overrides = {}) {
  const incoming = backendReview();
  return {
    id: "v18",
    seq: 18,
    date: incoming.date,
    stars: incoming.rating,
    lang: "en",
    favorite: incoming.original_favorite,
    better: incoming.original_improvement,
    translationSw: { favorite: incoming.favorite, improvement: incoming.improvement },
    shareConsent: false,
    ...overrides,
  };
}

function database(reviews = [], overrides = {}) {
  return {
    reviews,
    seq: Math.max(0, ...reviews.map((review) => review.seq)),
    plans: [{ id: "plan-1", key: "path:negative", seqAt: 18 }],
    pending: 0,
    lastSeenSeq: 18,
    dashLang: "sw",
    ...overrides,
  };
}

// Objects returned by the browser script live in a separate VM realm.
const snapshot = (value) => JSON.parse(JSON.stringify(value));
const flush = () => new Promise((resolve) => setImmediate(resolve));

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function syncHarness({ db = database(), fetchReviews, fetchInsights }) {
  const state = { db, insights: { cached: true }, error: null, loading: false };
  const writes = [];
  const sync = createReviewSync({
    fetchReviews,
    fetchInsights,
    updateDb: (update) => { state.db = update(state.db); writes.push("db"); },
    setInsights: (value) => { state.insights = value; writes.push("insights"); },
    setError: (value) => { state.error = value; writes.push("error"); },
    setLoading: (value) => { state.loading = value; writes.push("loading"); },
  });
  return { state, writes, ...sync };
}

test("an empty backend response preserves saved reviews and offline demo data", () => {
  const current = database([
    savedReview(),
    savedReview({ id: "demo-1", seq: 1, fallbackDemo: true }),
  ]);
  const result = mergeBackendReviews(current, []);
  assert.deepEqual(snapshot(result.reviews), snapshot(current.reviews));
  assert.equal(result.seq, current.seq);
  assert.deepEqual(snapshot(result.plans), snapshot(current.plans));
  assert.equal(result.dashLang, "sw");
});

test("loaded reviews replace explicit demo rows while preserving absent real reviews", () => {
  const actual = savedReview({ id: "v20", seq: 20, date: "2025-07-01" });
  const cached = savedReview({ id: "backend-19", seq: 19, date: "2025-05-01" });
  const current = database([
    savedReview({ id: "demo-1", seq: 1, fallbackDemo: true }),
    actual,
    cached,
  ]);
  const result = mergeBackendReviews(current, [backendReview()]);
  assert.equal(result.reviews.length, 3);
  assert.ok(!result.reviews.some((review) => review.fallbackDemo));
  assert.deepEqual(snapshot(result.reviews.find((review) => review.id === actual.id)), actual);
  assert.deepEqual(snapshot(result.reviews.find((review) => review.id === cached.id)), cached);
  assert.ok(result.seq >= 20);
});

test("syncing a submitted review retains its identity, moderation and consent", () => {
  const local = savedReview({
    lang: "fr",
    shareConsent: true,
    manualLabels: [{ topic: "path", feeling: "negative", confidence: 1 }],
    checked: true,
    skipped: true,
    deleted: true,
  });
  const current = database([local]);
  const before = snapshot(current);
  const result = mergeBackendReviews(current, [backendReview()]);
  assert.equal(result.reviews.length, 1);
  for (const key of ["id", "seq", "lang", "shareConsent", "checked", "skipped", "deleted"]) {
    assert.equal(result.reviews[0][key], local[key], key);
  }
  assert.deepEqual(snapshot(result.reviews[0].manualLabels), local.manualLabels);
  assert.deepEqual(snapshot(current), before, "merging must not mutate the persisted input");
});

test("backend rows map original text, translations, date and rating to the review UI", () => {
  const english = backendReview();
  const swahili = backendReview({
    date: "2025-07-08", rating: 5, original_favorite: null, original_improvement: null,
  });
  const result = mergeBackendReviews(database(), [english, swahili]);
  const first = result.reviews.find((review) => review.date === english.date);
  const second = result.reviews.find((review) => review.date === swahili.date);
  assert.equal(first.stars, english.rating);
  assert.equal(first.favorite, english.original_favorite);
  assert.equal(first.better, english.original_improvement);
  assert.deepEqual(snapshot(first.translationSw), {
    favorite: english.favorite, improvement: english.improvement,
  });
  assert.equal(second.stars, swahili.rating);
  assert.equal(second.favorite, swahili.favorite);
  assert.equal(second.better, swahili.improvement);
  assert.equal(second.lang, "sw");
  assert.equal(first.shareConsent, false);
});

test("repeated and reordered loads keep stable identities without duplicate reviews", () => {
  const first = backendReview();
  const second = backendReview({ date: "2025-07-08", rating: 5 });
  const loaded = mergeBackendReviews(database([savedReview()]), [first, second]);
  const identities = new Map(loaded.reviews.map((review) => [review.date, [review.id, review.seq]]));
  const refreshed = mergeBackendReviews(loaded, [second, first]);
  const reloaded = mergeBackendReviews(refreshed, [first, second]);
  assert.equal(reloaded.reviews.length, 2);
  for (const review of reloaded.reviews) {
    assert.deepEqual([review.id, review.seq], identities.get(review.date));
  }
});

test("legitimate identical reviews retain multiplicity across repeated loads", () => {
  const incoming = backendReview();
  const current = database([
    savedReview({ id: "v18", seq: 18, checked: true }),
    savedReview({ id: "v19", seq: 19, skipped: true }),
  ]);
  const first = mergeBackendReviews(current, [incoming, incoming]);
  const second = mergeBackendReviews(first, [incoming, incoming, incoming]);
  const third = mergeBackendReviews(second, [incoming, incoming, incoming]);
  assert.equal(first.reviews.length, 2);
  assert.equal(second.reviews.length, 3);
  assert.equal(third.reviews.length, 3);
  assert.equal(new Set(third.reviews.map((review) => review.id)).size, 3);
  assert.equal(third.reviews.find((review) => review.id === "v18").checked, true);
  assert.equal(third.reviews.find((review) => review.id === "v19").skipped, true);
});

test("reviews become available while insights are still loading", async () => {
  const reviews = deferred();
  const insights = deferred();
  const harness = syncHarness({ fetchReviews: () => reviews.promise, fetchInsights: () => insights.promise });
  const refreshing = harness.refresh();
  assert.equal(harness.state.loading, true);
  reviews.resolve([backendReview()]);
  await flush();
  assert.equal(harness.state.db.reviews.length, 1);
  assert.equal(harness.state.loading, false, "review loading should not wait for analysis");
  insights.resolve({ summary: "Coffee is popular" });
  await refreshing;
  await flush();
  assert.deepEqual(harness.state.insights, { summary: "Coffee is popular" });
});

test("failed insights do not discard successfully fetched reviews", async () => {
  const harness = syncHarness({
    fetchReviews: async () => [backendReview()],
    fetchInsights: async () => { throw new Error("Analysis unavailable"); },
  });
  await harness.refresh();
  await flush();
  assert.equal(harness.state.db.reviews.length, 1);
  assert.equal(harness.state.loading, false);
});

test("a failed review fetch keeps cached reviews and exposes a retryable error", async () => {
  const db = database([savedReview()]);
  const failure = new Error("Network unavailable");
  const harness = syncHarness({
    db,
    fetchReviews: async () => { throw failure; },
    fetchInsights: async () => ({ summary: "Cached analysis" }),
  });
  await harness.refresh();
  await flush();
  assert.deepEqual(snapshot(harness.state.db), snapshot(db));
  assert.equal(harness.state.error, failure);
  assert.equal(harness.state.loading, false);
});

test("an older refresh cannot apply reviews or insights after a newer refresh", async () => {
  const oldReviews = deferred();
  const newReviews = deferred();
  const oldInsights = deferred();
  const newInsights = deferred();
  const reviewCalls = [oldReviews, newReviews];
  const insightCalls = [oldInsights, newInsights];
  const harness = syncHarness({
    fetchReviews: () => reviewCalls.shift().promise,
    fetchInsights: () => insightCalls.shift().promise,
  });
  const older = harness.refresh();
  const newer = harness.refresh();
  newReviews.resolve([backendReview({ date: "2025-08-01" })]);
  newInsights.resolve({ version: "new" });
  await newer;
  await flush();
  oldReviews.resolve([backendReview({ date: "2025-01-01" })]);
  oldInsights.resolve({ version: "old" });
  await older;
  await flush();
  assert.deepEqual(snapshot(harness.state.db.reviews.map((review) => review.date)), ["2025-08-01"]);
  assert.deepEqual(harness.state.insights, { version: "new" });
  assert.equal(harness.state.error, null);
});

test("failure of an obsolete refresh does not stop loading or show a stale error", async () => {
  const oldReviews = deferred();
  const newReviews = deferred();
  const reviewCalls = [oldReviews, newReviews];
  const harness = syncHarness({
    fetchReviews: () => reviewCalls.shift().promise,
    fetchInsights: async () => ({}),
  });
  const older = harness.refresh();
  const newer = harness.refresh();
  oldReviews.reject(new Error("Old request failed"));
  await older;
  await flush();
  assert.equal(harness.state.error, null);
  assert.equal(harness.state.loading, true);
  newReviews.resolve([backendReview()]);
  await newer;
  assert.equal(harness.state.loading, false);
  assert.equal(harness.state.db.reviews.length, 1);
});

test("cancel prevents in-flight requests from changing the reset database", async () => {
  const reviews = deferred();
  const insights = deferred();
  const harness = syncHarness({ fetchReviews: () => reviews.promise, fetchInsights: () => insights.promise });
  const refreshing = harness.refresh();
  harness.cancel();
  const writesAfterCancel = harness.writes.length;
  reviews.resolve([backendReview()]);
  insights.resolve({ obsolete: true });
  await refreshing;
  await flush();
  assert.equal(harness.state.db.reviews.length, 0);
  assert.equal(harness.writes.length, writesAfterCancel);
  assert.deepEqual(harness.state.insights, { cached: true });
});

test("a new refresh succeeds after cancellation", async () => {
  const harness = syncHarness({
    fetchReviews: async () => [backendReview()],
    fetchInsights: async () => ({ recovered: true }),
  });
  harness.cancel();
  await harness.refresh();
  await flush();
  assert.equal(harness.state.db.reviews.length, 1);
  assert.deepEqual(harness.state.insights, { recovered: true });
});

test("local submissions made during a fetch survive its eventual response", async () => {
  const reviews = deferred();
  const harness = syncHarness({ fetchReviews: () => reviews.promise, fetchInsights: async () => ({}) });
  const refreshing = harness.refresh();
  const submitted = savedReview({ id: "v24", seq: 24, date: "2025-08-01", shareConsent: true });
  harness.state.db = database([submitted]);
  reviews.resolve([backendReview()]);
  await refreshing;
  assert.equal(harness.state.db.reviews.length, 2);
  assert.deepEqual(snapshot(harness.state.db.reviews.find((review) => review.id === submitted.id)), submitted);
  assert.ok(harness.state.db.seq >= 24);
});
