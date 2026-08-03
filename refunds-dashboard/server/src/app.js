import fs from "node:fs";
import path from "node:path";
import cors from "cors";
import express from "express";
import { config } from "./config/env.js";
import { currentActor } from "./middleware/currentActor.js";
import { errorHandler, notFoundHandler } from "./middleware/errorHandler.js";
import { apiRoutes } from "./routes/index.js";

export function createApp() {
  const app = express();

  app.use(cors({ origin: config.clientOrigin }));
  app.use(express.json());

  // Readiness probe for the POC platform supervisor, which checks it on the
  // app's own port. Kept outside the mount point and ahead of identity so a
  // malformed role header cannot make the app look unhealthy.
  app.get("/healthz", (req, res) => {
    res.json({
      status: "ok",
      app: "refunds-dashboard",
      platformManaged: config.platformManaged,
    });
  });

  // Under the platform the gateway forwards the mount prefix as-is, so the app
  // lives at /apps/refunds-dashboard/...; standalone the prefix is empty.
  const mounted = express.Router();
  mounted.use(currentActor);
  mounted.use("/api", apiRoutes);

  if (config.serveClient && fs.existsSync(config.clientDist)) {
    const indexFile = path.join(config.clientDist, "index.html");
    mounted.use(express.static(config.clientDist));
    // SPA fallback for anything that is not an API route or a real file.
    mounted.get(/^(?!\/api\/).*/, (req, res, next) => {
      res.sendFile(indexFile, (error) => (error ? next(error) : undefined));
    });
  }

  app.use(config.platformBasePath || "/", mounted);
  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
