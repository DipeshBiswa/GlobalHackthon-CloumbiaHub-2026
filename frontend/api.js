const BACKEND_URL = "http://127.0.0.1:8000";

async function translateReviewWithBackend(review) {
  const response = await fetch(`${BACKEND_URL}/reviews/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      rating: review.stars,
      language: "en",
      date: review.date,
      favorite: review.favorite || "No favorite provided.",
      improvement: review.better || "No improvement provided.",
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Backend translation failed (${response.status}): ${detail}`);
  }
  return response.json();
}
