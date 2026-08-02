import { config } from "./config/env.js";
import { createApp } from "./app.js";
import { initializeDatabase } from "./db/index.js";

const { seedResult } = initializeDatabase();

if (seedResult.skipped) {
  console.log(`Using existing database at ${config.databasePath}`);
} else {
  console.log(
    `Seeded ${seedResult.seeded} synthetic refund requests into ${config.databasePath}`,
  );
}

createApp().listen(config.port, () => {
  console.log(`Refunds API listening on http://localhost:${config.port}`);
  console.log(`Finance approval threshold: $${config.approvalThresholdAmount}`);
});
