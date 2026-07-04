import React, { useState, useEffect, useRef } from "react";
import { 
  Bot, ShieldCheck, Play, Square, RefreshCw, 
  Settings, Terminal, Database, Users, Smartphone,
  Film, HelpCircle, CheckCircle2, AlertTriangle, Key
} from "lucide-react";

export default function App() {
  const [botStatus, setBotStatus] = useState<{ isRunning: boolean; pid: number | null; hasToken: boolean }>({
    isRunning: false,
    pid: null,
    hasToken: false
  });
  const [dbStats, setDbStats] = useState({ usersCount: 0, userbotsCount: 0, downloadsCount: 0, complaintsCount: 0 });
  const [logs, setLogs] = useState<string[]>([]);
  const [botToken, setBotToken] = useState("");
  const [adminIds, setAdminIds] = useState("");
  const [activeTab, setActiveTab] = useState<"dashboard" | "logs" | "settings" | "userbot">("dashboard");
  const [loading, setLoading] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");
  const logContainerRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    try {
      const [statusRes, statsRes, envRes, logsRes] = await Promise.all([
        fetch("/api/bot/status").then(r => r.json()),
        fetch("/api/db/stats").then(r => r.json()),
        fetch("/api/env").then(r => r.json()),
        fetch("/api/bot/logs").then(r => r.json())
      ]);

      setBotStatus(statusRes);
      setDbStats(statsRes);
      if (!botToken) setBotToken(envRes.botToken);
      if (!adminIds) setAdminIds(envRes.adminIds);
      setLogs(logsRes.logs || []);
    } catch (e) {
      console.error("Fetch data error:", e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleStartBot = async () => {
    setLoading(true);
    await fetch("/api/bot/start", { method: "POST" });
    await fetchData();
    setLoading(false);
  };

  const handleStopBot = async () => {
    setLoading(true);
    await fetch("/api/bot/stop", { method: "POST" });
    await fetchData();
    setLoading(false);
  };

  const handleSaveEnv = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await fetch("/api/env", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ botToken, adminIds })
    });
    setSavedMessage("Sozlamalar saqlandi!");
    setTimeout(() => setSavedMessage(""), 3000);
    await fetchData();
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Bar Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
            <Film className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              MovieBot & Userbot Boshqaruv Paneli
            </h1>
            <p className="text-xs text-slate-400">
              UzMovie, Asilmedia scraper va Userbot bilan 50MB+ yuklash tizimi
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
            botStatus.isRunning 
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" 
              : "bg-amber-500/10 text-amber-400 border-amber-500/30"
          }`}>
            <span className={`w-2 h-2 rounded-full ${botStatus.isRunning ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
            <span>{botStatus.isRunning ? "Bot Ishlamoqda" : "Bot To'xtatilgan"}</span>
          </div>

          {botStatus.isRunning ? (
            <button
              onClick={handleStopBot}
              disabled={loading}
              className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition shadow"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>To'xtatish</span>
            </button>
          ) : (
            <button
              onClick={handleStartBot}
              disabled={loading || !botStatus.hasToken}
              className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition shadow"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Ishga Tushirish</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Content Body */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col space-y-6">
        
        {/* Navigation Tabs */}
        <div className="flex space-x-2 border-b border-slate-800 pb-3">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition ${
              activeTab === "dashboard" ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-900"
            }`}
          >
            <Bot className="w-4 h-4" />
            <span>Asosiy Statistika</span>
          </button>

          <button
            onClick={() => setActiveTab("userbot")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition ${
              activeTab === "userbot" ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-900"
            }`}
          >
            <Smartphone className="w-4 h-4" />
            <span>Userbot Yo'riqnomasi</span>
          </button>

          <button
            onClick={() => setActiveTab("logs")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition ${
              activeTab === "logs" ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-900"
            }`}
          >
            <Terminal className="w-4 h-4" />
            <span>Konsole Loglari</span>
          </button>

          <button
            onClick={() => setActiveTab("settings")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition ${
              activeTab === "settings" ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-900"
            }`}
          >
            <Settings className="w-4 h-4" />
            <span>Sozlamalar (.env)</span>
          </button>
        </div>

        {/* TAB 1: DASHBOARD */}
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            {!botStatus.hasToken && (
              <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-xs space-y-1 text-amber-200">
                  <p className="font-bold">Bot Token kiritilmagan!</p>
                  <p>Botni ishga tushirish uchun "Sozlamalar" bo'limidan <b>BOT_TOKEN</b> va <b>ADMIN_IDS</b> kiriting.</p>
                </div>
              </div>
            )}

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">Jami Foydalanuvchilar</span>
                  <Users className="w-4 h-4 text-indigo-400" />
                </div>
                <p className="text-2xl font-bold text-white">{dbStats.usersCount}</p>
              </div>

              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">Ulangan Userbotlar</span>
                  <Smartphone className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-2xl font-bold text-white">{dbStats.userbotsCount}</p>
              </div>

              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">Yuklab Olishlar</span>
                  <Film className="w-4 h-4 text-sky-400" />
                </div>
                <p className="text-2xl font-bold text-white">{dbStats.downloadsCount}</p>
              </div>

              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">Ochiq Shikoyatlar</span>
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                </div>
                <p className="text-2xl font-bold text-white">{dbStats.complaintsCount}</p>
              </div>
            </div>

            {/* Quick Bot Features Summary */}
            <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>MovieBot Mukammallashgan Imkoniyatlari</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
                  <p className="font-bold text-indigo-400">🎬 Kinolarni Avto-Parse qilish</p>
                  <p className="text-slate-400">Asilmedia, UzMovie, UzMovi.tv, Kinolar.tv va to'g'ridan to'g'ri MP4/MKV havolalarini avto skanerlaydi.</p>
                </div>

                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
                  <p className="font-bold text-emerald-400">🔐 Userbot 50MB+ Yuklash</p>
                  <p className="text-slate-400">50MB dan katta bo'lgan fayllar (2GB gacha) foydalanuvchining o'z Userbot (Telethon) accountingiz orqali yuklanadi.</p>
                </div>

                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
                  <p className="font-bold text-sky-400">👑 HTML Admin Panel</p>
                  <p className="text-slate-400">Telegram ichida /admin buyrug'i orqali foydalanuvchilar, to'lovlar, majburiy obuna va kartalarni boshqarish.</p>
                </div>

                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
                  <p className="font-bold text-purple-400">📦 Telegram Storage Kanal</p>
                  <p className="text-slate-400">Bir marta yuklangan kinolar storage kanalga saqlanib, keyingi so'rovlarda zudlik bilan forward qilinadi.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: USERBOT GUIDE */}
        {activeTab === "userbot" && (
          <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg">
                <Smartphone className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Userbot Ulanish Yo'riqnomasi</h2>
                <p className="text-xs text-slate-400">50MB dan katta fayllarni yuborish uchun foydalanuvchi bot ichida Userbot layotini ulaydi</p>
              </div>
            </div>

            <div className="space-y-4 text-xs text-slate-300">
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <p className="font-bold text-white text-sm">1. Telegram botda buyruq yuboring:</p>
                <code className="block p-2 bg-slate-900 rounded text-emerald-400 font-mono text-xs">/connect_api</code>
              </div>

              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <p className="font-bold text-white text-sm">2. API ID va API Hash oling:</p>
                <p className="text-slate-400">
                  Foydalanuvchi <a href="https://my.telegram.org" target="_blank" rel="noreferrer" className="text-indigo-400 underline">my.telegram.org</a> ga kirib, <b>API development tools</b> bo'limidan <b>api_id</b> va <b>api_hash</b> oladi.
                </p>
              </div>

              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <p className="font-bold text-white text-sm">3. Telefon va Tasdiqlash Kodi:</p>
                <p className="text-slate-400">
                  Bot bosqichma-bosqich telefon raqam va SMS/Telegram kodini so'raydi. (2FA bo'lsa parolni ham qabul qiladi).
                </p>
              </div>

              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300">
                ✅ Telethon StringSession SQLite ma'lumotlar bazasida xavfsiz saqlanadi va katta kinolarni yuklashda avto qo'llaniladi.
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: LOGS */}
        {activeTab === "logs" && (
          <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center space-x-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <span>Jonli Telegram Bot Konsoli</span>
              </h2>
              <button
                onClick={fetchData}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs flex items-center space-x-1"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Yangilash</span>
              </button>
            </div>

            <div
              ref={logContainerRef}
              className="p-4 bg-slate-950 font-mono text-xs text-emerald-400 rounded-xl border border-slate-800 h-96 overflow-y-auto space-y-1"
            >
              {logs.length === 0 ? (
                <p className="text-slate-600">Hozircha konsolda loglar yo'q...</p>
              ) : (
                logs.map((log, index) => (
                  <p key={index} className={log.includes("[BOT-ERR]") ? "text-rose-400" : "text-emerald-400"}>
                    {log}
                  </p>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 4: SETTINGS */}
        {activeTab === "settings" && (
          <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg">
                <Key className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Bot Sozlamalari (.env)</h2>
                <p className="text-xs text-slate-400">@BotFather bergan Telegram Bot Token va Admin ID larini kiritish</p>
              </div>
            </div>

            <form onSubmit={handleSaveEnv} className="space-y-4 max-w-xl">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">BOT_TOKEN (Telegram Bot Token)</label>
                <input
                  type="text"
                  value={botToken}
                  onChange={(e) => setBotToken(e.target.value)}
                  placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">ADMIN_IDS (Admin Telegram ID lari)</label>
                <input
                  type="text"
                  value={adminIds}
                  onChange={(e) => setAdminIds(e.target.value)}
                  placeholder="123456789, 987654321"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              {savedMessage && (
                <p className="text-xs text-emerald-400 font-medium">{savedMessage}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition"
              >
                Sozlamalarni Saqlash
              </button>
            </form>
          </div>
        )}

      </div>
    </div>
  );
}
