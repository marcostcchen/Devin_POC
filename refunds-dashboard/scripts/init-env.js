import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// Copies each `.env.example` to `.env` on first setup so the app runs with
// working defaults without committing environment files to git.
const projectRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const envTargets = ["server", "client"];

for (const target of envTargets) {
  const examplePath = join(projectRoot, target, ".env.example");
  const envPath = join(projectRoot, target, ".env");

  if (!existsSync(examplePath)) {
    console.warn(`No .env.example found for "${target}", skipping.`);
    continue;
  }

  if (existsSync(envPath)) {
    console.log(`${target}/.env already exists, leaving it untouched.`);
    continue;
  }

  mkdirSync(dirname(envPath), { recursive: true });
  copyFileSync(examplePath, envPath);
  console.log(`Created ${target}/.env from .env.example`);
}
