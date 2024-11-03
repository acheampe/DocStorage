'use client'
import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import LockIcon from '@/components/LockIcon'

interface User {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
}

interface File {
  id: number;
  name: string;
  uploaded_at: string;
}

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [recentFiles, setRecentFiles] = useState<File[]>([]);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');

    if (!token || !userData) {
      router.push('/login');
      return;
    }

    setUser(JSON.parse(userData));
    setRecentFiles([]);
  }, [router]);

  const handleLogout = () => {
    // Clear local storage
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // Redirect to home page
    router.push('/');
  };

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <div className="flex min-h-screen justify-center items-center">
      <LockIcon />
      <div className="fixed top-5 right-5 flex gap-4">
        <span 
          className="material-symbols-rounded text-gold text-5xl cursor-pointer hover:opacity-80"
          onClick={() => router.push('/settings')}
        >
          settings
        </span>
        <span 
          className="material-symbols-rounded text-gold text-5xl cursor-pointer hover:opacity-80" 
          onClick={handleLogout}
        >
          logout
        </span>
      </div>

      <div className="w-full max-w-3xl mx-auto flex flex-col items-center space-y-6 mt-32">
        {/* Search Bar */}
        <div className="w-full">
          <input
            type="text"
            placeholder="Search file"
            className="w-full p-4 border-4 border-navy rounded-2xl"
          />
        </div>

        {/* Recent Files Section */}
        <div className="w-full">
          <div className="bg-white rounded-2xl p-4 mb-4">
            <h2 className="text-4xl font-bold text-gold text-center">Recent Files</h2>
          </div>

          {recentFiles.length === 0 ? (
            <div className="text-center">
              <div className="grid grid-cols-3 gap-2 mb-4 max-w-lg mx-auto">
                {/* First Row */}
                <span className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]">slideshow</span>
                <span className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]">description</span>
                <span className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]">picture_as_pdf</span>
                {/* Second Row */}
                <span className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]">image</span>
                <span className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]">folder</span>
                <span className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]">article</span>
              </div>
              <h3 className="text-2xl font-bold text-navy">
                Upload files to store for DocStorage to display
              </h3>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-6">
              {recentFiles.slice(0, 6).map((file) => (
                <div key={file.id} className="p-4 border border-navy rounded-lg">
                  <h4 className="font-bold">{file.name}</h4>
                  <p className="text-sm">{file.uploaded_at}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between w-full">
          <button className="bg-navy text-white font-bold text-xl py-4 px-8 rounded-2xl hover:bg-opacity-90 transition-all">
            View All Files
          </button>
          <button className="bg-navy text-white font-bold text-xl py-4 px-8 rounded-2xl hover:bg-opacity-90 transition-all">
            Upload file
          </button>
        </div>
      </div>
    </div>
  );
}