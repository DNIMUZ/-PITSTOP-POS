// Minimal Cloudflare Worker: serve the Vite SPA from static assets and
// proxy /api/* calls to the hosted backend (works.dev build pipeline).
//
// env.API_BASE     -> live backend origin, e.g. https://api.onrender.com
//                     (set via `vars` in wrangler.jsonc; override per env)
const resolveApi = (env) =>
  (env.API_BASE || "https://YOUR-SERVICE.onrender.com").replace(/\/+$/, "");

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/")) {
      const target = new URL(url.pathname + url.search, resolveApi(env));
      const headers = new Headers(request.headers);
      const init = { method: request.method, headers, redirect: "manual" };
      if (request.method !== "GET" && request.method !== "HEAD") {
        init.body = request.body;
        init.duplex = "half";
      }
      return fetch(new Request(target, init));
    }

    return env.ASSETS.fetch(request);
  },
};