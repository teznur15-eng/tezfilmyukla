import express from "express";
import path from "path";
import fs from "fs";
import { spawn, ChildProcess } from "child_process";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;

app.use(express.json());

let botProcess: ChildProcess | null = null;
let botLogs: string[] = [];

function addLog(msg: string) {
  const time = new Date().toLocaleTimeString();
  const line = `[${time}] ${msg}`;
  botLogs.push(line);
  if (botLogs.length > 200) {
    botLogs.shift();
  }
}

function startPythonBot() {
  if (botProcess) {
    addLog("Bot is already running.");
    return false;
  }

  addLog("Starting MovieBot (main.py)...");
  botProcess = spawn("python3", ["main.py"], {
    env: { ...process.env },
    cwd: process.cwd()
  });

  botProcess.stdout?.on("data", (data) => {
    const text = data.toString().trim();
    if (text) {
      addLog(`[BOT] ${text}`);
    }
  });

  botProcess.stderr?.on("data", (data) => {
    const text = data.toString().trim();
    if (text) {
      addLog(`[BOT-ERR] ${text}`);
    }
  });

  botProcess.on("exit", (code, signal) => {
    addLog(`Bot process exited with code ${code}, signal ${signal}`);
    botProcess = null;
  });

  botProcess.on("error", (err) => {
    addLog(`Failed to start bot process: ${err.message}`);
    botProcess = null;
  });

  return true;
}

function stopPythonBot() {
  if (!botProcess) {
    addLog("Bot is not running.");
    return false;
  }
  addLog("Stopping MovieBot process...");
  botProcess.kill("SIGTERM");
  botProcess = null;
  return true;
}

// Automatically try starting python bot if BOT_TOKEN is present in env
if (process.env.BOT_TOKEN && process.env.BOT_TOKEN !== "YOUR_TELEGRAM_BOT_TOKEN_HERE") {
  setTimeout(() => {
    startPythonBot();
  }, 1000);
}

// ─── API ROUTES ───────────────────────────────────────────────

app.get("/api/bot/status", (req, res) => {
  res.json({
    isRunning: botProcess !== null,
    pid: botProcess?.pid || null,
    hasToken: Boolean(process.env.BOT_TOKEN && process.env.BOT_TOKEN !== "YOUR_TELEGRAM_BOT_TOKEN_HERE")
  });
});

app.post("/api/bot/start", (req, res) => {
  const started = startPythonBot();
  res.json({ success: started, isRunning: botProcess !== null });
});

app.post("/api/bot/stop", (req, res) => {
  const stopped = stopPythonBot();
  res.json({ success: stopped, isRunning: botProcess !== null });
});

app.get("/api/bot/logs", (req, res) => {
  res.json({ logs: botLogs });
});

app.get("/api/env", (req, res) => {
  res.json({
    botToken: process.env.BOT_TOKEN || "",
    adminIds: process.env.ADMIN_IDS || ""
  });
});

app.post("/api/env", (req, res) => {
  const { botToken, adminIds } = req.body;
  
  if (botToken !== undefined) process.env.BOT_TOKEN = botToken;
  if (adminIds !== undefined) process.env.ADMIN_IDS = adminIds;

  // Update .env file
  try {
    const envPath = path.join(process.cwd(), ".env");
    let envContent = "";
    if (fs.existsSync(envPath)) {
      envContent = fs.readFileSync(envPath, "utf-8");
    }

    if (botToken !== undefined) {
      if (envContent.includes("BOT_TOKEN=")) {
        envContent = envContent.replace(/BOT_TOKEN=.* /g, `BOT_TOKEN="${botToken}"`);
      } else {
        envContent += `\nBOT_TOKEN="${botToken}"\n`;
      }
    }

    if (adminIds !== undefined) {
      if (envContent.includes("ADMIN_IDS=")) {
        envContent = envContent.replace(/ADMIN_IDS=.*/g, `ADMIN_IDS="${adminIds}"`);
      } else {
        envContent += `\nADMIN_IDS="${adminIds}"\n`;
      }
    }

    fs.writeFileSync(envPath, envContent, "utf-8");
    addLog("Updated .env file with new credentials.");
  } catch (err) {
    addLog(`Failed to update .env: ${(err as Error).message}`);
  }

  res.json({ success: true });
});

// SQLite data reader for web dashboard
app.get("/api/db/stats", async (req, res) => {
  const sqlite3 = await import("sqlite3");
  const dbPath = path.join(process.cwd(), "moviebot.db");
  
  if (!fs.existsSync(dbPath)) {
    return res.json({ usersCount: 0, userbotsCount: 0, downloadsCount: 0, complaintsCount: 0 });
  }

  const db = new sqlite3.default.Database(dbPath);
  db.get("SELECT COUNT(*) as uc FROM users", [], (err, uRow: any) => {
    db.get("SELECT COUNT(*) as ubc FROM userbot_sessions", [], (err, ubRow: any) => {
      db.get("SELECT COUNT(*) as dc FROM downloads", [], (err, dRow: any) => {
        db.get("SELECT COUNT(*) as cc FROM complaints WHERE status = 'open'", [], (err, cRow: any) => {
          db.close();
          res.json({
            usersCount: uRow?.uc || 0,
            userbotsCount: ubRow?.ubc || 0,
            downloadsCount: dRow?.dc || 0,
            complaintsCount: cRow?.cc || 0
          });
        });
      });
    });
  });
});

// ─── VITE / STATIC MIDDLEWARE ──────────────────────────────────

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
