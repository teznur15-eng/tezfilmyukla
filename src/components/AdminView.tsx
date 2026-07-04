import React, { useState } from 'react';
import { useApp } from '../AppContext';
import { Movie, User, Card, Ad, Receipt, AppConfig, MovieCategory } from '../types';
import { 
  Tv, Users, CreditCard, Megaphone, FileText, Palette, MessageSquare, 
  Settings, Plus, Trash2, Check, X, ShieldAlert, Edit, Eye, Sparkles, 
  Activity, ExternalLink, RefreshCw, Send
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function AdminView() {
  const { 
    movies, addMovie, deleteMovie,
    users, updateUser, deleteUser, setUserBlockedStatus, setUserRole, grantManualVip,
    cards, addCard, updateCard, deleteCard,
    receipts, approveReceipt, rejectReceipt,
    ads, addAd, deleteAd, updateAd,
    chats, addChatMessage, clearChat,
    config, updateConfig
  } = useApp();

  const [activeSubTab, setActiveSubTab] = useState<'movies' | 'subscribers' | 'finance' | 'ads' | 'users' | 'copyright' | 'branding' | 'chats' | 'bot_settings'>('movies');

  // --- 1. Movie Upload Form State ---
  const [newMovie, setNewMovie] = useState({
    title: '',
    year: 2026,
    genre: '',
    code: '',
    description: '',
    category: 'kino' as MovieCategory,
    imageUrl: '',
    link720: '',
    link1080: ''
  });

  // --- 2. Live Bank Card Form State ---
  const [newCard, setNewCard] = useState({
    holder: '',
    number: '',
    bank: '',
    isActive: true
  });

  // --- 3. Live Advertisement Form State ---
  const [newAd, setNewAd] = useState({
    title: '',
    type: 'telegram' as 'google' | 'telegram',
    content: '',
    imageUrl: '',
    isActive: true
  });

  // --- 4. Chat support state ---
  const [selectedUserChatId, setSelectedUserChatId] = useState<string>('');
  const [adminReplyText, setAdminReplyText] = useState('');

  // --- 5. Branding colors picker ---
  const [primaryColor, setPrimaryColor] = useState(config.primaryColor);
  const [logoUrl, setLogoUrl] = useState(config.logoUrl);

  // --- 6. Bot parameters ---
  const [newMandatoryChannel, setNewMandatoryChannel] = useState('');

  // Handle movie submission
  const handleMovieSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMovie.title || !newMovie.code || !newMovie.link720 || !newMovie.link1080) {
      alert('Iltimos barcha majburiy maydonlarni to\'ldiring!');
      return;
    }
    
    // Check if code already exists
    if (movies.some(m => m.code === newMovie.code)) {
      alert(`"${newMovie.code}" kodli film allaqachon mavjud! Iltimos boshqa kod tanlang.`);
      return;
    }

    addMovie({
      title: newMovie.title,
      year: Number(newMovie.year),
      genre: newMovie.genre || 'Tafsilotlar yo\'q',
      code: newMovie.code,
      description: newMovie.description || 'Tafsilotlar kiritilmagan.',
      category: newMovie.category,
      imageUrl: newMovie.imageUrl || 'https://images.unsplash.com/photo-1594909122845-11baa439b7bf?auto=format&fit=crop&w=600&q=80',
      link720: newMovie.link720,
      link1080: newMovie.link1080,
      rating: 8.0 // default
    });

    alert('Kino muvaffaqiyatli yuklandi va qidiruv bazasiga qo\'shildi!');
    
    // Reset form
    setNewMovie({
      title: '',
      year: 2026,
      genre: '',
      code: '',
      description: '',
      category: 'kino',
      imageUrl: '',
      link720: '',
      link1080: ''
    });
  };

  // Handle Card Submission
  const handleCardSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCard.number || !newCard.bank || !newCard.holder) return;
    addCard(newCard);
    setNewCard({ holder: '', number: '', bank: '', isActive: true });
    alert('Yangi to\'lov kartasi muvaffaqiyatli qo\'shildi!');
  };

  // Handle Ad Submission
  const handleAdSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAd.title || !newAd.content) return;
    addAd(newAd);
    setNewAd({ title: '', type: 'telegram', content: '', imageUrl: '', isActive: true });
    alert('Yangi reklama kampaniyasi yaratildi!');
  };

  // Handle Admin Message Reply
  const handleAdminChatReply = (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminReplyText.trim() || !selectedUserChatId) return;

    const targetUser = users.find(u => u.id === selectedUserChatId);
    
    addChatMessage(
      selectedUserChatId,
      targetUser ? targetUser.name : 'Foydalanuvchi',
      adminReplyText.trim(),
      'admin'
    );
    
    setAdminReplyText('');
  };

  // Handle logo and color config change
  const handleBrandingSave = (e: React.FormEvent) => {
    e.preventDefault();
    updateConfig({
      ...config,
      primaryColor,
      logoUrl
    });
    alert('Bot va Sayt dizayni muvaffaqiyatli yangilandi!');
  };

  const handleAddMandatoryChannel = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMandatoryChannel.trim()) return;
    if (config.mandatoryChannels.includes(newMandatoryChannel.trim())) return;
    updateConfig({
      ...config,
      mandatoryChannels: [...config.mandatoryChannels, newMandatoryChannel.trim()]
    });
    setNewMandatoryChannel('');
  };

  const handleRemoveMandatoryChannel = (channelName: string) => {
    updateConfig({
      ...config,
      mandatoryChannels: config.mandatoryChannels.filter(c => c !== channelName)
    });
  };

  // Filter chats users (unique user ID lists having messages)
  const chatUsers = Array.from(new Set(chats.map(c => c.userId))).map(id => {
    return users.find(u => u.id === id) || { id, name: 'Noma\'lum Foydalanuvchi', isOnline: false, role: 'user' };
  });

  return (
    <div className="flex flex-col md:flex-row h-full bg-slate-900 text-slate-100 font-sans overflow-hidden">
      
      {/* Sidebar navigation */}
      <aside className="w-full md:w-64 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-800 flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-500" style={{ color: config.primaryColor }} />
          <span className="font-black text-xs uppercase tracking-widest text-slate-300">Admin Panel</span>
        </div>

        <nav className="flex-1 overflow-y-auto p-2 space-y-1">
          {[
            { id: 'movies', label: '🎬 Kinolar yuklash', icon: Tv },
            { id: 'subscribers', label: '🌟 VIP foydalanuvchilar', icon: Sparkles },
            { id: 'finance', label: '💳 Moliya (Cheklar)', icon: CreditCard },
            { id: 'ads', label: '📢 Reklama', icon: Megaphone },
            { id: 'users', label: '👥 Foydalanuvchilar', icon: Users },
            { id: 'copyright', label: '⚖️ Mualliflik huquqi', icon: FileText },
            { id: 'branding', label: '🎨 Bot dizayni', icon: Palette },
            { id: 'chats', label: '💬 Chatlar suhbatlari', icon: MessageSquare },
            { id: 'bot_settings', label: '⚙️ Bot sozlamalari', icon: Settings },
          ].map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSubTab(item.id as any)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left text-xs font-semibold transition ${activeSubTab === item.id ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20' : 'text-slate-400 hover:text-white hover:bg-slate-900/50'}`}
                style={activeSubTab === item.id ? { color: config.primaryColor, borderColor: `${config.primaryColor}20`, backgroundColor: `${config.primaryColor}10` } : {}}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Workspace Panel */}
      <main className="flex-1 overflow-y-auto p-6 bg-slate-900/50">
        <AnimatePresence mode="wait">
          
          {/* 1. MOVIES UPLOAD FORM TAB */}
          {activeSubTab === 'movies' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">Kino yuklash sahifasi</h2>
                  <p className="text-xs text-slate-400">Yangi filmlar va seriallarni yuklash va bot qidiruviga kod qo'shish.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Form column */}
                <form onSubmit={handleMovieSubmit} className="lg:col-span-2 bg-slate-950 border border-slate-800 p-6 rounded-3xl space-y-4 text-xs">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Film Nomi *</label>
                      <input 
                        type="text" 
                        required
                        placeholder="Masalan: Qasoskorlar: Intihosi"
                        value={newMovie.title}
                        onChange={(e) => setNewMovie({...newMovie, title: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Yuklangan Yili *</label>
                      <input 
                        type="number" 
                        required
                        value={newMovie.year}
                        onChange={(e) => setNewMovie({...newMovie, year: Number(e.target.value)})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Janr (Vergul bilan) *</label>
                      <input 
                        type="text" 
                        required
                        placeholder="Masalan: Triller, Drama, Sarguzasht"
                        value={newMovie.genre}
                        onChange={(e) => setNewMovie({...newMovie, genre: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Kino Kodi (Unikal son) *</label>
                      <input 
                        type="text" 
                        required
                        placeholder="Masalan: 2334"
                        value={newMovie.code}
                        onChange={(e) => setNewMovie({...newMovie, code: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Film Toifasi *</label>
                      <select
                        value={newMovie.category}
                        onChange={(e) => setNewMovie({...newMovie, category: e.target.value as MovieCategory})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-300 focus:outline-none"
                      >
                        <option value="kino">Film / Kino</option>
                        <option value="serial">Serial</option>
                        <option value="kdrama">KDrama (Koreys)</option>
                        <option value="turk">Turk Seriali</option>
                        <option value="anime">Anime</option>
                        <option value="multfilm">Multfilm</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Poster Rasm Link (Card rasm) *</label>
                      <input 
                        type="url" 
                        placeholder="Unsplash yoki rasm manzili linki"
                        value={newMovie.imageUrl}
                        onChange={(e) => setNewMovie({...newMovie, imageUrl: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Oddiy 720p Video Link (Bepul foydalanuvchi) *</label>
                    <input 
                      type="url" 
                      required
                      placeholder="HD 720p mp4 video file manzili"
                      value={newMovie.link720}
                      onChange={(e) => setNewMovie({...newMovie, link720: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Premium 1080p Video Link (Faqat VIP a'zo) *</label>
                    <input 
                      type="url" 
                      required
                      placeholder="FHD 1080p premium mp4 video file manzili"
                      value={newMovie.link1080}
                      onChange={(e) => setNewMovie({...newMovie, link1080: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Film Syujeti (Tafsilotlar)</label>
                    <textarea 
                      rows={4}
                      placeholder="Ushbu film haqida qisqacha ma'lumot kiriting..."
                      value={newMovie.description}
                      onChange={(e) => setNewMovie({...newMovie, description: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none"
                    />
                  </div>

                  <button 
                    type="submit"
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 font-bold text-white rounded-xl transition cursor-pointer text-xs"
                    style={{ backgroundColor: config.primaryColor }}
                  >
                    Kinoni bazaga qo'shish (Upload) 🎬
                  </button>
                </form>

                {/* Previews / Quick list */}
                <div className="bg-slate-950 border border-slate-800 p-4 rounded-3xl h-[550px] flex flex-col">
                  <h3 className="font-bold text-xs text-slate-400 block mb-3 uppercase">Mavjud kinolar ro'yxati ({movies.length})</h3>
                  <div className="flex-1 overflow-y-auto space-y-2.5 text-xs pr-1">
                    {movies.map(movie => (
                      <div key={movie.id} className="bg-slate-900 border border-slate-800 p-2.5 rounded-xl flex items-center justify-between gap-3 shadow">
                        <div className="flex items-center gap-2 max-w-[70%]">
                          <img src={movie.imageUrl} alt={movie.title} className="w-9 h-12 object-cover rounded-md" referrerPolicy="no-referrer" />
                          <div className="truncate">
                            <h4 className="font-bold text-xs truncate text-white">{movie.title}</h4>
                            <span className="text-[9px] text-indigo-400 block font-mono">Kodi: {movie.code} | {movie.category}</span>
                          </div>
                        </div>
                        <button 
                          onClick={() => {
                            if (confirm(`Rostdan ham "${movie.title}" filmini o'chirmoqchimisiz?`)) {
                              deleteMovie(movie.id);
                            }
                          }}
                          className="p-1.5 rounded-lg bg-red-600/10 hover:bg-red-600 text-red-500 hover:text-white transition cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* 2. VIP SUBSCRIBERS MANAGEMENT TAB */}
          {activeSubTab === 'subscribers' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">VIP Obunachilar Bo'limi</h2>
                <p className="text-xs text-slate-400">VIP obuna olgan foydalanuvchilar holati, muddatini boshqarish va cheklash.</p>
              </div>

              {/* Table / List */}
              <div className="bg-slate-950 border border-slate-800 rounded-3xl overflow-hidden shadow">
                <div className="overflow-x-auto text-xs">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/50 text-[10px] font-bold text-slate-400 uppercase">
                        <th className="p-4">Ism / Email</th>
                        <th className="p-4">Roli</th>
                        <th className="p-4">VIP Muddat</th>
                        <th className="p-4">Holat</th>
                        <th className="p-4">Taqiq (Blok)</th>
                        <th className="p-4 text-right">Amallar</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-medium">
                      {users.map(user => {
                        const isVip = user.vipUntil && new Date(user.vipUntil) > new Date();
                        const expiry = user.vipUntil ? new Date(user.vipUntil).toLocaleDateString('uz-UZ') : 'Yo\'q';
                        return (
                          <tr key={user.id} className="hover:bg-slate-900/20">
                            <td className="p-4">
                              <div className="flex items-center gap-2.5">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-white bg-slate-800 border ${isVip ? 'border-amber-500 text-amber-400' : 'border-slate-700'}`}>
                                  {user.name.substring(0,2).toUpperCase()}
                                </div>
                                <div>
                                  <div className="font-bold text-slate-200">{user.name}</div>
                                  <div className="text-[10px] text-slate-500 font-mono">{user.email}</div>
                                </div>
                              </div>
                            </td>
                            <td className="p-4">
                              <span className="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-slate-800 text-slate-400">
                                {user.role}
                              </span>
                            </td>
                            <td className="p-4 font-mono">
                              {isVip ? (
                                <span className="text-amber-400 font-bold flex items-center gap-1">
                                  <Sparkles className="w-3.5 h-3.5 fill-current" /> {expiry}
                                </span>
                              ) : (
                                <span className="text-slate-500">Oddiy foydalanuvchi</span>
                              )}
                            </td>
                            <td className="p-4">
                              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${user.isOnline ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${user.isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                                {user.isOnline ? 'Online' : 'Offline'}
                              </span>
                            </td>
                            <td className="p-4">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${user.isBlocked ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
                                {user.isBlocked ? 'Taqiqlangan' : 'Ruxsat berilgan'}
                              </span>
                            </td>
                            <td className="p-4 text-right space-x-1.5">
                              <button 
                                onClick={() => setUserBlockedStatus(user.id, !user.isBlocked)}
                                className={`px-2 py-1 rounded text-[10px] font-bold transition cursor-pointer ${user.isBlocked ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'bg-red-600 hover:bg-red-500 text-white'}`}
                              >
                                {user.isBlocked ? 'Blokdan ochish' : 'Bloklash'}
                              </button>
                              <button 
                                onClick={() => grantManualVip(user.id, 30)}
                                className="px-2 py-1 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-[10px] transition cursor-pointer"
                              >
                                +30 kun VIP
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.div>
          )}

          {/* 3. FINANCE & RECEIPT VERIFICATION TAB */}
          {activeSubTab === 'finance' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Moliya (To'lov cheklarini tekshirish)</h2>
                <p className="text-xs text-slate-400">Telegram botdan kelgan VIP to'lov cheklarini tekshirish, VIP berish va to'lov kartalarini tahrirlash.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Receipts validation list */}
                <div className="lg:col-span-2 space-y-4">
                  <h3 className="font-bold text-xs text-slate-400 uppercase tracking-wider">Yuborilgan to'lov cheklari</h3>
                  
                  {receipts.length === 0 ? (
                    <div className="bg-slate-950 border border-slate-800 rounded-3xl py-12 text-center text-slate-500 text-xs">
                      Hozircha tekshirilmagan to'lov cheklari mavjud emas.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {receipts.map(receipt => (
                        <div key={receipt.id} className="bg-slate-950 border border-slate-800 p-4 rounded-3xl flex flex-col sm:flex-row gap-4 justify-between shadow">
                          
                          <div className="flex gap-3">
                            {/* receipt visual screenshot thumbnail */}
                            <a href={receipt.imageUrl} target="_blank" rel="noreferrer" className="w-20 h-28 border border-slate-800 rounded-xl overflow-hidden bg-slate-900 shrink-0 group relative cursor-zoom-in">
                              <img src={receipt.imageUrl} alt="Chek" className="w-full h-full object-cover group-hover:opacity-80 transition" referrerPolicy="no-referrer" />
                              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center text-[10px] text-white">Ko'rish</div>
                            </a>

                            <div className="space-y-1 text-xs">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-200">{receipt.userName}</span>
                                <span className="text-[10px] text-slate-500">#{receipt.id.substring(8)}</span>
                              </div>
                              <p className="text-slate-400">Yuborilgan karta: <span className="font-mono text-indigo-400">{receipt.cardNumber}</span></p>
                              <p className="text-slate-400">To'lov miqdori: <span className="font-mono font-black text-amber-400">{receipt.amount.toLocaleString()} so'm</span></p>
                              <p className="text-[10px] text-slate-500 font-mono">Sana: {new Date(receipt.createdAt).toLocaleString('uz-UZ')}</p>
                              
                              <div className="pt-2">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${receipt.status === 'pending' ? 'bg-amber-500/10 text-amber-400' : receipt.status === 'approved' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                                  {receipt.status}
                                </span>
                              </div>
                            </div>
                          </div>

                          {receipt.status === 'pending' && (
                            <div className="flex sm:flex-col justify-end gap-2 text-xs shrink-0 pt-3 sm:pt-0">
                              <button 
                                onClick={() => approveReceipt(receipt.id)}
                                className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold text-white flex items-center gap-1.5 shadow transition cursor-pointer"
                              >
                                <Check className="w-4 h-4" /> Chekni tasdiqlash
                              </button>
                              <button 
                                onClick={() => rejectReceipt(receipt.id)}
                                className="px-3.5 py-2 rounded-xl bg-red-600 hover:bg-red-500 font-bold text-white flex items-center gap-1.5 shadow transition cursor-pointer"
                              >
                                <X className="w-4 h-4" /> Bekor qilish
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Cards Setup column */}
                <div className="space-y-4">
                  <h3 className="font-bold text-xs text-slate-400 uppercase tracking-wider">To'lov kartalari</h3>
                  
                  {/* Create Card Form */}
                  <form onSubmit={handleCardSubmit} className="bg-slate-950 border border-slate-800 p-4 rounded-3xl space-y-3 text-xs">
                    <h4 className="font-bold text-slate-300">Yangi Karta qo'shish</h4>
                    
                    <div>
                      <label className="text-[9px] font-bold text-slate-400 block mb-0.5 uppercase">Karta raqami</label>
                      <input 
                        type="text" 
                        required
                        placeholder="8600 1204 5678 9012"
                        value={newCard.number}
                        onChange={(e) => setNewCard({...newCard, number: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-2 text-white font-mono"
                      />
                    </div>

                    <div>
                      <label className="text-[9px] font-bold text-slate-400 block mb-0.5 uppercase">Karta Egasi Ismi</label>
                      <input 
                        type="text" 
                        required
                        placeholder="XALQ BANKI (Sardor T.)"
                        value={newCard.holder}
                        onChange={(e) => setNewCard({...newCard, holder: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-2 text-white"
                      />
                    </div>

                    <div>
                      <label className="text-[9px] font-bold text-slate-400 block mb-0.5 uppercase">Bank / Tizim</label>
                      <input 
                        type="text" 
                        required
                        placeholder="Masalan: TBC Bank, Uzcard"
                        value={newCard.bank}
                        onChange={(e) => setNewCard({...newCard, bank: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-2 text-white"
                      />
                    </div>

                    <button 
                      type="submit"
                      className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 font-bold text-white rounded-xl transition cursor-pointer text-xs"
                      style={{ backgroundColor: config.primaryColor }}
                    >
                      Kartani qo'shish
                    </button>
                  </form>

                  {/* List of active Cards */}
                  <div className="space-y-2">
                    {cards.map(card => (
                      <div key={card.id} className="bg-slate-950 border border-slate-800 p-3 rounded-2xl flex items-center justify-between gap-3 text-xs">
                        <div>
                          <h4 className="font-bold text-slate-200">{card.bank}</h4>
                          <p className="font-mono text-indigo-400 mt-0.5">{card.number}</p>
                          <span className="text-[9px] text-slate-500">Egasi: {card.holder}</span>
                        </div>
                        <div className="flex gap-1.5">
                          <button 
                            onClick={() => updateCard({...card, isActive: !card.isActive})}
                            className={`px-2 py-1 rounded text-[9px] font-bold ${card.isActive ? 'bg-emerald-600/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'}`}
                          >
                            {card.isActive ? 'Faol' : 'Nofaol'}
                          </button>
                          <button 
                            onClick={() => deleteCard(card.id)}
                            className="p-1.5 rounded bg-red-600/10 hover:bg-red-600 text-red-500 hover:text-white transition cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </motion.div>
          )}

          {/* 4. ADVERTISEMENT MANAGEMENT TAB */}
          {activeSubTab === 'ads' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Reklama Boshqaruvi</h2>
                <p className="text-xs text-slate-400">Google Ads yoki telegram ichki reklama bannerlarini joylashtirish, tahrirlash va o'chirish. VIP foydalanuvchilarga reklama ko'rsatilmaydi!</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Create Ad Form */}
                <form onSubmit={handleAdSubmit} className="bg-slate-950 border border-slate-800 p-5 rounded-3xl space-y-4 text-xs">
                  <h3 className="font-bold text-slate-300">Yangi Reklama Banneri</h3>
                  
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Sarlavha (Kompaniya nomi)</label>
                    <input 
                      type="text" 
                      required
                      placeholder="Masalan: Pepsi Yangi Yil Tanlovi"
                      value={newAd.title}
                      onChange={(e) => setNewAd({...newAd, title: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-white"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Reklama Toifasi</label>
                    <select
                      value={newAd.type}
                      onChange={(e) => setNewAd({...newAd, type: e.target.value as any})}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-slate-300"
                    >
                      <option value="telegram">Telegram kanal reklamasi</option>
                      <option value="google">Google sayt banneri</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Rasm URL (ixtiyoriy)</label>
                    <input 
                      type="url" 
                      placeholder="Rasm manzili (banner)"
                      value={newAd.imageUrl}
                      onChange={(e) => setNewAd({...newAd, imageUrl: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-white"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Reklama Matni (Kontent)</label>
                    <textarea 
                      rows={4}
                      required
                      placeholder="Reklama mazmunini batafsil yozing..."
                      value={newAd.content}
                      onChange={(e) => setNewAd({...newAd, content: e.target.value})}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-white"
                    />
                  </div>

                  <button 
                    type="submit"
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 font-bold text-white rounded-xl transition text-xs cursor-pointer"
                    style={{ backgroundColor: config.primaryColor }}
                  >
                    Reklamani joylash 📢
                  </button>
                </form>

                {/* Ads List Grid */}
                <div className="lg:col-span-2 space-y-4">
                  <h3 className="font-bold text-xs text-slate-400 uppercase tracking-wider">Mavjud reklama kampaniyalari ({ads.length})</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {ads.map(ad => (
                      <div key={ad.id} className="bg-slate-950 border border-slate-800 p-4 rounded-3xl space-y-3 flex flex-col justify-between shadow">
                        <div className="space-y-2 text-xs">
                          <div className="flex items-center justify-between gap-2">
                            <span className="px-2 py-0.5 rounded bg-indigo-600/10 text-indigo-400 text-[10px] font-bold uppercase" style={{ color: config.primaryColor }}>
                              {ad.type}
                            </span>
                            <span className="font-mono text-[10px] text-slate-500">
                              👁️ {ad.impressions} ta taassurot
                            </span>
                          </div>
                          
                          <h4 className="font-bold text-slate-200">{ad.title}</h4>
                          <p className="text-slate-400 leading-relaxed font-normal">{ad.content}</p>
                          {ad.imageUrl && (
                            <img src={ad.imageUrl} alt="Ad poster" className="w-full h-24 object-cover rounded-xl border border-slate-800" referrerPolicy="no-referrer" />
                          )}
                        </div>

                        <div className="flex items-center justify-between border-t border-slate-800/60 pt-3 mt-2 text-xs">
                          <button 
                            onClick={() => updateAd({...ad, isActive: !ad.isActive})}
                            className={`px-3 py-1 rounded-xl text-[10px] font-bold transition ${ad.isActive ? 'bg-emerald-600/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-500'}`}
                          >
                            {ad.isActive ? 'Faol ko\'rsatilmoqda' : 'To\'xtatilgan'}
                          </button>
                          
                          <button 
                            onClick={() => deleteAd(ad.id)}
                            className="p-1.5 rounded-lg bg-red-600/10 hover:bg-red-600 text-red-500 hover:text-white transition cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </motion.div>
          )}

          {/* 5. USERS CREDENTIALS & DELEGATIONS TAB */}
          {activeSubTab === 'users' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Foydalanuvchilar & Tizim Rollari</h2>
                <p className="text-xs text-slate-400">Owner, Admin, va oddiy a'zolarga rollar berish, ruxsatlar boshqaruvi.</p>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-3xl overflow-hidden shadow text-xs">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/50 text-[10px] font-bold text-slate-400 uppercase">
                      <th className="p-4">Foydalanuvchi</th>
                      <th className="p-4">Roli</th>
                      <th className="p-4">Balansi</th>
                      <th className="p-4 text-right">Amal (Roli va Ruxsatlar)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {users.map(user => (
                      <tr key={user.id} className="hover:bg-slate-900/10">
                        <td className="p-4">
                          <div className="font-bold text-slate-200">{user.name}</div>
                          <span className="text-[10px] text-slate-500 font-mono">{user.email}</span>
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${user.role === 'owner' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : user.role === 'admin' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'bg-slate-800 text-slate-400'}`}>
                            {user.role}
                          </span>
                        </td>
                        <td className="p-4 font-mono font-bold">{user.balance.toLocaleString()} so'm</td>
                        <td className="p-4 text-right space-x-1">
                          <button 
                            disabled={user.role === 'owner'}
                            onClick={() => setUserRole(user.id, 'admin')}
                            className="px-2.5 py-1 rounded bg-indigo-600/10 text-indigo-400 hover:bg-indigo-600 hover:text-white font-bold text-[10px] disabled:opacity-50 transition cursor-pointer"
                          >
                            Admin qilish
                          </button>
                          <button 
                            disabled={user.role === 'owner'}
                            onClick={() => setUserRole(user.id, 'user')}
                            className="px-2.5 py-1 rounded bg-slate-800 text-slate-400 hover:text-white font-bold text-[10px] disabled:opacity-50 transition cursor-pointer"
                          >
                            User qilish
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {/* 6. COPYRIGHT TEXT EDITOR TAB */}
          {activeSubTab === 'copyright' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 max-w-xl">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Mualliflik Huquqi tushuntirishlari</h2>
                <p className="text-xs text-slate-400">Sayt footer matni, mualliflik huquqlari tushuntirishlari va pichat kabi rasmiy ma'lumotlarni tahrirlash.</p>
              </div>

              <div className="bg-slate-950 border border-slate-800 p-6 rounded-3xl space-y-4 text-xs">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Mualliflik huquqi va bog'lanish matni</label>
                  <textarea 
                    rows={6}
                    value={config.copyrightText}
                    onChange={(e) => updateConfig({...config, copyrightText: e.target.value})}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-white leading-relaxed"
                  />
                </div>

                <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl flex items-center gap-3">
                  <ShieldAlert className="w-5 h-5 text-indigo-500 shrink-0" style={{ color: config.primaryColor }} />
                  <p className="text-[11px] text-slate-400">Ushbu ma'lumotlar foydalanuvchilarning "Profil" sahifasining mualliflik huquqi tushuntirish qismida avtomatik ravishda aks etadi.</p>
                </div>
              </div>
            </motion.div>
          )}

          {/* 7. BRANDING (COLORS, LOGO) EDITOR TAB */}
          {activeSubTab === 'branding' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 max-w-xl">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Bot & Sayt dizayni (Branding)</h2>
                <p className="text-xs text-slate-400">Sayt va botning asosiy vizual rang sxemasini va logotip manzillarini tahrirlash.</p>
              </div>

              <form onSubmit={handleBrandingSave} className="bg-slate-950 border border-slate-800 p-6 rounded-3xl space-y-4 text-xs">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Asosiy Rang (Hex Code)</label>
                  <div className="flex gap-3 items-center">
                    <input 
                      type="color" 
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-10 h-10 rounded bg-transparent border border-slate-800 cursor-pointer shrink-0"
                    />
                    <input 
                      type="text" 
                      required
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Logo URL (Sarlavha ikonkasi)</label>
                  <input 
                    type="url" 
                    required
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white"
                  />
                </div>

                <button 
                  type="submit"
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 font-bold text-white rounded-xl transition text-xs cursor-pointer"
                  style={{ backgroundColor: config.primaryColor }}
                >
                  Dizaynni saqlash 🎨
                </button>
              </form>
            </motion.div>
          )}

          {/* 8. SUPPORT CHATS & MESSAGES TAB */}
          {activeSubTab === 'chats' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Chatlar va Suhbatlar (Support)</h2>
                <p className="text-xs text-slate-400">Bot foydalanuvchilaridan kelgan murojaat va savollarga admin panel orqali javob berish.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Users chat list queue */}
                <div className="bg-slate-950 border border-slate-800 rounded-3xl p-4 h-[480px] flex flex-col">
                  <h3 className="font-bold text-xs text-slate-400 block mb-3 uppercase">Faol suhbatlar</h3>
                  <div className="flex-1 overflow-y-auto space-y-2 text-xs pr-1">
                    {chatUsers.length === 0 ? (
                      <div className="h-full flex items-center justify-center text-slate-500 text-center">
                        Hozircha suhbatlar mavjud emas.
                      </div>
                    ) : (
                      chatUsers.map(u => (
                        <button
                          key={u.id}
                          onClick={() => setSelectedUserChatId(u.id)}
                          className={`w-full text-left p-3 rounded-xl border flex items-center justify-between transition ${selectedUserChatId === u.id ? 'bg-indigo-600/10 border-indigo-500' : 'bg-slate-900 border-slate-800/80 hover:border-slate-700'}`}
                        >
                          <div>
                            <h4 className="font-bold text-slate-200">{u.name}</h4>
                            <span className="text-[10px] text-slate-500 block">Status: {u.isOnline ? 'Online' : 'Offline'}</span>
                          </div>
                          {chats.filter(c => c.userId === u.id && c.sender === 'user').length > 0 && (
                            <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full animate-pulse" style={{ backgroundColor: config.primaryColor }} />
                          )}
                        </button>
                      ))
                    )}
                  </div>
                </div>

                {/* Active chat log view & respond form */}
                <div className="md:col-span-2 bg-slate-950 border border-slate-800 rounded-3xl p-4 h-[480px] flex flex-col justify-between shadow">
                  {selectedUserChatId ? (
                    <>
                      {/* header details */}
                      <div className="border-b border-slate-800/80 pb-3 mb-3 flex items-center justify-between text-xs">
                        <div>
                          <h4 className="font-bold text-slate-200">
                            {users.find(u => u.id === selectedUserChatId)?.name || 'Mijoz'} bilan suhbat
                          </h4>
                          <span className="text-[10px] text-slate-500">ID: {selectedUserChatId}</span>
                        </div>
                        <button 
                          onClick={() => {
                            clearChat(selectedUserChatId);
                            setSelectedUserChatId('');
                          }}
                          className="text-[10px] text-red-500 hover:underline"
                        >
                          Suhbatni tozalash
                        </button>
                      </div>

                      {/* message history bubbles */}
                      <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs mb-3">
                        {chats.filter(c => c.userId === selectedUserChatId).map(msg => (
                          <div key={msg.id} className={`flex ${msg.sender === 'admin' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[80%] rounded-2xl px-3 py-2 leading-relaxed shadow-sm ${msg.sender === 'admin' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-slate-900 text-slate-100 rounded-tl-none'}`} style={msg.sender === 'admin' ? { backgroundColor: config.primaryColor } : {}}>
                              <p className="break-words">{msg.text}</p>
                              <span className="text-[9px] text-slate-400 block mt-1 text-right font-mono">
                                {new Date(msg.createdAt).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* input send form */}
                      <form onSubmit={handleAdminChatReply} className="flex gap-2 border-t border-slate-800 pt-3">
                        <input 
                          type="text"
                          required
                          value={adminReplyText}
                          onChange={(e) => setAdminReplyText(e.target.value)}
                          placeholder="Foydalanuvchiga javob yozing (Telegram botda ko'rinadi)..."
                          className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none"
                        />
                        <button 
                          type="submit"
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-1 cursor-pointer"
                          style={{ backgroundColor: config.primaryColor }}
                        >
                          <Send className="w-3.5 h-3.5" /> Javob
                        </button>
                      </form>
                    </>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center text-xs space-y-1">
                      <MessageSquare className="w-8 h-8 text-slate-700 mb-1" />
                      <p className="font-bold">Suhbat tanlanmagan</p>
                      <p>Mijoz suhbatlariga kirish uchun chap paneldan biror kishini tanlang.</p>
                    </div>
                  )}
                </div>

              </div>
            </motion.div>
          )}

          {/* 9. TELEGRAM BOT SETTINGS TAB */}
          {activeSubTab === 'bot_settings' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 max-w-xl">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Bot integratsiya sozlamalari</h2>
                <p className="text-xs text-slate-400">Majburiy obuna kanallarini kiritish, VIP obuna xabarlarini tahrirlash.</p>
              </div>

              <div className="bg-slate-950 border border-slate-800 p-6 rounded-3xl space-y-5 text-xs">
                {/* Channels configuration */}
                <div className="space-y-3">
                  <h3 className="font-bold text-slate-300">Majburiy Obuna Kanallari</h3>
                  
                  <form onSubmit={handleAddMandatoryChannel} className="flex gap-2">
                    <input 
                      type="text"
                      placeholder="Masalan: @kino_olami"
                      value={newMandatoryChannel}
                      onChange={(e) => setNewMandatoryChannel(e.target.value)}
                      className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white"
                    />
                    <button 
                      type="submit"
                      className="px-4 py-2 bg-indigo-600 text-white rounded-xl font-bold cursor-pointer hover:bg-indigo-500"
                      style={{ backgroundColor: config.primaryColor }}
                    >
                      Qo'shish
                    </button>
                  </form>

                  <div className="flex flex-wrap gap-2 pt-1">
                    {config.mandatoryChannels.length === 0 ? (
                      <span className="text-slate-500">Hech qanday kanal kiritilmagan. Botda majburiy obuna yo'q.</span>
                    ) : (
                      config.mandatoryChannels.map(channel => (
                        <div key={channel} className="bg-slate-900 border border-slate-800 px-3 py-1 rounded-full flex items-center gap-2 font-mono text-[11px]">
                          <span>{channel}</span>
                          <button 
                            type="button" 
                            onClick={() => handleRemoveMandatoryChannel(channel)}
                            className="text-red-500 font-bold hover:text-red-400"
                          >
                            ×
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* VIP Buyruq xabari editor */}
                <div className="space-y-2 border-t border-slate-800 pt-4">
                  <h3 className="font-bold text-slate-300">Bot VIP Buyrug'i Javob Matni</h3>
                  <textarea 
                    rows={6}
                    value={config.vipMessage}
                    onChange={(e) => updateConfig({...config, vipMessage: e.target.value})}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-white leading-relaxed"
                  />
                  <span className="text-[10px] text-slate-500 block">Ushbu matn foydalanuvchilar telegram botda /vip buyrug'ini kiritganlarida qaytadi.</span>
                </div>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </main>

    </div>
  );
}
