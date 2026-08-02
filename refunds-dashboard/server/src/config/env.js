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

export const config = {
  serverRoot,
  port: readNumber("PORT", 4000),
  clientOrigin: process.env.CLIENT_ORIGIN ?? "http://localhost:5173",
  databasePath: path.resolve(
    serverRoot,
    process.env.DATABASE_PATH ?? "./data/refunds.db",
  ),
  approvalThresholdAmount: readNumber("APPROVAL_THRESHOLD_AMOUNT", 200),
  seedRequestCount: readNumber("SEED_REQUEST_COUNT", 23),
};
