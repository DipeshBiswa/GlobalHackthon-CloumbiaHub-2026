const BACKEND_URL = "http://127.0.0.1:8000";

async function requestBackend(path, options = {}) {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Backend request failed (${response.status}): ${detail}`);
  }
  return response.json();
}

async function checkBackendHealth() {
  return requestBackend("/health");
}

async function translateReviewWithBackend(review) {
  return requestBackend("/reviews/translate", {
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
  return requestBackend("/reviews/insights");
}
