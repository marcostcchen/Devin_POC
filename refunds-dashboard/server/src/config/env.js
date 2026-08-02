import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const serverRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
);

dotenv.config({ path: path.join(serverRoot, ".env") });

function readNumber(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;

  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    throw new Error(
      `Environment variable ${name} must be numeric, received "${raw}"`,
    );
  }
  return parsed;
}

// Set by the POC platform when it supervises this app (see ../../../poc.yaml and
// poc-platform/docs/platform-contract.md); absent when running standalone.
const platformManaged = process.env.PLATFORM_MANAGED === "1";
const platformDataDir = process.env.PLATFORM_DATA_DIR ?? "";

// Under the platform the API also serves the built client, so the whole
// prototype is one process behind one origin instead of an API plus a Vite
// dev server the gateway would have to route separately.
const clientDist = path.resolve(serverRoot, "..", "client", "dist");

export const config = {
  serverRoot,
  port: readNumber("PORT", 4000),
  clientOrigin: process.env.CLIENT_ORIGIN ?? "http://localhost:5173",
  databasePath: path.resolve(
    platformDataDir || serverRoot,
    process.env.DATABASE_PATH ?? "./data/refunds.db",
  ),
  approvalThresholdAmount: readNumber("APPROVAL_THRESHOLD_AMOUNT", 200),
  seedRequestCount: readNumber("SEED_REQUEST_COUNT", 23),
  platformManaged,
  platformBasePath: (process.env.PLATFORM_BASE_PATH ?? "").replace(/\/$/, ""),
  serveClient: process.env.SERVE_CLIENT === "true" || platformManaged,
  clientDist,
};
