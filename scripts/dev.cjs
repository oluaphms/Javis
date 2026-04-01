/**
 * Sobe Vite e o backend Node em paralelo (sem dependência extra).
 * Uso: node scripts/dev.cjs
 */
const { spawn } = require("child_process");
const path = require("path");

const root = path.join(__dirname, "..");
const shell = process.platform === "win32";

// Comandos em uma única string evitam aviso DEP0190 com shell no Windows.
const vite = spawn("npx vite", {
  stdio: "inherit",
  shell,
  cwd: root,
  env: process.env,
});

const api = spawn("npm run backend", {
  stdio: "inherit",
  shell,
  cwd: root,
  env: process.env,
});

function shutdown(code = 0) {
  try {
    vite.kill("SIGTERM");
  } catch (_) {}
  try {
    api.kill("SIGTERM");
  } catch (_) {}
  process.exit(code);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

vite.on("exit", (code) => {
  try {
    api.kill("SIGTERM");
  } catch (_) {}
  process.exit(code ?? 0);
});

api.on("exit", (code) => {
  try {
    vite.kill("SIGTERM");
  } catch (_) {}
  process.exit(code ?? 0);
});
