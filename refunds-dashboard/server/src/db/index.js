import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { config } from "../config/env.js";
import { createSchema } from "./schema.js";
import { seedRefundRequests } from "./seed.js";

let database;

/** Opens (creating if needed) the SQLite database, applies schema and seed data. */
export function initializeDatabase({
  databasePath = config.databasePath,
  seedCount = config.seedRequestCount,
} = {}) {
  fs.mkdirSync(path.dirname(databasePath), { recursive: true });

  database = new Database(databasePath);
  database.pragma("journal_mode = WAL");
  database.pragma("foreign_keys = ON");

  createSchema(database);
  const seedResult = seedRefundRequests(database, seedCount);

  return { database, seedResult };
}

export function getDatabase() {
  if (!database) {
    throw new Error(
      "Database has not been initialized. Call initializeDatabase() first.",
    );
  }
  return database;
}

export function closeDatabase() {
  if (database) {
    database.close();
    database = undefined;
  }
}
