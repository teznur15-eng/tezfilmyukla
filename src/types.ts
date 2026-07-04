export type MovieCategory = 'kino' | 'serial' | 'kdrama' | 'turk' | 'anime' | 'multfilm';

export interface Comment {
  id: string;
  userName: string;
  text: string;
  createdAt: string;
}

export interface Movie {
  id: string;
  title: string;
  year: number;
  genre: string;
  code: string; // Movie search code e.g. "2334"
  description: string;
  category: MovieCategory;
  imageUrl: string;
  link720: string; // regular stream link
  link1080: string; // VIP stream link
  rating: number;
  views: number;
  comments: Comment[];
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'owner' | 'admin' | 'user';
  vipUntil: string | null; // ISO Date String or null
  isBlocked: boolean;
  isOnline: boolean;
  balance: number;
}

export interface Receipt {
  id: string;
  userId: string;
  userName: string;
  amount: number;
  cardNumber: string;
  imageUrl: string; // Base64 or placeholder check
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
}

export interface Card {
  id: string;
  holder: string;
  number: string;
  bank: string;
  isActive: boolean;
}

export interface Ad {
  id: string;
  title: string;
  type: 'google' | 'telegram';
  content: string; // text or link
  imageUrl?: string;
  isActive: boolean;
  impressions: number;
}

export interface ChatMessage {
  id: string;
  userId: string;
  userName: string;
  text: string;
  sender: 'user' | 'admin';
  createdAt: string;
}

export interface AppConfig {
  primaryColor: string; // Hex color code
  logoUrl: string;
  copyrightText: string;
  mandatoryChannels: string[]; // channels like ["@kinohouse_uz", "@topkino_uz"]
  vipMessage: string; // text sent when bot responds about VIP subscription
  isBotMaintenance: boolean;
}

export interface WatchHistoryItem {
  id: string;
  movieId: string;
  progress: number; // in percentage (0 to 100)
  watchedAt: string;
}
