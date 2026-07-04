import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../AppContext';
import { 
  Send, Sparkles, CreditCard, ShieldCheck, Check, AlertCircle, FileText, 
  User as UserIcon, HelpCircle, Phone, ArrowUpRight, Upload, BellRing
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function BotView() {
  const { 
    currentUser, 
    config, 
    cards, 
    movies, 
    chats, 
    addChatMessage, 
    addReceipt, 
    receipts
  } = useApp();

  const [messageText, setMessageText] = useState('');
  const [hasSubscribed, setHasSubscribed] = useState(false);
  const [showVipPortal, setShowVipPortal] = useState(false);

  // VIP Receipt submit state
  const [selectedPlan, setSelectedPlan] = useState<'1month' | '3month' | '1year'>('1month');
  const [selectedCardId, setSelectedCardId] = useState('');
  const [paymentAmount, setPaymentAmount] = useState('15000');
  const [receiptImage, setReceiptImage] = useState<string>('');
  const [isSubmittingCheck, setIsSubmittingCheck] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Filter messages for current simulated user
  const userMessages = chats.filter(m => m.userId === (currentUser?.id || 'user-owner'));

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chats, userMessages.length]);

  // Set default payment card
  useEffect(() => {
    if (cards.length > 0 && !selectedCardId) {
      setSelectedCardId(cards[0].id);
    }
  }, [cards]);

  // Handle plan selection update amounts
  useEffect(() => {
    if (selectedPlan === '1month') setPaymentAmount('15000');
    else if (selectedPlan === '3month') setPaymentAmount('35000');
    else if (selectedPlan === '1year') setPaymentAmount('120000');
  }, [selectedPlan]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageText.trim() || !currentUser) return;

    const text = messageText.trim();
    setMessageText('');

    // Save user message
    addChatMessage(currentUser.id, currentUser.name, text, 'user');

    // Simulate bot replies
    setTimeout(() => {
      processBotLogic(text);
    }, 1000);
  };

  const processBotLogic = (text: string) => {
    if (!currentUser) return;

    const lower = text.toLowerCase();

    // Start Command
    if (lower === '/start') {
      addChatMessage(
        currentUser.id,
        'Kino Bot',
        `Salom <b>${currentUser.name}</b>! 👋\n\nKino Portal rasmiy integratsiya botiga xush kelibsiz.\n\n🎬 Ushbu bot orqali siz saytdagi barcha kinolarni osonlik bilan yuklab olishingiz mumkin.\n\n🌟 Mavjud buyruqlar:\n👉 <b>[Kino Kodi]</b> - Kino yuklash (Masalan: 1001)\n👉 <b>/vip</b> - VIP Premium obuna olish narxlari\n👉 <b>/help</b> - Admin bilan bog'lanish va qo'llab-quvvatlash`,
        'admin'
      );
      return;
    }

    // VIP Command
    if (lower === '/vip') {
      addChatMessage(
        currentUser.id,
        'Kino Bot',
        config.vipMessage,
        'admin'
      );
      setShowVipPortal(true);
      return;
    }

    // Help Command
    if (lower === '/help') {
      addChatMessage(
        currentUser.id,
        'Kino Bot',
        `Savol yoki takliflaringiz bo'lsa, ushbu chatga bemalol yozishingiz mumkin. Adminlarimiz tez orada sizga javob berishadi! 💬\n\nSayt ma'muriyati: @kinortal_admin_bot\nMualliflik huquqi bo'yicha: support@kinoportal.uz`,
        'admin'
      );
      return;
    }

    // Number Search (Movie Code)
    const codeMatch = text.match(/^\d+$/);
    if (codeMatch) {
      const code = codeMatch[0];
      
      // If subscription required and not simulated yet
      if (config.mandatoryChannels.length > 0 && !hasSubscribed) {
        addChatMessage(
          currentUser.id,
          'Kino Bot',
          `❌ Kechirasiz, kino yuklashdan oldin homiy kanallarimizga a'zo bo'lishingiz shart!\n\nIltimos, quyidagi kanallarga qo'shiling va keyin "Tekshirish" tugmasini bosing:\n${config.mandatoryChannels.map(c => `• ${c}`).join('\n')}`,
          'admin'
        );
        return;
      }

      const movie = movies.find(m => m.code === code);
      if (movie) {
        addChatMessage(
          currentUser.id,
          'Kino Bot',
          `🎬 <b>${movie.title}</b> (${movie.year})\n\n📂 Janr: ${movie.genre}\n⚡ Ko'rishlar: ${movie.views}\n\n📥 Yuklab olish:\n🔹 [Oddiy 720p yuklash](${movie.link720})\n🌟 [Premium 1080p yuklash (VIP)](${movie.link1080})`,
          'admin'
        );
      } else {
        addChatMessage(
          currentUser.id,
          'Kino Bot',
          `🔍 Kechirasiz, bizning bazamizdan <b>"${code}"</b> kodli film topilmadi. Qayta urinib ko'ring yoki saytdan kino kodini qidiring!`,
          'admin'
        );
      }
      return;
    }

    // Standard support ticket responder simulation (fallback text)
    addChatMessage(
      currentUser.id,
      'Kino Bot',
      `Xabaringiz qabul qilindi. 📩 Adminlarimiz sizga tez orada javob yuborishadi.`,
      'admin'
    );
  };

  const handleVerifySubscription = () => {
    setHasSubscribed(true);
    if (currentUser) {
      addChatMessage(
        currentUser.id,
        'Kino Bot',
        `🎉 Rahmat! Obuna muvaffaqiyatli tekshirildi. Endi istalgan kino kodini yuborib yuklab olishingiz mumkin!`,
        'admin'
      );
    }
  };

  const simulateVipReceiptUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) return;

    setIsSubmittingCheck(true);

    // Simulate upload delay
    setTimeout(() => {
      const selectedCard = cards.find(c => c.id === selectedCardId) || cards[0];
      
      // Submit to context
      addReceipt(
        Number(paymentAmount),
        selectedCard ? selectedCard.number : '8600 0000 0000 0000',
        receiptImage || 'https://images.unsplash.com/photo-1628157582853-a796fa650a6a?auto=format&fit=crop&w=300&q=80' // default check receipt mockup
      );

      setIsSubmittingCheck(false);
      setShowVipPortal(false);
      setReceiptImage('');
      
      addChatMessage(
        currentUser.id,
        'Kino Bot',
        `📥 To'lov chekingiz muvaffaqiyatli qabul qilindi. Moliyaviy adminlar chekni tekshirib, tez orada VIP statusini faollashtirishadi! Sabr uchun rahmat! 🙏`,
        'admin'
      );
    }, 1500);
  };

  const handleFileChangeFake = () => {
    // Generate a beautiful mock check base64 / dummy receipt image to showcase
    setReceiptImage('https://images.unsplash.com/photo-1554415707-6e8cfc93fe23?auto=format&fit=crop&w=600&q=80');
  };

  const isVipActive = () => {
    if (!currentUser?.vipUntil) return false;
    return new Date(currentUser.vipUntil) > new Date();
  };

  return (
    <div className="flex h-full bg-slate-950 text-slate-100 overflow-hidden font-sans p-2 select-none justify-center items-center">
      
      {/* Smartphone Outer Shell Mockup */}
      <div className="relative w-full max-w-[420px] h-[95%] aspect-[9/18] bg-slate-900 rounded-[45px] border-4 border-slate-800 shadow-2xl flex flex-col overflow-hidden">
        
        {/* Smartphone Notch */}
        <div className="absolute top-0 inset-x-0 h-6 bg-slate-900 rounded-b-xl flex justify-center items-center z-50">
          <div className="w-24 h-4 bg-black rounded-full" />
        </div>

        {/* Telegram Header */}
        <div className="bg-slate-800/90 pt-8 pb-3 px-4 border-b border-slate-700/50 flex items-center justify-between shrink-0 z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center font-bold text-sm text-indigo-400">
              KB
            </div>
            <div>
              <h3 className="font-bold text-xs flex items-center gap-1">
                KinoPortal Bot {isVipActive() && <Sparkles className="w-3 h-3 text-amber-400" />}
              </h3>
              <span className="text-[10px] text-slate-400">bot @kinoportal_bot</span>
            </div>
          </div>

          <div className="flex gap-2">
            {!hasSubscribed && config.mandatoryChannels.length > 0 && (
              <button 
                onClick={handleVerifySubscription}
                className="px-2.5 py-1 rounded bg-indigo-600 text-[10px] font-bold text-white hover:bg-indigo-500 cursor-pointer"
              >
                Kanalga a'zoman
              </button>
            )}
          </div>
        </div>

        {/* Telegram Chat Message History Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-950/40 relative">
          
          {/* Default Greeting Block (Empty state helper) */}
          {userMessages.length === 0 && (
            <div className="bg-slate-900/60 p-5 rounded-3xl border border-slate-800 text-center space-y-2.5 max-w-[280px] mx-auto mt-6">
              <Sparkles className="w-8 h-8 text-indigo-400 mx-auto" />
              <h4 className="font-bold text-xs">Botni boshlash uchun bosing</h4>
              <p className="text-[10px] text-slate-400 leading-normal">
                Kino yuklab olish kodi, VIP tariflar va admin suhbatlarini sinab ko'rish uchun start buyrug'ini yuboring.
              </p>
              <button 
                onClick={() => processBotLogic('/start')}
                className="w-full py-1.5 bg-indigo-600 rounded-lg text-xs font-bold text-white cursor-pointer"
              >
                /start
              </button>
            </div>
          )}

          {/* Render Chats bubbles */}
          {userMessages.map(msg => {
            const isAdminSender = msg.sender === 'admin';
            return (
              <div 
                key={msg.id} 
                className={`flex ${isAdminSender ? 'justify-start' : 'justify-end'}`}
              >
                <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-xs leading-relaxed shadow-md ${isAdminSender ? 'bg-slate-800 text-slate-100 rounded-tl-none' : 'bg-indigo-600 text-white rounded-tr-none'}`}>
                  {/* Handle HTML tags render in simulation */}
                  <div 
                    dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br />') }} 
                    className="break-words font-normal"
                  />
                  <span className="text-[9px] text-slate-400/80 block mt-1 text-right font-mono">
                    {new Date(msg.createdAt).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            );
          })}

          <div ref={messagesEndRef} />
        </div>

        {/* Telegram Fast Options Keyboard Buttons */}
        <div className="px-3 py-1 bg-slate-900 border-t border-slate-800 shrink-0">
          <div className="grid grid-cols-3 gap-1.5 text-[10px] font-bold">
            <button 
              onClick={() => {
                setMessageText('/start');
                processBotLogic('/start');
              }}
              className="py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-center text-slate-300"
            >
              🚀 Boshlash
            </button>
            <button 
              onClick={() => {
                setMessageText('/vip');
                processBotLogic('/vip');
              }}
              className="py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-center text-slate-300 flex items-center justify-center gap-1"
            >
              💎 VIP tariflar
            </button>
            <button 
              onClick={() => {
                setMessageText('/help');
                processBotLogic('/help');
              }}
              className="py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-center text-slate-300"
            >
              ❓ Murojaat
            </button>
          </div>
        </div>

        {/* Interactive Payment Receipt Upload Drawer (Triggered by /vip or portal) */}
        <AnimatePresence>
          {showVipPortal && (
            <motion.div 
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute inset-x-0 bottom-0 bg-slate-900 border-t-2 border-slate-700 z-30 p-4 max-h-[80%] overflow-y-auto rounded-t-3xl"
            >
              <div className="flex justify-between items-center mb-3">
                <h4 className="font-bold text-xs flex items-center gap-1.5 text-amber-400">
                  <CreditCard className="w-4 h-4" /> VIP To'lov Cheki yuborish
                </h4>
                <button 
                  onClick={() => setShowVipPortal(false)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Yopish
                </button>
              </div>

              {cards.length === 0 ? (
                <div className="bg-slate-950 p-4 rounded-xl text-center text-[11px] text-slate-400 space-y-1">
                  <AlertCircle className="w-5 h-5 text-amber-500 mx-auto" />
                  <p>Hozircha faol to'lov kartalari mavjud emas. Admin tomonidan karta qo'shilishi kutilmoqda.</p>
                </div>
              ) : (
                <form onSubmit={simulateVipReceiptUpload} className="space-y-3 text-xs text-left">
                  {/* Step 1: Choose plan */}
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">Obuna Tarifi</label>
                    <div className="grid grid-cols-3 gap-1.5">
                      {[
                        { id: '1month', label: '1 oy', price: '15,000' },
                        { id: '3month', label: '3 oy', price: '35,000' },
                        { id: '1year', label: '1 yil', price: '120,000' }
                      ].map(plan => (
                        <button
                          key={plan.id}
                          type="button"
                          onClick={() => setSelectedPlan(plan.id as any)}
                          className={`p-1.5 rounded-xl border text-center transition ${selectedPlan === plan.id ? 'bg-amber-500/10 border-amber-500 text-amber-300 font-bold' : 'bg-slate-950 border-slate-800 text-slate-300'}`}
                        >
                          <div className="text-[11px]">{plan.label}</div>
                          <div className="text-[9px] text-slate-400">{plan.price} s</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Step 2: Choose target card */}
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">To'lov qilinadigan karta</label>
                    <select
                      value={selectedCardId}
                      onChange={(e) => setSelectedCardId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 font-mono text-xs focus:outline-none"
                    >
                      {cards.filter(c => c.isActive).map(card => (
                        <option key={card.id} value={card.id}>
                          {card.bank} - {card.number}
                        </option>
                      ))}
                    </select>
                    <span className="text-[9px] text-slate-500 block mt-1">
                      Karta egasi: {cards.find(c => c.id === selectedCardId)?.holder || 'Kino Admin'}
                    </span>
                  </div>

                  {/* Step 3: Check Receipt upload simulation */}
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 block mb-1 uppercase">To'lov cheki (Screenshot)</label>
                    
                    {receiptImage ? (
                      <div className="relative rounded-xl overflow-hidden border border-slate-700 h-24 bg-slate-950 flex items-center justify-center">
                        <img src={receiptImage} alt="Receipt Preview" className="h-full w-full object-cover" referrerPolicy="no-referrer" />
                        <button 
                          type="button" 
                          onClick={() => setReceiptImage('')} 
                          className="absolute top-1 right-1 bg-red-600 text-white rounded-full p-1 text-[8px] font-bold"
                        >
                          X
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={handleFileChangeFake}
                        className="w-full h-24 bg-slate-950 border-2 border-dashed border-slate-800 rounded-xl flex flex-col items-center justify-center text-slate-500 gap-1 hover:border-indigo-500 hover:text-indigo-400 transition"
                      >
                        <Upload className="w-6 h-6" />
                        <span className="text-[10px] font-bold">Virtual chekni biriktirish</span>
                        <span className="text-[8px] text-slate-600">Simulyatsiya rasmi qo'shiladi</span>
                      </button>
                    )}
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isSubmittingCheck}
                    className="w-full py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-slate-800 text-slate-950 font-black rounded-xl text-center shadow-lg transition uppercase tracking-wider text-[11px] cursor-pointer flex items-center justify-center gap-2"
                  >
                    {isSubmittingCheck ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                        Jo'natilmoqda...
                      </>
                    ) : (
                      'To\'lov chekini yuborish 🚀'
                    )}
                  </button>
                </form>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Telegram Input Bar */}
        <form onSubmit={handleSendMessage} className="bg-slate-800 p-2.5 border-t border-slate-700 flex items-center gap-2 shrink-0 z-10">
          <input 
            type="text"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder="Xabar yozing yoki kino kodi..."
            className="flex-1 bg-slate-950 text-xs text-white border border-slate-700 rounded-full px-3.5 py-2 focus:outline-none focus:border-indigo-500"
          />
          <button 
            type="submit"
            className="p-2 rounded-full bg-indigo-600 text-white hover:bg-indigo-500 transition cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

      </div>
    </div>
  );
}
