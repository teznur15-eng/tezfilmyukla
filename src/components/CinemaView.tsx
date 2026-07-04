import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../AppContext';
import { Movie, MovieCategory } from '../types';
import { 
  Play, Search, Star, Clock, Heart, Download, MessageSquare, Send, 
  ChevronRight, ChevronLeft, Lock, BadgePercent, Check, Eye, ExternalLink, Sparkles
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function CinemaView() {
  const { 
    movies, 
    currentUser, 
    config, 
    savedMovies, 
    watchHistory, 
    toggleSavedMovie, 
    addToHistory, 
    addComment, 
    incrementViews,
    addChatMessage,
    ads,
    incrementAdImpressions
  } = useApp();

  // Navigation states
  const [activeTab, setActiveTab] = useState<'home' | 'search' | 'history' | 'saved' | 'profile'>('home');
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  
  // Carousel states
  const [carouselIndex, setCarouselIndex] = useState(0);
  const carouselMovies = movies.slice(0, 3);

  // Filter / Search states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<MovieCategory | 'all'>('all');
  const [selectedGenre, setSelectedGenre] = useState<string>('all');
  const [selectedYear, setSelectedYear] = useState<string>('all');
  const [codeSearchQuery, setCodeSearchQuery] = useState('');

  // Player controls
  const [isPlaying, setIsPlaying] = useState(false);
  const [videoQuality, setVideoQuality] = useState<'720p' | '1080p'>('720p');
  const [videoSpeed, setVideoSpeed] = useState<number>(1);
  const [videoProgress, setVideoProgress] = useState(0);
  const [isVipPromptOpen, setIsVipPromptOpen] = useState(false);
  const [commentText, setCommentText] = useState('');
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const progressIntervalRef = useRef<any>(null);

  // Auto-scroll carousel
  useEffect(() => {
    if (activeTab !== 'home' || selectedMovie) return;
    const interval = setInterval(() => {
      setCarouselIndex(prev => (prev + 1) % Math.max(1, carouselMovies.length));
    }, 6000);
    return () => clearInterval(interval);
  }, [carouselMovies.length, activeTab, selectedMovie]);

  // Handle ad impression tracking
  useEffect(() => {
    ads.filter(a => a.isActive).forEach(a => {
      incrementAdImpressions(a.id);
    });
  }, [activeTab, selectedMovie]);

  const handleMovieSelect = (movie: Movie) => {
    setSelectedMovie(movie);
    incrementViews(movie.id);
    setIsPlaying(false);
    setVideoQuality('720p');
    setVideoSpeed(1);
    setVideoProgress(0);
  };

  const handlePlayToggle = () => {
    if (!currentUser) return;
    
    if (videoQuality === '1080p' && !isVipActive()) {
      setIsVipPromptOpen(true);
      return;
    }

    setIsPlaying(!isPlaying);
    if (!isPlaying) {
      // simulate progress
      progressIntervalRef.current = setInterval(() => {
        setVideoProgress(prev => {
          const next = prev + 1;
          if (next >= 100) {
            clearInterval(progressIntervalRef.current);
            setIsPlaying(false);
            addToHistory(selectedMovie!.id, 100);
            return 100;
          }
          if (next % 10 === 0) {
            addToHistory(selectedMovie!.id, next);
          }
          return next;
        });
      }, 1000 / videoSpeed);
    } else {
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    }
  };

  useEffect(() => {
    return () => {
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };
  }, []);

  const changeQuality = (quality: '720p' | '1080p') => {
    if (quality === '1080p' && !isVipActive()) {
      setIsVipPromptOpen(true);
      return;
    }
    setVideoQuality(quality);
    setIsPlaying(false);
    setVideoProgress(0);
  };

  const handleSpeedChange = (speed: number) => {
    setVideoSpeed(speed);
    if (isPlaying) {
      setIsPlaying(false);
      setTimeout(() => handlePlayToggle(), 100);
    }
  };

  const handleAddComment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || !selectedMovie || !currentUser) return;
    addComment(selectedMovie.id, currentUser.name, commentText.trim());
    setCommentText('');
  };

  const triggerDownloadInBot = (movie: Movie) => {
    if (!currentUser) return;
    // Send message into user's support log/simulation chat
    addChatMessage(
      currentUser.id,
      currentUser.name,
      `/kino ${movie.code}`,
      'user'
    );
    addChatMessage(
      currentUser.id,
      'Kino Bot',
      `🎬 <b>${movie.title}</b> (${movie.year})\n\n📂 Janr: ${movie.genre}\n📺 Sifat: HD 720p & FHD 1080p\n\n📥 Kinoni yuklab olish uchun quyidagi tugmalarni bosing:\n⚡ [Yuklab olish 720p](${movie.link720})\n💎 [Premium yuklab olish 1080p](${movie.link1080})`,
      'admin'
    );
    alert(`"${movie.title}" filmi Telegram botingizga muvaffaqiyatli yuborildi! Bot simulyatoriga o'tib yuklab olishingiz mumkin.`);
  };

  const isVipActive = () => {
    if (!currentUser?.vipUntil) return false;
    return new Date(currentUser.vipUntil) > new Date();
  };

  // Get active user subscription format
  const getVipExpiryText = () => {
    if (!currentUser?.vipUntil) return null;
    const expDate = new Date(currentUser.vipUntil);
    if (expDate < new Date()) return 'Muddati tugagan';
    return expDate.toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  // Genres from movies
  const genres = ['all', ...Array.from(new Set(movies.map(m => m.genre.split(', ').flat()).flat()))];
  const years = ['all', ...Array.from(new Set(movies.map(m => m.year.toString())))].sort((a, b) => (b as string).localeCompare(a as string));

  const filteredMovies = movies.filter(m => {
    const matchesSearch = m.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          m.code.includes(searchQuery);
    const matchesCategory = selectedCategory === 'all' || m.category === selectedCategory;
    const matchesGenre = selectedGenre === 'all' || m.genre.includes(selectedGenre);
    const matchesYear = selectedYear === 'all' || m.year.toString() === selectedYear;
    return matchesSearch && matchesCategory && matchesGenre && matchesYear;
  });

  const handleCodeSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!codeSearchQuery.trim()) return;
    const found = movies.find(m => m.code === codeSearchQuery.trim());
    if (found) {
      handleMovieSelect(found);
      setCodeSearchQuery('');
    } else {
      alert(`Kechirasiz, "${codeSearchQuery}" kodli film topilmadi.`);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 font-sans select-none overflow-hidden" style={{ '--primary': config.primaryColor } as React.CSSProperties}>
      
      {/* Top Header */}
      <header className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <img src={config.logoUrl} alt="Logo" className="w-9 h-9 rounded-full object-cover border border-slate-700" referrerPolicy="no-referrer" />
          <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-indigo-400 to-indigo-200 bg-clip-text text-transparent">
            KinoPortal
          </span>
        </div>

        <div className="flex items-center gap-2">
          {currentUser && (
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${isVipActive() ? 'bg-amber-500/10 border-amber-500/30 text-amber-300' : 'bg-slate-800 border-slate-700 text-slate-300'}`}>
              <span className={`w-2 h-2 rounded-full ${currentUser.isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
              <span className="max-w-[100px] truncate">{currentUser.name}</span>
              {isVipActive() && <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
            </div>
          )}
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 overflow-y-auto pb-20">
        <AnimatePresence mode="wait">
          {selectedMovie ? (
            /* =================== DETAILED MOVIE VIEW =================== */
            <motion.div 
              key="movie-detail"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              className="p-4 max-w-4xl mx-auto space-y-6"
            >
              {/* Back Button */}
              <button 
                onClick={() => setSelectedMovie(null)}
                className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" /> Bosh sahifaga qaytish
              </button>

              {/* Cinematic Video Player */}
              <div className="relative aspect-video rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-2xl">
                {!isPlaying ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-cover bg-center" style={{ backgroundImage: `linear-gradient(to top, rgba(15, 23, 42, 0.95), rgba(15, 23, 42, 0.5)), url(${selectedMovie.imageUrl})` }}>
                    <button 
                      onClick={handlePlayToggle}
                      className="p-5 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white shadow-xl hover:scale-105 transition duration-300 cursor-pointer"
                      style={{ backgroundColor: config.primaryColor }}
                    >
                      <Play className="w-8 h-8 fill-current" />
                    </button>
                    <p className="mt-3 text-sm font-semibold text-slate-200">
                      {videoQuality === '1080p' ? 'Full HD 1080p (Premium)' : 'Standard HD 720p'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      {isVipActive() ? 'Premium ruxsat faol' : '1080p faqat VIP uchun'}
                    </p>
                  </div>
                ) : (
                  <div className="absolute inset-0 bg-slate-950 flex flex-col justify-between p-4">
                    {/* Fake Video playback */}
                    <div className="flex-1 flex flex-col items-center justify-center">
                      <div className="relative w-20 h-20">
                        <div className="absolute inset-0 rounded-full border-4 border-slate-800 border-t-indigo-500 animate-spin" style={{ borderTopColor: config.primaryColor }} />
                        <Play className="w-8 h-8 text-slate-400 absolute inset-0 m-auto animate-pulse" />
                      </div>
                      <p className="text-sm font-mono mt-4 text-slate-400">
                        Video o'ynatilmoqda: {videoProgress}% / ({videoSpeed}x)
                      </p>
                    </div>

                    {/* Quality, Speed Controls */}
                    <div className="bg-slate-900/90 backdrop-blur-md p-3 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={handlePlayToggle} 
                          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium"
                        >
                          Pauza
                        </button>
                        <span className="text-slate-400 font-mono">{videoProgress}% korildi</span>
                      </div>

                      {/* Video Speed Selector */}
                      <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg">
                        {[0.5, 1, 1.5, 2].map(speed => (
                          <button
                            key={speed}
                            onClick={() => handleSpeedChange(speed)}
                            className={`px-2 py-1 rounded-md text-[10px] font-bold ${videoSpeed === speed ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
                            style={videoSpeed === speed ? { backgroundColor: config.primaryColor } : {}}
                          >
                            {speed}x
                          </button>
                        ))}
                      </div>

                      {/* Resolution Selector */}
                      <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg">
                        <button 
                          onClick={() => changeQuality('720p')}
                          className={`px-2 py-1 rounded-md text-[10px] font-bold ${videoQuality === '720p' ? 'bg-slate-800 text-white' : 'text-slate-400'}`}
                        >
                          720p
                        </button>
                        <button 
                          onClick={() => changeQuality('1080p')}
                          className={`px-2 py-1 rounded-md text-[10px] font-bold flex items-center gap-1 ${videoQuality === '1080p' ? 'bg-amber-600 text-white' : 'text-slate-400'} ${!isVipActive() ? 'opacity-80' : ''}`}
                        >
                          {!isVipActive() && <Lock className="w-3 h-3" />}
                          1080p {!isVipActive() && '⭐'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Title & Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Poster / Details */}
                <div className="md:col-span-2 space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 text-xs font-semibold uppercase" style={{ color: config.primaryColor, borderColor: `${config.primaryColor}20`, backgroundColor: `${config.primaryColor}10` }}>
                      {selectedMovie.category}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-xs font-medium">
                      {selectedMovie.year} - yil
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-xs font-mono">
                      Kod: {selectedMovie.code}
                    </span>
                  </div>

                  <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">{selectedMovie.title}</h1>

                  {/* Rating / Actions */}
                  <div className="flex flex-wrap items-center justify-between gap-4 p-3 bg-slate-900 border border-slate-800 rounded-xl">
                    <div className="flex items-center gap-2">
                      <Star className="w-5 h-5 fill-amber-400 text-amber-400" />
                      <span className="font-bold text-lg">{selectedMovie.rating}</span>
                      <span className="text-slate-500 text-xs">/ 10</span>
                      <span className="mx-2 text-slate-700">|</span>
                      <Eye className="w-4 h-4 text-slate-400" />
                      <span className="text-slate-300 text-xs font-mono">{selectedMovie.views.toLocaleString()} marta ko'rildi</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button 
                        onClick={() => toggleSavedMovie(selectedMovie.id)}
                        className={`p-2 rounded-xl border transition ${savedMovies.includes(selectedMovie.id) ? 'bg-rose-500/10 border-rose-500/30 text-rose-400' : 'border-slate-800 bg-slate-950 text-slate-400 hover:text-white'}`}
                      >
                        <Heart className="w-5 h-5 fill-current" />
                      </button>
                      <button 
                        onClick={() => triggerDownloadInBot(selectedMovie)}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg transition cursor-pointer"
                        style={{ backgroundColor: config.primaryColor }}
                      >
                        <Download className="w-4 h-4" /> Botga yuborish (Yuklab olish)
                      </button>
                    </div>
                  </div>

                  {/* Synopsis / Story */}
                  <div className="space-y-2">
                    <h3 className="text-sm font-bold text-slate-300">Film Syujeti</h3>
                    <p className="text-sm text-slate-400 leading-relaxed bg-slate-900/50 p-4 rounded-xl border border-slate-800/50">
                      {selectedMovie.description}
                    </p>
                  </div>

                  {/* Movie Info */}
                  <div className="grid grid-cols-2 gap-4 text-xs bg-slate-900/50 p-4 rounded-xl border border-slate-800/50">
                    <div>
                      <span className="text-slate-500 block mb-0.5">Janr:</span>
                      <span className="text-slate-300 font-medium">{selectedMovie.genre}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block mb-0.5">Kod raqami (Qidiruv):</span>
                      <span className="text-slate-300 font-mono font-bold">{selectedMovie.code}</span>
                    </div>
                  </div>
                </div>

                {/* Comments Panel */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-slate-400" /> Izohlar ({selectedMovie.comments.length})
                  </h3>

                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col h-[300px]">
                    {/* Comment list */}
                    <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
                      {selectedMovie.comments.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-slate-500 text-center">
                          Ilk izohni siz qoldiring!
                        </div>
                      ) : (
                        selectedMovie.comments.map(comment => (
                          <div key={comment.id} className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/50">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="font-bold text-slate-300">{comment.userName}</span>
                              <span className="text-[10px] text-slate-500 font-mono">
                                {new Date(comment.createdAt).toLocaleDateString('uz-UZ')}
                              </span>
                            </div>
                            <p className="text-slate-400 leading-normal">{comment.text}</p>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Input form */}
                    <form onSubmit={handleAddComment} className="mt-3 flex items-center gap-2 border-t border-slate-800 pt-3 shrink-0">
                      <input 
                        type="text" 
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder="Izoh qoldiring..."
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                      <button 
                        type="submit"
                        className="p-2 rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 shrink-0 cursor-pointer"
                        style={{ backgroundColor: config.primaryColor }}
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    </form>
                  </div>
                </div>
              </div>

              {/* Show Google / TG Active Ads */}
              {ads.filter(a => a.isActive).map(ad => (
                <div key={ad.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 text-xs relative overflow-hidden">
                  <div className="absolute top-2 right-2 bg-slate-800 text-[10px] text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">
                    {ad.type === 'google' ? 'Google Reklama' : 'Telegram Reklama'}
                  </div>
                  <h4 className="font-bold text-slate-300 mb-1">{ad.title}</h4>
                  <p className="text-slate-400 leading-relaxed pr-24">{ad.content}</p>
                  {ad.imageUrl && (
                    <img src={ad.imageUrl} alt="Ad" className="mt-3 h-20 w-full object-cover rounded-xl border border-slate-800" referrerPolicy="no-referrer" />
                  )}
                </div>
              ))}
            </motion.div>
          ) : (
            /* =================== WEB PLATFORM SHELL =================== */
            <motion.div 
              key={activeTab}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="p-4 max-w-6xl mx-auto space-y-6"
            >
              
              {/* Home tab view */}
              {activeTab === 'home' && (
                <>
                  {/* Movie code search panel */}
                  <form onSubmit={handleCodeSearchSubmit} className="flex gap-2 max-w-md mx-auto bg-slate-900 border border-slate-800 p-2 rounded-2xl">
                    <div className="flex-1 flex items-center gap-2 px-2 bg-slate-950 border border-slate-800 rounded-xl">
                      <Search className="w-4 h-4 text-slate-500 shrink-0" />
                      <input 
                        type="text" 
                        value={codeSearchQuery}
                        onChange={(e) => setCodeSearchQuery(e.target.value)}
                        placeholder="Kino kodini kiriting (masalan, 1001)..."
                        className="w-full bg-transparent py-2 border-0 focus:outline-none text-xs text-white"
                      />
                    </div>
                    <button 
                      type="submit" 
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-xl text-white shadow transition cursor-pointer"
                      style={{ backgroundColor: config.primaryColor }}
                    >
                      Topish
                    </button>
                  </form>

                  {/* Carousel banner slider */}
                  {carouselMovies.length > 0 && (
                    <div className="relative h-48 md:h-72 rounded-3xl overflow-hidden border border-slate-800 group shadow-lg">
                      <AnimatePresence mode="wait">
                        <motion.div 
                          key={carouselIndex}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="absolute inset-0 bg-cover bg-center flex flex-col justify-end p-6"
                          style={{ backgroundImage: `linear-gradient(to top, rgba(15, 23, 42, 0.95) 15%, rgba(15, 23, 42, 0.2)), url(${carouselMovies[carouselIndex].imageUrl})` }}
                        >
                          <div className="space-y-2 max-w-lg">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/20 text-[10px] font-bold uppercase tracking-wider">
                                Premyera
                              </span>
                              <span className="text-xs text-slate-300 font-semibold">{carouselMovies[carouselIndex].year}</span>
                            </div>
                            <h2 className="text-xl md:text-3xl font-black text-white leading-tight">
                              {carouselMovies[carouselIndex].title}
                            </h2>
                            <p className="text-xs text-slate-400 line-clamp-2 md:line-clamp-3">
                              {carouselMovies[carouselIndex].description}
                            </p>
                            <button 
                              onClick={() => handleMovieSelect(carouselMovies[carouselIndex])}
                              className="inline-flex items-center gap-2 mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-xl shadow-lg transition cursor-pointer"
                              style={{ backgroundColor: config.primaryColor }}
                            >
                              <Play className="w-3.5 h-3.5 fill-current" /> Tomosha qilish
                            </button>
                          </div>
                        </motion.div>
                      </AnimatePresence>

                      {/* Manual Slide Controls */}
                      <button 
                        onClick={() => setCarouselIndex(prev => (prev - 1 + carouselMovies.length) % carouselMovies.length)}
                        className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-slate-900/60 hover:bg-slate-900 text-white border border-slate-800 opacity-0 group-hover:opacity-100 transition duration-300 cursor-pointer"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => setCarouselIndex(prev => (prev + 1) % carouselMovies.length)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-slate-900/60 hover:bg-slate-900 text-white border border-slate-800 opacity-0 group-hover:opacity-100 transition duration-300 cursor-pointer"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>

                      {/* Carousel Bullet Indicators */}
                      <div className="absolute bottom-4 right-6 flex gap-1.5 z-10">
                        {carouselMovies.map((_, idx) => (
                          <button
                            key={idx}
                            onClick={() => setCarouselIndex(idx)}
                            className={`h-1.5 rounded-full transition-all duration-300 ${carouselIndex === idx ? 'w-5 bg-indigo-500' : 'w-1.5 bg-slate-600'}`}
                            style={carouselIndex === idx ? { backgroundColor: config.primaryColor } : {}}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Genre / Category badges */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Janr va turlari</h3>
                    <div className="flex flex-wrap gap-2">
                      {(['all', 'kino', 'serial', 'kdrama', 'turk', 'anime', 'multfilm'] as const).map(cat => (
                        <button
                          key={cat}
                          onClick={() => setSelectedCategory(cat)}
                          className={`px-4 py-1.5 rounded-full text-xs font-bold border transition duration-200 capitalize cursor-pointer ${selectedCategory === cat ? 'bg-indigo-600 text-white border-transparent shadow' : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700'}`}
                          style={selectedCategory === cat ? { backgroundColor: config.primaryColor } : {}}
                        >
                          {cat === 'all' ? 'Barchasi' : cat}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Movie Cards Grid */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                        <Star className="w-4 h-4 text-amber-500 fill-amber-500" /> Yangi yuklangan kinolar ({filteredMovies.length})
                      </h3>
                    </div>

                    {filteredMovies.length === 0 ? (
                      <div className="bg-slate-900/50 rounded-2xl border border-slate-800 py-12 text-center text-slate-500 text-sm">
                        Kechirasiz, tanlangan janrda filmlar mavjud emas.
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                        {filteredMovies.map(movie => (
                          <div 
                            key={movie.id} 
                            onClick={() => handleMovieSelect(movie)}
                            className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden cursor-pointer hover:border-slate-700 transition duration-300 flex flex-col group shadow"
                          >
                            <div className="relative aspect-[3/4] bg-slate-950 overflow-hidden shrink-0">
                              <img 
                                src={movie.imageUrl} 
                                alt={movie.title} 
                                className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
                                referrerPolicy="no-referrer"
                              />
                              <div className="absolute top-2 left-2 bg-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full border border-indigo-500 shadow-md" style={{ backgroundColor: config.primaryColor }}>
                                {movie.category.toUpperCase()}
                              </div>
                              <div className="absolute bottom-2 right-2 bg-slate-950/85 backdrop-blur-sm px-2 py-0.5 rounded-lg flex items-center gap-1 text-[10px] font-bold text-slate-200 border border-slate-800">
                                <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                                {movie.rating}
                              </div>
                              <div className="absolute top-2 right-2 bg-slate-950/85 backdrop-blur-sm px-2 py-0.5 rounded-lg text-[9px] font-mono font-bold text-slate-400 border border-slate-800">
                                Kod: {movie.code}
                              </div>
                            </div>
                            <div className="p-3 flex-1 flex flex-col justify-between space-y-1 bg-slate-900">
                              <div>
                                <h4 className="font-bold text-xs text-white leading-tight line-clamp-1 group-hover:text-indigo-400 transition" style={{ hover: { color: config.primaryColor } } as React.CSSProperties}>
                                  {movie.title}
                                </h4>
                                <p className="text-[10px] text-slate-400 mt-0.5 line-clamp-1">{movie.genre}</p>
                              </div>
                              <div className="flex items-center justify-between border-t border-slate-800 pt-2 mt-1 text-[9px] text-slate-500 font-medium">
                                <span>{movie.year}-yil</span>
                                <span>{movie.views.toLocaleString()} ko'rildi</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Search catalog tab */}
              {activeTab === 'search' && (
                <div className="space-y-6">
                  {/* Search layout filter bar */}
                  <div className="bg-slate-900 border border-slate-800 p-4 rounded-3xl space-y-4">
                    <div className="flex items-center gap-2 px-3 bg-slate-950 border border-slate-800 rounded-2xl">
                      <Search className="w-4 h-4 text-slate-500 shrink-0" />
                      <input 
                        type="text" 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Nomi, janri yoki kino kodini yozing..."
                        className="w-full bg-transparent py-3 border-0 focus:outline-none text-xs text-white"
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-500 block mb-1 uppercase">Kategoriya</label>
                        <select 
                          value={selectedCategory} 
                          onChange={(e: any) => setSelectedCategory(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-300 focus:outline-none"
                        >
                          <option value="all">Barcha toifalar</option>
                          <option value="kino">Film/Kino</option>
                          <option value="serial">Serial</option>
                          <option value="kdrama">KDrama</option>
                          <option value="turk">Turk Serali</option>
                          <option value="anime">Anime</option>
                          <option value="multfilm">Multfilm</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[10px] font-bold text-slate-500 block mb-1 uppercase">Janr</label>
                        <select 
                          value={selectedGenre} 
                          onChange={(e) => setSelectedGenre(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-300 focus:outline-none"
                        >
                          <option value="all">Barcha janrlar</option>
                          {genres.filter(g => g !== 'all').map(g => (
                            <option key={g} value={g}>{g}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="text-[10px] font-bold text-slate-500 block mb-1 uppercase">Yil</label>
                        <select 
                          value={selectedYear} 
                          onChange={(e) => setSelectedYear(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-300 focus:outline-none"
                        >
                          <option value="all">Barcha yillar</option>
                          {years.filter(y => y !== 'all').map(y => (
                            <option key={y} value={y}>{y}-yil</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Results */}
                  <div className="space-y-4">
                    <h3 className="font-bold text-sm text-slate-400">Qidiruv natijalari ({filteredMovies.length})</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      {filteredMovies.map(movie => (
                        <div 
                          key={movie.id} 
                          onClick={() => handleMovieSelect(movie)}
                          className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden cursor-pointer hover:border-slate-700 transition flex flex-col group shadow"
                        >
                          <img src={movie.imageUrl} alt={movie.title} className="aspect-[3/4] object-cover" referrerPolicy="no-referrer" />
                          <div className="p-3">
                            <h4 className="font-bold text-xs text-white truncate group-hover:text-indigo-400 transition" style={{ hover: { color: config.primaryColor } } as React.CSSProperties}>{movie.title}</h4>
                            <p className="text-[9px] text-slate-500 truncate mt-0.5">{movie.genre}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Watch History Tab */}
              {activeTab === 'history' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                      <Clock className="w-5 h-5 text-indigo-400" /> Ko'rilgan filmlar tarixi
                    </h2>
                  </div>

                  {watchHistory.length === 0 ? (
                    <div className="bg-slate-900 border border-slate-800 rounded-3xl py-12 text-center text-slate-500 text-sm">
                      Ko'rish tarixi hozircha bo'sh. Saytda biron-bir film tomosha qiling.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {watchHistory.map(historyItem => {
                        const movie = movies.find(m => m.id === historyItem.movieId);
                        if (!movie) return null;
                        return (
                          <div 
                            key={historyItem.id}
                            onClick={() => handleMovieSelect(movie)}
                            className="bg-slate-900 border border-slate-800 p-3 rounded-2xl flex gap-3 hover:border-slate-700 cursor-pointer transition shadow"
                          >
                            <img src={movie.imageUrl} alt={movie.title} className="w-16 h-20 object-cover rounded-xl" referrerPolicy="no-referrer" />
                            <div className="flex-1 flex flex-col justify-between py-1">
                              <div>
                                <h4 className="font-bold text-xs text-white leading-snug">{movie.title}</h4>
                                <p className="text-[10px] text-slate-500 mt-0.5">{movie.genre}</p>
                              </div>
                              <div className="space-y-1.5">
                                <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                                  <div className="bg-indigo-500 h-full" style={{ width: `${historyItem.progress}%`, backgroundColor: config.primaryColor }} />
                                </div>
                                <div className="flex items-center justify-between text-[9px] text-slate-500">
                                  <span>{historyItem.progress}% tomosha qilindi</span>
                                  <span>{new Date(historyItem.watchedAt).toLocaleDateString('uz-UZ')}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Saved Movies Tab */}
              {activeTab === 'saved' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                      <Heart className="w-5 h-5 text-rose-500 fill-rose-500" /> Saqlab qo'yilgan filmlar ({savedMovies.length})
                    </h2>
                  </div>

                  {savedMovies.length === 0 ? (
                    <div className="bg-slate-900 border border-slate-800 rounded-3xl py-12 text-center text-slate-500 text-sm">
                      Sevimli filmlaringiz ro'yxati bo'sh. Filmlarga yurakcha belgisini bosing.
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      {savedMovies.map(movieId => {
                        const movie = movies.find(m => m.id === movieId);
                        if (!movie) return null;
                        return (
                          <div 
                            key={movie.id}
                            onClick={() => handleMovieSelect(movie)}
                            className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden cursor-pointer hover:border-slate-700 transition flex flex-col group shadow"
                          >
                            <img src={movie.imageUrl} alt={movie.title} className="aspect-[3/4] object-cover" referrerPolicy="no-referrer" />
                            <div className="p-3">
                              <h4 className="font-bold text-xs text-white truncate group-hover:text-indigo-400 transition" style={{ hover: { color: config.primaryColor } } as React.CSSProperties}>{movie.title}</h4>
                              <p className="text-[9px] text-slate-500 truncate mt-0.5">{movie.genre}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Profile / Subscription Tab */}
              {activeTab === 'profile' && (
                <div className="max-w-xl mx-auto space-y-6">
                  {/* Premium Subscription Banner */}
                  <div className={`p-6 rounded-3xl border ${isVipActive() ? 'bg-gradient-to-br from-amber-500/20 to-amber-700/5 border-amber-500/30 text-amber-200' : 'bg-slate-900 border-slate-800'}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${isVipActive() ? 'bg-amber-500 text-slate-950 shadow-md animate-pulse' : 'bg-slate-800 text-slate-400'}`}>
                            {isVipActive() ? 'VIP Premium' : 'Oddiy a\'zo'}
                          </span>
                        </div>
                        <h2 className="text-xl font-bold text-white">
                          {currentUser ? currentUser.name : 'Profil egasi'}
                        </h2>
                        <p className="text-xs text-slate-400">{currentUser?.email}</p>
                      </div>

                      {/* Golden border frame indicator */}
                      <div className={`w-14 h-14 rounded-full p-0.5 ${isVipActive() ? 'bg-gradient-to-tr from-yellow-400 to-amber-500 shadow-lg' : 'bg-slate-800'}`}>
                        <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center font-bold text-lg text-slate-300">
                          {currentUser?.name.substring(0, 2).toUpperCase()}
                        </div>
                      </div>
                    </div>

                    <div className="border-t border-slate-800/80 my-4 pt-4 flex items-center justify-between text-xs">
                      <div>
                        <span className="text-slate-500 block mb-0.5">Balans:</span>
                        <span className="font-mono font-black text-slate-200">{currentUser?.balance.toLocaleString()} so'm</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block mb-0.5">Obuna muddati:</span>
                        <span className="font-mono font-bold text-amber-400">
                          {isVipActive() ? `Faol (${getVipExpiryText()})` : 'Faol emas'}
                        </span>
                      </div>
                    </div>

                    {/* Simulating Telegram Connection details */}
                    <div className="mt-2 bg-slate-950 p-3 rounded-2xl border border-slate-800 flex items-center justify-between gap-3 text-[11px]">
                      <div>
                        <span className="text-slate-500 block">Integratsiyalangan telegram bot:</span>
                        <span className="font-mono text-indigo-400">@kinortal_uz_bot</span>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">Ulandi</span>
                    </div>
                  </div>

                  {/* Copyright Notice */}
                  <div className="bg-slate-900 border border-slate-800 p-5 rounded-3xl space-y-3">
                    <h3 className="font-bold text-xs text-slate-300">Mualliflik huquqi va qonuniy ma'lumotlar</h3>
                    <p className="text-xs text-slate-400 leading-relaxed font-normal">
                      {config.copyrightText}
                    </p>
                    <div className="flex gap-4 pt-2 border-t border-slate-800/60 text-xs">
                      <a href="https://telegram.org" target="_blank" className="text-indigo-400 hover:underline inline-flex items-center gap-1">
                        <ExternalLink className="w-3.5 h-3.5" /> Telegram
                      </a>
                      <a href="https://instagram.com" target="_blank" className="text-rose-400 hover:underline inline-flex items-center gap-1">
                        <ExternalLink className="w-3.5 h-3.5" /> Instagram
                      </a>
                      <a href="https://youtube.com" target="_blank" className="text-red-400 hover:underline inline-flex items-center gap-1">
                        <ExternalLink className="w-3.5 h-3.5" /> YouTube
                      </a>
                    </div>
                  </div>
                </div>
              )}

            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* VIP Upgrade Prompts Modal */}
      {isVipPromptOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-3xl max-w-sm w-full space-y-4 shadow-2xl">
            <div className="text-center space-y-2">
              <Sparkles className="w-10 h-10 text-amber-400 mx-auto" />
              <h3 className="text-lg font-bold text-white">VIP Obuna kerak</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Full HD 1080p sifatda, reklamasiz tomosha qilish va yuklab olish uchun VIP tariflaridan biriga obuna bo'ling.
              </p>
            </div>

            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between font-bold">
                <span className="text-slate-300">1 oylik obuna</span>
                <span className="text-amber-400">15 000 so'm</span>
              </div>
              <div className="flex justify-between font-bold border-t border-slate-800/50 pt-2">
                <span className="text-slate-300">3 oylik obuna</span>
                <span className="text-amber-400">35 000 so'm</span>
              </div>
              <div className="flex justify-between font-bold border-t border-slate-800/50 pt-2">
                <span className="text-slate-300">1 yillik obuna</span>
                <span className="text-amber-400">120 000 so'm</span>
              </div>
            </div>

            <p className="text-[10px] text-center text-slate-500">
              Ushbu to'lovni Telegram Bot simulyatori orqali yoki o'zingiz tahrirlayotgan bot orqali amalga oshirishingiz mumkin.
            </p>

            <div className="flex gap-2">
              <button 
                onClick={() => setIsVipPromptOpen(false)}
                className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold rounded-xl"
              >
                Yopish
              </button>
              <button 
                onClick={() => {
                  setIsVipPromptOpen(false);
                  setActiveTab('profile');
                  setSelectedMovie(null);
                }}
                className="flex-1 py-2.5 bg-amber-500 text-slate-950 text-xs font-bold rounded-xl hover:bg-amber-400 transition"
              >
                Tariflar bo'limi
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Floating Application Navbar (iOS app style) */}
      {!selectedMovie && (
        <nav className="fixed bottom-0 inset-x-0 bg-slate-900 border-t border-slate-800 py-2.5 px-4 flex justify-around items-center z-40 max-w-6xl mx-auto rounded-t-3xl shadow-xl">
          <button 
            onClick={() => setActiveTab('home')}
            className={`flex flex-col items-center gap-1 text-[10px] font-bold ${activeTab === 'home' ? 'text-indigo-500' : 'text-slate-400 hover:text-white'}`}
            style={activeTab === 'home' ? { color: config.primaryColor } : {}}
          >
            <Play className="w-4 h-4 fill-current" />
            Bosh sahifa
          </button>
          <button 
            onClick={() => setActiveTab('search')}
            className={`flex flex-col items-center gap-1 text-[10px] font-bold ${activeTab === 'search' ? 'text-indigo-500' : 'text-slate-400 hover:text-white'}`}
            style={activeTab === 'search' ? { color: config.primaryColor } : {}}
          >
            <Search className="w-4 h-4" />
            Qidiruv
          </button>
          <button 
            onClick={() => setActiveTab('history')}
            className={`flex flex-col items-center gap-1 text-[10px] font-bold ${activeTab === 'history' ? 'text-indigo-500' : 'text-slate-400 hover:text-white'}`}
            style={activeTab === 'history' ? { color: config.primaryColor } : {}}
          >
            <Clock className="w-4 h-4" />
            Tarix
          </button>
          <button 
            onClick={() => setActiveTab('saved')}
            className={`flex flex-col items-center gap-1 text-[10px] font-bold ${activeTab === 'saved' ? 'text-indigo-500' : 'text-slate-400 hover:text-white'}`}
            style={activeTab === 'saved' ? { color: config.primaryColor } : {}}
          >
            <Heart className="w-4 h-4 fill-current" />
            Saqlangan
          </button>
          <button 
            onClick={() => setActiveTab('profile')}
            className={`flex flex-col items-center gap-1 text-[10px] font-bold ${activeTab === 'profile' ? 'text-indigo-500' : 'text-slate-400 hover:text-white'}`}
            style={activeTab === 'profile' ? { color: config.primaryColor } : {}}
          >
            <Sparkles className="w-4 h-4" />
            Profil/VIP
          </button>
        </nav>
      )}

    </div>
  );
}
