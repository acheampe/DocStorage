'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Navigation() {
  const router = useRouter();

  const handleLogout = () => {
    localStorage.clear();
    router.push('/');
  };

  return (
    <nav className="bg-navy p-4">
      <div className="container mx-auto flex justify-between items-center">
        <Link href="/dashboard" className="text-gold text-2xl font-bold">
          DocStorage
        </Link>
        <div className="flex items-center gap-6">
          <Link 
            href="/files" 
            className="text-white hover:text-gold transition-colors"
          >
            All Files
          </Link>
          <Link 
            href="/settings" 
            className="text-white hover:text-gold transition-colors"
          >
            Settings
          </Link>
          <button 
            onClick={handleLogout} 
            className="text-white hover:text-gold transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
} 