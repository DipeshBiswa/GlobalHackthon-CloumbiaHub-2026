/* Localhost only. Serve through FastAPI or the documented local proxy server. */
window.EchoAPI = (() => {
  async function request(path, method = "GET", body) {
    const response = await fetch("/api" + path, { method, credentials: "same-origin",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body) });
    const result = await response.json();
    if (!response.ok) {
      const detail = result.detail;
      const error = new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map(x => x.msg).join("; ") : detail?.message || "Local request failed.");
      error.status = response.status; error.retryAfter = detail?.retry_after || 0;
      throw error;
    }
    return result;
  }
  return {
    login: (username, password) => request("/auth/login", "POST", { username, password }),
    signup: (username, password, display_name) => request("/auth/signup", "POST", { username, password, display_name }),
    logout: () => request("/auth/logout", "POST"), me: () => request("/auth/me"),
    unlock: pin => request("/pin/unlock", "POST", { pin }), lock: () => request("/pin/lock", "POST"),
    submitReview: body => request("/reviews", "POST", body),
    getReviews: (filter = "all") => request("/reviews?filter=" + encodeURIComponent(filter) + "&include_deleted=true"),
    deleteReview: id => request(`/reviews/${id}`, "DELETE"), restoreReview: id => request(`/reviews/${id}/restore`, "PATCH"),
    seen: () => request("/reviews/seen", "POST"), getDashboard: () => request("/dashboard"),
    getSuggestions: () => request("/suggestions"), getKnowledge: () => request("/knowledge"),
    decide: (key, ignored) => request("/suggestions/decision", "POST", {key, ignored}),
    getPlans: () => request("/plans"), createPlan: body => request("/plans", "POST", body),
    updatePlan: (id, status) => request(`/plans/${id}`, "PATCH", {status}),
    deletePlan: id => request(`/plans/${id}`, "DELETE"),
    getMonthlyPerformance: month => request("/performance/monthly?month=" + month),
    getNotSureReviews: () => request("/reviews?filter=not_sure"),
    updateClassification: (id, body) => request(`/reviews/${id}/classification`, "PATCH", body),
  };
})();
