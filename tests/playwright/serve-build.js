// Static server for Playwright: serves ./build under the GitHub Pages prefix
// (/metroverse-jobs/), like the hosted site. No dependencies.
//   node tests/playwright/serve-build.js [port]
const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.argv[2] || 3001);
const PREFIX = "/metroverse-jobs";
const ROOT = path.resolve(__dirname, "..", "..", "build");
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".ico": "image/x-icon",
  ".txt": "text/plain",
};

http
  .createServer((req, res) => {
    const urlPath = decodeURIComponent(req.url.split("?")[0]);
    if (urlPath === PREFIX) {
      res.writeHead(301, { Location: PREFIX + "/" });
      return res.end();
    }
    if (!urlPath.startsWith(PREFIX + "/")) {
      res.writeHead(404);
      return res.end("Not found");
    }
    let file = path.join(ROOT, urlPath.slice(PREFIX.length));
    if (!file.startsWith(ROOT)) {
      res.writeHead(403);
      return res.end();
    }
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
      file = path.join(file, "index.html");
    }
    fs.readFile(file, (err, data) => {
      if (err) {
        res.writeHead(404);
        return res.end("Not found");
      }
      res.writeHead(200, {
        "Content-Type": TYPES[path.extname(file).toLowerCase()] || "application/octet-stream",
      });
      res.end(data);
    });
  })
  .listen(PORT, () => console.log(`Serving ${ROOT} at http://localhost:${PORT}${PREFIX}/`));
