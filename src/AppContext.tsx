import React, { createContext, useContext, useState, useEffect } from 'react';
import { Movie, User, Card, Ad, Receipt, AppConfig, ChatMessage, Comment, WatchHistoryItem } from './types';
import { INITIAL_MOVIES, INITIAL_USERS, INITIAL_CARDS, INITIAL_ADS, INITIAL_RECEIPTS, DEFAULT_CONFIG } from './mockData';

interface AppContextType {
  movies: Movie[];
  users: User[];
  cards: Card[];
  ads: Ad[];
  receipts: Receipt[];
  chats: ChatMessage[];
  config: AppConfig;
  currentUser: User | null;
  watchHistory: WatchHistoryItem[];
  savedMovies: string[]; // movie IDs
  
  // Movie Actions
  addMovie: (movie: Omit<Movie, 'id' | 'views' | 'comments'>) => void;
  updateMovie: (movie: Movie) => void;
  deleteMovie: (movieId: string) => void;
  addComment: (movieId: string, userName: string, text: string) => void;
  incrementViews: (movieId: string) => void;
  
  // Saved / History Actions
  toggleSavedMovie: (movieId: string) => void;
  addToHistory: (movieId: string, progress: number) => void;
  clearHistory: () => void;

  // User Management Actions
  addUser: (user: User) => void;
  updateUser: (user: User) => void;
  deleteUser: (userId: string) => void;
  setUserBlockedStatus: (userId: string, isBlocked: boolean) => void;
  setUserOnlineStatus: (userId: string, isOnline: boolean) => void;
  setUserRole: (userId: string, role: 'owner' | 'admin' | 'user') => void;
  grantManualVip: (userId: string, days: number) => void;
  switchActiveUser: (userId: string) => void;

  // Financial Actions
  addReceipt: (amount: number, cardNumber: string, imageUrl: string) => void;
  approveReceipt: (receiptId: string) => void;
  rejectReceipt: (receiptId: string) => void;
  addCard: (card: Omit<Card, 'id'>) => void;
  updateCard: (card: Card) => void;
  deleteCard: (cardId: string) => void;

  // Ad Actions
  addAd: (ad: Omit<Ad, 'id' | 'impressions'>) => void;
  updateAd: (ad: Ad) => void;
  deleteAd: (adId: string) => void;
  incrementAdImpressions: (adId: string) => void;

  // Telegram Integration & Chat Actions
  addChatMessage: (userId: string, userName: string, text: string, sender: 'user' | 'admin') => void;
  clearChat: (userId: string) => void;
  deleteChatMessage: (messageId: string) => void;
  updateConfig: (config: AppConfig) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  // --- LocalStorage States ---
  const [movies, setMovies] = useState<Movie[]>(() => {
    const saved = localStorage.getItem('kp_movies');
    return saved ? JSON.parse(saved) : INITIAL_MOVIES;
  });

  const [users, setUsers] = useState<User[]>(() => {
    const saved = localStorage.getItem('kp_users');
    return saved ? JSON.parse(saved) : INITIAL_USERS;
  });

  const [cards, setCards] = useState<Card[]>(() => {
    const saved = localStorage.getItem('kp_cards');
    return saved ? JSON.parse(saved) : INITIAL_CARDS;
  });

  const [ads, setAds] = useState<Ad[]>(() => {
    const saved = localStorage.getItem('kp_ads');
    return saved ? JSON.parse(saved) : INITIAL_ADS;
  });

  const [receipts, setReceipts] = useState<Receipt[]>(() => {
    const saved = localStorage.getItem('kp_receipts');
    return saved ? JSON.parse(saved) : INITIAL_RECEIPTS;
  });

  const [chats, setChats] = useState<ChatMessage[]>(() => {
    const saved = localStorage.getItem('kp_chats');
    return saved ? JSON.parse(saved) : [];
  });

  const [config, setConfig] = useState<AppConfig>(() => {
    const saved = localStorage.getItem('kp_config');
    return saved ? JSON.parse(saved) : DEFAULT_CONFIG;
  });

  const [activeUserId, setActiveUserId] = useState<string>(() => {
    const saved = localStorage.getItem('kp_active_user_id');
    return saved || 'user-owner'; // Default is Owner
  });

  const [savedMovies, setSavedMovies] = useState<string[]>(() => {
    const saved = localStorage.getItem('kp_saved_movies');
    return saved ? JSON.parse(saved) : [];
  });

  const [watchHistory, setWatchHistory] = useState<WatchHistoryItem[]>(() => {
    const saved = localStorage.getItem('kp_watch_history');
    return saved ? JSON.parse(saved) : [];
  });

  // Derived current user
  const currentUser = users.find(u => u.id === activeUserId) || users[0] || null;

  // --- Sync with LocalStorage on State Changes ---
  useEffect(() => {
    localStorage.setItem('kp_movies', JSON.stringify(movies));
  }, [movies]);

  useEffect(() => {
    localStorage.setItem('kp_users', JSON.stringify(users));
  }, [users]);

  useEffect(() => {
    localStorage.setItem('kp_cards', JSON.stringify(cards));
  }, [cards]);

  useEffect(() => {
    localStorage.setItem('kp_ads', JSON.stringify(ads));
  }, [ads]);

  useEffect(() => {
    localStorage.setItem('kp_receipts', JSON.stringify(receipts));
  }, [receipts]);

  useEffect(() => {
    localStorage.setItem('kp_chats', JSON.stringify(chats));
  }, [chats]);

  useEffect(() => {
    localStorage.setItem('kp_config', JSON.stringify(config));
  }, [config]);

  useEffect(() => {
    localStorage.setItem('kp_active_user_id', activeUserId);
  }, [activeUserId]);

  useEffect(() => {
    localStorage.setItem('kp_saved_movies', JSON.stringify(savedMovies));
  }, [savedMovies]);

  useEffect(() => {
    localStorage.setItem('kp_watch_history', JSON.stringify(watchHistory));
  }, [watchHistory]);

  // --- Movie Actions ---
  const addMovie = (newMovie: Omit<Movie, 'id' | 'views' | 'comments'>) => {
    const movie: Movie = {
      ...newMovie,
      id: `movie-${Date.now()}`,
      views: 0,
      comments: []
    };
    setMovies(prev => [movie, ...prev]);
  };

  const updateMovie = (updatedMovie: Movie) => {
    setMovies(prev => prev.map(m => m.id === updatedMovie.id ? updatedMovie : m));
  };

  const deleteMovie = (movieId: string) => {
    setMovies(prev => prev.filter(m => m.id !== movieId));
    setSavedMovies(prev => prev.filter(id => id !== movieId));
    setWatchHistory(prev => prev.filter(item => item.movieId !== movieId));
  };

  const addComment = (movieId: string, userName: string, text: string) => {
    const comment: Comment = {
      id: `comment-${Date.now()}`,
      userName,
      text,
      createdAt: new Date().toISOString()
    };
    setMovies(prev => prev.map(m => {
      if (m.id === movieId) {
        return { ...m, comments: [...m.comments, comment] };
      }
      return m;
    }));
  };

  const incrementViews = (movieId: string) => {
    setMovies(prev => prev.map(m => m.id === movieId ? { ...m, views: m.views + 1 } : m));
  };

  // --- Saved / History ---
  const toggleSavedMovie = (movieId: string) => {
    setSavedMovies(prev => {
      if (prev.includes(movieId)) {
        return prev.filter(id => id !== movieId);
      } else {
        return [...prev, movieId];
      }
    });
  };

  const addToHistory = (movieId: string, progress: number) => {
    setWatchHistory(prev => {
      const filtered = prev.filter(item => item.movieId !== movieId);
      const newItem: WatchHistoryItem = {
        id: `history-${Date.now()}`,
        movieId,
        progress,
        watchedAt: new Date().toISOString()
      };
      return [newItem, ...filtered];
    });
  };

  const clearHistory = () => {
    setWatchHistory([]);
  };

  // --- User Management ---
  const addUser = (newUser: User) => {
    setUsers(prev => [...prev, newUser]);
  };

  const updateUser = (updatedUser: User) => {
    setUsers(prev => prev.map(u => u.id === updatedUser.id ? updatedUser : u));
  };

  const deleteUser = (userId: string) => {
    setUsers(prev => prev.filter(u => u.id !== userId));
    if (activeUserId === userId) {
      setActiveUserId('user-owner');
    }
  };

  const setUserBlockedStatus = (userId: string, isBlocked: boolean) => {
    setUsers(prev => prev.map(u => u.id === userId ? { ...u, isBlocked } : u));
  };

  const setUserOnlineStatus = (userId: string, isOnline: boolean) => {
    setUsers(prev => prev.map(u => u.id === userId ? { ...u, isOnline } : u));
  };

  const setUserRole = (userId: string, role: 'owner' | 'admin' | 'user') => {
    setUsers(prev => prev.map(u => u.id === userId ? { ...u, role } : u));
  };

  const grantManualVip = (userId: string, days: number) => {
    setUsers(prev => prev.map(u => {
      if (u.id === userId) {
        const baseDate = u.vipUntil ? new Date(u.vipUntil) : new Date();
        if (baseDate < new Date()) {
          // If expired or null, start from today
          const newDate = new Date();
          newDate.setDate(newDate.getDate() + days);
          return { ...u, vipUntil: newDate.toISOString() };
        } else {
          // extend existing
          baseDate.setDate(baseDate.getDate() + days);
          return { ...u, vipUntil: baseDate.toISOString() };
        }
      }
      return u;
    }));
  };

  const switchActiveUser = (userId: string) => {
    setActiveUserId(userId);
  };

  // --- Financial Actions ---
  const addReceipt = (amount: number, cardNumber: string, imageUrl: string) => {
    if (!currentUser) return;
    const receipt: Receipt = {
      id: `receipt-${Date.now()}`,
      userId: currentUser.id,
      userName: currentUser.name,
      amount,
      cardNumber,
      imageUrl,
      status: 'pending',
      createdAt: new Date().toISOString()
    };
    setReceipts(prev => [receipt, ...prev]);

    // Send visual TG chat notification simulator
    addChatMessage(
      currentUser.id,
      currentUser.name,
      `Yangi VIP to'lov cheki yuborildi: ${amount.toLocaleString()} so'm. Tekshirish uchun yuborilgan karta: ${cardNumber}.`,
      'user'
    );
  };

  const approveReceipt = (receiptId: string) => {
    const receipt = receipts.find(r => r.id === receiptId);
    if (!receipt) return;

    // Set receipt status to approved
    setReceipts(prev => prev.map(r => r.id === receiptId ? { ...r, status: 'approved' } : r));

    // Grant VIP: for 15k give 30 days, for 35k give 90 days, for 120k give 365 days
    let days = 30;
    if (receipt.amount >= 120000) days = 365;
    else if (receipt.amount >= 35000) days = 90;

    grantManualVip(receipt.userId, days);

    // Notify user via chat
    const targetUser = users.find(u => u.id === receipt.userId);
    addChatMessage(
      receipt.userId,
      targetUser?.name || 'Foydalanuvchi',
      `Sizning to'lovingiz tasdiqlandi! Sizga ${days} kunga VIP statusi berildi. Tabriklaymiz! 🌟`,
      'admin'
    );
  };

  const rejectReceipt = (receiptId: string) => {
    const receipt = receipts.find(r => r.id === receiptId);
    if (!receipt) return;

    setReceipts(prev => prev.map(r => r.id === receiptId ? { ...r, status: 'rejected' } : r));

    // Notify user via chat
    const targetUser = users.find(u => u.id === receipt.userId);
    addChatMessage(
      receipt.userId,
      targetUser?.name || 'Foydalanuvchi',
      `Kechirasiz, siz yuborgan to'lov cheki bekor qilindi. Iltimos, ma'lumotlarni qayta tekshiring yoki adminga murojaat qiling. ❌`,
      'admin'
    );
  };

  const addCard = (newCard: Omit<Card, 'id'>) => {
    const card: Card = {
      ...newCard,
      id: `card-${Date.now()}`
    };
    setCards(prev => [...prev, card]);
  };

  const updateCard = (updatedCard: Card) => {
    setCards(prev => prev.map(c => c.id === updatedCard.id ? updatedCard : c));
  };

  const deleteCard = (cardId: string) => {
    setCards(prev => prev.filter(c => c.id !== cardId));
  };

  // --- Ad Actions ---
  const addAd = (newAd: Omit<Ad, 'id' | 'impressions'>) => {
    const ad: Ad = {
      ...newAd,
      id: `ad-${Date.now()}`,
      impressions: 0
    };
    setAds(prev => [...prev, ad]);
  };

  const updateAd = (updatedAd: Ad) => {
    setAds(prev => prev.map(a => a.id === updatedAd.id ? updatedAd : a));
  };

  const deleteAd = (adId: string) => {
    setAds(prev => prev.filter(a => a.id !== adId));
  };

  const incrementAdImpressions = (adId: string) => {
    setAds(prev => prev.map(a => a.id === adId ? { ...a, impressions: a.impressions + 1 } : a));
  };

  // --- Support Chat ---
  const addChatMessage = (userId: string, userName: string, text: string, sender: 'user' | 'admin') => {
    const msg: ChatMessage = {
      id: `msg-${Date.now()}`,
      userId,
      userName,
      text,
      sender,
      createdAt: new Date().toISOString()
    };
    setChats(prev => [...prev, msg]);
  };

  const clearChat = (userId: string) => {
    setChats(prev => prev.filter(c => c.userId !== userId));
  };

  const deleteChatMessage = (messageId: string) => {
    setChats(prev => prev.filter(c => c.id !== messageId));
  };

  const updateConfig = (newConfig: AppConfig) => {
    setConfig(newConfig);
  };

  return (
    <AppContext.Provider value={{
      movies,
      users,
      cards,
      ads,
      receipts,
      chats,
      config,
      currentUser,
      watchHistory,
      savedMovies,
      addMovie,
      updateMovie,
      deleteMovie,
      addComment,
      incrementViews,
      toggleSavedMovie,
      addToHistory,
      clearHistory,
      addUser,
      updateUser,
      deleteUser,
      setUserBlockedStatus,
      setUserOnlineStatus,
      setUserRole,
      grantManualVip,
      switchActiveUser,
      addReceipt,
      approveReceipt,
      rejectReceipt,
      addCard,
      updateCard,
      deleteCard,
      addAd,
      updateAd,
      deleteAd,
      incrementAdImpressions,
      addChatMessage,
      clearChat,
      deleteChatMessage,
      updateConfig
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
