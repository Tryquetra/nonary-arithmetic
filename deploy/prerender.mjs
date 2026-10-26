// Prerender step: replaces the two runtime dependencies of the article.
//
//   1. Tailwind Play CDN  -> compiled CSS, inlined
//   2. MathJax from a CDN -> static CHTML markup, generated here with the
//      same engine the page used at runtime, so the rendering is identical
//      while the browser downloads no JavaScript for math.
//
// Input:  index.html (authoring source, unchanged)
// Output: <outdir>/index.html plus the MathJax webfonts it needs.

import { readFileSync, writeFileSync, mkdirSync, copyFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

import { mathjax } from "mathjax-full/js/mathjax.js";
import { TeX } from "mathjax-full/js/input/tex.js";
import { CHTML } from "mathjax-full/js/output/chtml.js";
import { liteAdaptor } from "mathjax-full/js/adaptors/liteAdaptor.js";
import { RegisterHTMLHandler } from "mathjax-full/js/handlers/html.js";
import { AssistiveMmlHandler } from "mathjax-full/js/a11y/assistive-mml.js";
import { AllPackages } from "mathjax-full/js/input/tex/AllPackages.js";

const SRC = "index.html";
const OUT_DIR = process.argv[2] ?? "dist/nonary-ternary-bridge-conversion";
const FONT_DIR = "node_modules/mathjax-full/es5/output/chtml/fonts/woff-v2";
const FONT_URL = "fonts/woff-v2";

mkdirSync(OUT_DIR, { recursive: true });

const adaptor = liteAdaptor();
// Assistive MathML keeps the screen-reader copy of every expression, which is
// what the runtime MathJax build added on the client.
AssistiveMmlHandler(RegisterHTMLHandler(adaptor));

const tex = new TeX({ packages: AllPackages });
// matchFontHeight measures the surrounding font at render time, which would
// bake this machine's font metrics into the output. Disabled here and replaced
// by the two font-size rules below, measured from the rendered page: body text
// is Georgia at 103.9%, headings are Inter at 123.5%.
const chtml = new CHTML({ fontURL: FONT_URL, matchFontHeight: false });
const doc = mathjax.document("", { InputJax: tex, OutputJax: chtml });

let html = readFileSync(SRC, "utf8");

// ---------------------------------------------------------------- math ----
// Protect the code block so dollar signs inside Python never reach TeX.
const codeBlocks = [];
html = html.replace(/<pre[\s\S]*?<\/pre>/g, (m) => {
  codeBlocks.push(m);
  return `\u0000CODE${codeBlocks.length - 1}\u0000`;
});

// Math bodies are captured from HTML, so entities such as &lt; and &amp;
// must be decoded before TeX sees them.
const decode = (s) =>
  s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
   .replace(/&#39;/g, "'").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");

let count = 0;

// Display math first: $$...$$ and \[...\]
html = html.replace(/\$\$([\s\S]+?)\$\$/g, (_, body) => {
  count += 1;
  return adaptor.outerHTML(doc.convert(decode(body).trim(), { display: true }));
});
html = html.replace(/\\\[([\s\S]+?)\\\]/g, (_, body) => {
  count += 1;
  return adaptor.outerHTML(doc.convert(decode(body).trim(), { display: true }));
});

// Inline math: $...$ and \(...\)
html = html.replace(/\$([^$\n]+?)\$/g, (_, body) => {
  count += 1;
  return adaptor.outerHTML(doc.convert(decode(body), { display: false }));
});
html = html.replace(/\\\(([\s\S]+?)\\\)/g, (_, body) => {
  count += 1;
  return adaptor.outerHTML(doc.convert(decode(body), { display: false }));
});

html = html.replace(/\u0000CODE(\d+)\u0000/g, (_, i) => codeBlocks[Number(i)]);

// adaptiveCSS means the sheet only covers expressions already converted, so it
// must be read after every conversion has happened.
const css =
  adaptor.textContent(chtml.styleSheet(doc)) +
  "\nmjx-container{font-size:103.9%}" +
  "\nh1 mjx-container,h2 mjx-container,h3 mjx-container{font-size:123.5%}\n";

// ------------------------------------------------------------ tailwind ----
// Compile against the prerendered HTML so every class the page uses is kept.
writeFileSync(join(OUT_DIR, ".prerendered.html"), html);
execFileSync(
  "bunx",
  ["tailwindcss@3.4.17", "-i", "deploy/tailwind.css", "-o", join(OUT_DIR, ".tailwind.css"),
   "--content", join(OUT_DIR, ".prerendered.html"), "--minify"],
  { stdio: ["ignore", "pipe", "inherit"] },
);
const tailwind = readFileSync(join(OUT_DIR, ".tailwind.css"), "utf8");

// ------------------------------------------------------------- assemble ---
// Drop the CDN Tailwind script and the MathJax loader/config; inline both CSS
// payloads in their place so the document renders with zero JS.
html = html.replace(
  /[ \t]*<script src="https:\/\/cdn\.tailwindcss\.com"><\/script>\n?/,
  `    <style>${tailwind}</style>\n`,
);
html = html.replace(
  /[ \t]*<!-- MathJax Configuration -->[\s\S]*?<script id="MathJax-script" async src="[^"]*"><\/script>\n?/,
  `    <style>${css}</style>\n`,
);

// Self-host Inter: one preloaded variable file replaces the Google Fonts
// stylesheet and its three network round trips.
html = html.replace(
  /[ \t]*<link href="https:\/\/fonts\.googleapis\.com[^>]*>\n?/,
  `    <link rel="preload" href="fonts/inter-latin-wght.woff2" as="font" type="font/woff2" crossorigin>\n` +
  `    <style>@font-face{font-family:'Inter';font-style:normal;font-weight:100 900;font-display:swap;src:url(fonts/inter-latin-wght.woff2) format('woff2')}</style>\n`,
);

// No third-party origin is needed any more.
html = html.replace(/[ \t]*<link rel="preconnect" href="https:\/\/cdn\.jsdelivr\.net"[^>]*>\n?/, "");

writeFileSync(join(OUT_DIR, "index.html"), html);

// Self-hosted Inter.
mkdirSync(join(OUT_DIR, "fonts"), { recursive: true });
copyFileSync("assets/inter-latin-wght.woff2", join(OUT_DIR, "fonts/inter-latin-wght.woff2"));

// Fonts referenced by the CHTML stylesheet.
mkdirSync(join(OUT_DIR, FONT_URL), { recursive: true });
for (const f of readdirSync(FONT_DIR)) {
  copyFileSync(join(FONT_DIR, f), join(OUT_DIR, FONT_URL, f));
}

console.log(`prerendered ${count} expressions`);
console.log(`tailwind css ${(tailwind.length / 1024).toFixed(1)} KiB, mathjax css ${(css.length / 1024).toFixed(1)} KiB`);
