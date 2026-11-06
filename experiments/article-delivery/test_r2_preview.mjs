import assert from "node:assert/strict";
import test from "node:test";
import worker from "./r2-preview.mjs";

const originalCaches = globalThis.caches;
function setup() {
  const store = new Map();
  globalThis.caches = {default: {
    match: async (key) => store.get(key.url)?.clone(),
    put: async (key, value) => { store.set(key.url, value.clone()); }
  }};
  const keys = [];
  const env = {ARTICLE_HTML_BUCKET: {get: async key => {
    keys.push(key);
    return {text: async () => "<!doctype html><html><body>Preview</body></html>"};
  }}};
  const ctx = {waitUntil: promise => promise};
  return {keys,env,ctx};
}
test.after(() => {globalThis.caches = originalCaches;});

test("English category article maps to exact R2 key", async () => {
  const {keys,env,ctx} = setup();
  const response = await worker.fetch(new Request("https://preview.example/en/news/sports/test-123/"),env,ctx);
  assert.equal(response.status,200);
  assert.deepEqual(keys,["en/news/sports/test-123/index.html"]);
  assert.match(await response.text(), /Preview/);
});
test("Hindi article HEAD returns headers without body", async () => {
  const {keys,env,ctx} = setup();
  const response = await worker.fetch(new Request("https://preview.example/hi/news/technology/test-456/",{method:"HEAD"}),env,ctx);
  assert.equal(response.status,200);
  assert.equal(await response.text(),"");
  assert.deepEqual(keys,["hi/news/technology/test-456/index.html"]);
});
test("unmatched path is not handled", async () => {
  const {env,ctx} = setup();
  assert.equal((await worker.fetch(new Request("https://preview.example/en/"),env,ctx)).status,404);
});
test("unconfigured bucket fails closed", async () => {
  const {ctx} = setup();
  assert.equal((await worker.fetch(new Request("https://preview.example/en/news/sports/test/"),{},ctx)).status,503);
});
