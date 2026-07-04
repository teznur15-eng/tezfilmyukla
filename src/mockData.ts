import { Movie, User, Card, Ad, Receipt, AppConfig } from './types';

export const INITIAL_MOVIES: Movie[] = [
  {
    id: 'movie-1',
    title: 'Qasoskorlar: Intihosi (Avengers: Endgame)',
    year: 2019,
    genre: 'Fantastika, Jangari, Sarguzasht',
    code: '1001',
    description: 'Koinotning yarmini yo\'q qilgan Tanosga qarshi qolgan barcha qahramonlar birlashadi va vaqt bo\'ylab sayohat qilib, toshlarni qaytarishga harakat qilishadi.',
    category: 'kino',
    imageUrl: 'https://images.unsplash.com/photo-1594909122845-11baa439b7bf?auto=format&fit=crop&w=600&q=80',
    link720: 'https://www.w3schools.com/html/mov_bbb.mp4',
    link1080: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    rating: 8.9,
    views: 12450,
    comments: [
      { id: 'c1', userName: 'Asadbek', text: 'Juda zo\'r kino ekan! Oxiri juda ta\'sirli chiqibdi.', createdAt: '2026-06-20T12:30:00Z' },
      { id: 'c2', userName: 'Durdona', text: 'Iron Man qahramonligi unutilmas!', createdAt: '2026-06-21T14:45:00Z' }
    ]
  },
  {
    id: 'movie-2',
    title: 'Muhtasham Yuz Yil (Muhteşem Yüzyıl)',
    year: 2011,
    genre: 'Tarixiy, Drama, Melodrama',
    code: '1002',
    description: 'Usmoniylar imperiyasining eng qudratli sultoni - Sulton Sulaymon Qonuniy va uning kanizagi Hurram Sulton o\'rtasidagi muhabbat va saroy fitnalari haqida hikoya.',
    category: 'turk',
    imageUrl: 'https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=600&q=80',
    link720: 'https://www.w3schools.com/html/mov_bbb.mp4',
    link1080: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    rating: 8.4,
    views: 8400,
    comments: [
      { id: 'c3', userName: 'Feruza', text: 'Hurram Sulton rolini o\'ynagan aktrisa daho!', createdAt: '2026-06-22T08:15:00Z' }
    ]
  },
  {
    id: 'movie-3',
    title: 'Squid Game (Kalmar O\'yini)',
    year: 2021,
    genre: 'Triller, Drama, Sirlilik',
    code: '1003',
    description: 'Qarzga botgan 456 nafar ishtirokchi ulkan pul mukofoti uchun bolalar o\'yinlarida qatnashadi. Ammo o\'yinda yutqazganlar hayotdan ko\'z yumadi.',
    category: 'kdrama',
    imageUrl: 'https://images.unsplash.com/photo-1627856013091-fed6e4e30025?auto=format&fit=crop&w=600&q=80',
    link720: 'https://www.w3schools.com/html/mov_bbb.mp4',
    link1080: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    rating: 8.7,
    views: 15900,
    comments: [
      { id: 'c4', userName: 'Sardor', text: 'Triller ishqibozlari uchun haqiqiy durdona.', createdAt: '2026-06-23T10:20:00Z' }
    ]
  },
  {
    id: 'movie-4',
    title: 'Naruto Shippuden',
    year: 2007,
    genre: 'Anime, Sarguzasht, Jangari',
    code: '1004',
    description: 'Yosh ninja Naruto Uzumaki o\'z qishlog\'ida eng buyuk yetakchi - Hokage bo\'lish va do\'stlarini qutqarish uchun barcha to\'siqlarni yengib o\'tadi.',
    category: 'anime',
    imageUrl: 'https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80',
    link720: 'https://www.w3schools.com/html/mov_bbb.mp4',
    link1080: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
    rating: 9.1,
    views: 23100,
    comments: [
      { id: 'c5', userName: 'Akrom', text: 'Hayotiy darslarga boy ajoyib anime!', createdAt: '2026-06-24T11:05:00Z' }
    ]
  },
  {
    id: 'movie-5',
    title: 'Muzlik Davri 5 (Ice Age: Collision Course)',
    year: 2016,
    genre: 'Multfilm, Komediya, Sarguzasht',
    code: '1005',
    description: 'Skret yong\'oq ortidan quvib, tasodifan koinotga chiqib ketadi va yerga xavf soluvchi meteoritlarni yo\'naltirib yuboradi. Qahramonlarimiz yana birlashadi.',
    category: 'multfilm',
    imageUrl: 'https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80',
    link720: 'https://www.w3schools.com/html/mov_bbb.mp4',
    link1080: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
    rating: 7.2,
    views: 9320,
    comments: []
  },
  {
    id: 'movie-6',
    title: 'Sherlok Xolms (Sherlock TV Series)',
    year: 2010,
    genre: 'Detektiv, Drama, Jinoyat',
    code: '1006',
    description: 'Mashhur detektiv Sherlok Xolms va uning hamrohi Doktor Jon Vatson XXI asr Londonda sodir etilayotgan eng murakkab jinoyatlarni fosh etishadi.',
    category: 'serial',
    imageUrl: 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80',
    link720: 'https://www.w3schools.com/html/mov_bbb.mp4',
    link1080: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4',
    rating: 9.2,
    views: 18700,
    comments: [
      { id: 'c6', userName: 'Elyor', text: 'Benedikt Kamberbetch rolini ideal ijro etgan!', createdAt: '2026-06-24T16:50:00Z' }
    ]
  }
];

export const INITIAL_USERS: User[] = [
  {
    id: 'user-owner',
    name: 'Firdavs Jigarim',
    email: 'tuyginovsardor4@gmail.com', // Active user email provided in context
    role: 'owner',
    vipUntil: '2028-12-31T23:59:59Z',
    isBlocked: false,
    isOnline: true,
    balance: 150000
  },
  {
    id: 'user-admin',
    name: 'Sardor Admin',
    email: 'admin@kinoportal.uz',
    role: 'admin',
    vipUntil: '2027-01-01T00:00:00Z',
    isBlocked: false,
    isOnline: true,
    balance: 50000
  },
  {
    id: 'user-3',
    name: 'Bekzod Alimov',
    email: 'bekzod@gmail.com',
    role: 'user',
    vipUntil: null,
    isBlocked: false,
    isOnline: false,
    balance: 12000
  },
  {
    id: 'user-4',
    name: 'Jasur Shodiyev',
    email: 'jasur@gmail.com',
    role: 'user',
    vipUntil: '2026-07-25T17:00:00Z',
    isBlocked: false,
    isOnline: true,
    balance: 0
  },
  {
    id: 'user-5',
    name: 'Nozima Karimova',
    email: 'nozima@gmail.com',
    role: 'user',
    vipUntil: null,
    isBlocked: true,
    isOnline: false,
    balance: 5000
  }
];

export const INITIAL_CARDS: Card[] = [
  {
    id: 'card-1',
    holder: 'XALQ BANKI (Firdavs T.)',
    number: '8600 1204 5678 9012',
    bank: 'Xalq Banki',
    isActive: true
  },
  {
    id: 'card-2',
    holder: 'TBC BANK (Sardor T.)',
    number: '9860 0301 2244 8899',
    bank: 'TBC Bank',
    isActive: true
  }
];

export const INITIAL_ADS: Ad[] = [
  {
    id: 'ad-1',
    title: 'Telegram Kanal Reklamasi',
    type: 'telegram',
    content: 'Eng so\'nggi premyerlar va yangiliklar faqat bizning rasmiy @kinoport_uz kanalimizda! Obuna bo\'ling va sovg\'alarga ega bo\'ling!',
    imageUrl: 'https://images.unsplash.com/photo-1614680376593-902f74fa0d41?auto=format&fit=crop&w=600&q=80',
    isActive: true,
    impressions: 452
  },
  {
    id: 'ad-2',
    title: 'Google Premium Banner',
    type: 'google',
    content: 'Vip Obuna sotib oling va zerikarli reklamalardan butunlay xolos bo\'ling! Bor-yo\'g\'i 15,000 so\'m/oy.',
    isActive: true,
    impressions: 1120
  }
];

export const INITIAL_RECEIPTS: Receipt[] = [
  {
    id: 'receipt-1',
    userId: 'user-3',
    userName: 'Bekzod Alimov',
    amount: 15000,
    cardNumber: '8600 1204 5678 9012',
    imageUrl: 'https://images.unsplash.com/photo-1628157582853-a796fa650a6a?auto=format&fit=crop&w=600&q=80',
    status: 'pending',
    createdAt: '2026-06-24T15:30:00Z'
  },
  {
    id: 'receipt-2',
    userId: 'user-5',
    userName: 'Nozima Karimova',
    amount: 45000,
    cardNumber: '9860 0301 2244 8899',
    imageUrl: 'https://images.unsplash.com/photo-1554415707-6e8cfc93fe23?auto=format&fit=crop&w=600&q=80',
    status: 'approved',
    createdAt: '2026-06-23T09:15:00Z'
  }
];

export const DEFAULT_CONFIG: AppConfig = {
  primaryColor: '#6366F1', // Indigo text/buttons
  logoUrl: 'https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?auto=format&fit=crop&w=120&q=80',
  copyrightText: 'Barcha huquqlar himoyalangan. © 2026 KinoPortal. Admin bilan bog\'lanish: @kinoportal_admin_bot',
  mandatoryChannels: ['@kinoportal_rasmiy', '@kino_kodlar_dunyo'],
  vipMessage: 'Premium obuna narxlari:\n1 oylik - 15,000 so\'m\n3 oylik - 35,000 so\'m\nYillik - 120,000 so\'m\n\nTo\'lov qilish uchun profil bo\'limidan kartaga pul o\'tkazib chekini yuboring yoki quyidagi kartalarga to\'lab, botga yuboring!',
  isBotMaintenance: false
};
