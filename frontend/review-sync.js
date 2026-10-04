/* Keep saved reviews usable while the local server starts or reconnects. */
function backendReviewKey(review) {
  return JSON.stringify([review.date, review.rating, review.favorite, review.improvement]);
}

function localReviewKey(review) {
  if (!review.translationSw) return null;
  return backendReviewKey({
    date: review.date,
    rating: review.stars,
    favorite: review.translationSw.favorite,
    improvement: review.translationSw.improvement,
  });
}

function reviewFromBackend(review) {
  return {
    date: review.date,
    lang: review.original_favorite ? "en" : "sw",
    stars: review.rating,
    favorite: review.original_favorite || review.favorite,
    better: review.original_improvement || review.improvement,
    shareConsent: false,
    translationEn: null,
    translationSw: { favorite: review.favorite, improvement: review.improvement },
    synthetic: Boolean(review.is_demo),
  };
}

function mergeBackendReviews(current, incoming) {
  if (!Array.isArray(incoming)) throw new Error("Invalid review response.");
  // An empty store can belong to a freshly started server. Keep the local copy.
  if (!incoming.length) return current;

  const reviews = current.reviews.filter((review) => !review.fallbackDemo).map((review) => ({ ...review }));
  const matches = new Map();
  reviews.forEach((review, index) => {
    const key = localReviewKey(review);
    if (key === null) return;
    if (!matches.has(key)) matches.set(key, []);
    matches.get(key).push(index);
  });
  let seq = Math.max(current.seq || 0, ...reviews.map((review) => review.seq || 0));
  const ids = new Set(reviews.map((review) => review.id));
  incoming.forEach((review) => {
    const candidates = matches.get(backendReviewKey(review));
    const index = candidates && candidates.length ? candidates.shift() : undefined;
    if (index !== undefined) {
      // Preserve visitor consent, local labels, deletion marks and sequence IDs.
      reviews[index] = { ...reviewFromBackend(review), ...reviews[index], backendSaved: true };
    } else {
      let id;
      do { id = `backend-${++seq}`; } while (ids.has(id));
      ids.add(id);
      reviews.push({ ...reviewFromBackend(review), id, seq, backendSaved: true });
    }
  });
  return { ...current, reviews, seq, pending: 0 };
}

function createReviewSync({ fetchReviews, fetchInsights, updateDb, setInsights, setError, setLoading }) {
  let generation = 0;
  return {
    async refresh() {
      const request = ++generation;
      setLoading(true);
      // Insights may need to load a model. They must never hold up saved reviews.
      Promise.resolve().then(fetchInsights).then((insights) => {
        if (request === generation) setInsights(insights);
      }).catch(() => {
        if (request === generation) setInsights(null);
      });
      try {
        const incoming = await fetchReviews();
        if (!Array.isArray(incoming)) throw new Error("Invalid review response.");
        if (request !== generation) return;
        updateDb((current) => mergeBackendReviews(current, incoming));
        setError(null);
      } catch (error) {
        if (request === generation) setError(error);
      } finally {
        if (request === generation) setLoading(false);
      }
    },
    cancel() { generation += 1; },
  };
}
