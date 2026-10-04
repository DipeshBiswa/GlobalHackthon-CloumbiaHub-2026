const BACKEND_URL = "http://127.0.0.1:8000";

async function requestBackend(path, options = {}) {
  const { timeoutMs = 15000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${BACKEND_URL}${path}`, {
      ...fetchOptions,
      headers: { "Content-Type": "application/json", ...(fetchOptions.headers || {}) },
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Backend request failed (${response.status}): ${detail}`);
    }
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

async function checkBackendHealth() {
  return requestBackend("/health");
}

async function translateReviewWithBackend(review) {
  return requestBackend("/reviews/translate", {
    timeoutMs: 120000,
    method: "POST",
    body: JSON.stringify({
      rating: review.stars,
      language: "en",
      date: review.date,
      favorite: review.favorite || "No favorite provided.",
      improvement: review.better || "No improvement provided.",
    }),
  });
}

async function translateReviewsBatchWithBackend(reviews) {
  return requestBackend("/reviews/translate/batch", {
    timeoutMs: 600000,
    method: "POST",
    body: JSON.stringify({
      reviews: reviews.map((review) => ({
        rating: review.stars,
        language: "en",
        date: review.date,
        favorite: review.favorite || "No favorite provided.",
        improvement: review.better || "No improvement provided.",
      })),
    }),
  });
}

async function getTranslatedReviewsFromBackend() {
  return requestBackend("/reviews/translated");
}

async function getInsightsFromBackend() {
  return requestBackend("/reviews/insights", { timeoutMs: 120000 });
}
