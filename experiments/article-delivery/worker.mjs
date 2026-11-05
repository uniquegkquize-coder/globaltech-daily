/**
 * GlobeWire Daily — isolated article-delivery proof of concept.
 * NOT deployed or routed to production. Do not enable before load/SEO testing.
 *
 * Requests: /en/news/<slug>/ or /hi/news/<slug>/
 * Source: existing, committed dist HTML (no article deletion or URL rewriting).
 * Raw GitHub is a prototype origin only; production requires a durable origin.
 */
const BASE = "https://raw.githubusercontent.com/uniquegkquize-coder/globaltech-daily/main/dist";
const ARTICLE_PATH = /^\/(en|hi)\/news\/([a-zA-Z0-9][a-zA-Z0-9-]{0,180})\/$/;
export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", {status:405, headers:{"Allow":"GET, HEAD"}});
    }
    const url = new URL(request.url);
    const match = url.pathname.match(ARTICLE_PATH);
    if (!match) return new Response("Not Found", {status:404});
    const originUrl = BASE + url.pathname + "index.html";
    const cache = caches.default;
    const key = new Request(originUrl, {method:"GET"});
    let response = await cache.match(key);
    if (!response) {
      const upstream = await fetch(originUrl, {redirect:"follow", cf:{cacheTtl:300, cacheEverything:true}});
      if (!upstream.ok) return new Response("Article unavailable", {status:upstream.status === 404 ? 404 : 503});
      const html = await upstream.text();
      if (!html.toLowerCase().includes("<html")) return new Response("Invalid article response", {status:502});
      response = new Response(html, {status:200, headers:{"Content-Type":"text/html; charset=utf-8","Cache-Control":"public, max-age=60, s-maxage=300","X-Content-Type-Options":"nosniff"}});
      await cache.put(key, response.clone());
    }
    return request.method === "HEAD" ? new Response(null,{status:response.status,headers:response.headers}) : response;
  }
};
