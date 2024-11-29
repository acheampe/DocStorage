'use client'
import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Footer from '@/components/Footer'
// import LockIcon from '@/components/LockIcon'

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
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [recentFiles, setRecentFiles] = useState<File[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  useEffect(() => {
    try {
      const userData = localStorage.getItem('user');
      if (!userData) {
        router.push('/login');
        return;
      }
      const parsedUser = JSON.parse(userData);
      if (!parsedUser || !parsedUser.user_id) {
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        router.push('/login');
        return;
      }
      setUser(parsedUser);
    } catch (err) {
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      router.push('/login');
    }
  }, [router]);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const uploadStatus = searchParams.get('upload');
    
    if (uploadStatus === 'success') {
      setUploadMessage('Files uploaded successfully!');
      // Clear the message after 3 seconds
      setTimeout(() => {
        setUploadMessage(null);
        // Remove the query parameter
        router.replace('/dashboard', undefined, { shallow: true });
      }, 3000);
    } else if (uploadStatus === 'partial') {
      setUploadMessage('Some files were uploaded successfully');
      setTimeout(() => {
        setUploadMessage(null);
        router.replace('/dashboard', undefined, { shallow: true });
      }, 3000);
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    router.push('/');
  };

  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Navigation Bar */}
      <nav className="bg-navy p-4">
        <div className="container mx-auto flex justify-between items-center">
          <Link href="/dashboard" className="text-gold text-2xl font-bold" title="Return to dashboard home">
            DocStorage
          </Link>
          <div className="flex items-center gap-6">
            <Link 
              href="/settings" 
              className="text-white hover:text-gold transition-colors"
              title="Update your profile information and password"
            >
              Settings
            </Link>
            <button 
              onClick={handleLogout} 
              className="text-white hover:text-gold transition-colors"
              title="Sign out of your account"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-grow container mx-auto p-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-bold text-navy">
            Welcome, {user?.first_name}!
          </h1>
          <Link 
            href="/uploadFiles"
            className="bg-navy text-white px-6 py-2 rounded-lg hover:bg-opacity-90"
            title="Upload new documents to your storage"
          >
            Upload Files
          </Link>
        </div>

        {/* Search Bar */}
        <div className="relative mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search files..."
            className="w-full p-4 border-4 border-navy rounded-2xl pl-12"
            title="Search through all your files"
          />
          <span 
            className="material-symbols-rounded absolute left-4 top-1/2 -translate-y-1/2 text-navy opacity-50"
            title="Search icon"
          >
            search
          </span>
        </div>

        {uploadMessage && (
          <div className="mb-6 p-4 bg-green-100 text-green-700 rounded-lg text-center transition-opacity duration-500">
            {uploadMessage}
          </div>
        )}

        {/* Recent Files Section */}
        <section className="bg-white rounded-lg shadow-xl p-6">
          <h2 className="text-2xl font-bold text-navy mb-4">Recent Files</h2>
          {recentFiles.length === 0 ? (
            <div className="text-center">
              <div className="grid grid-cols-3 gap-2 mb-4 max-w-lg mx-auto">
                <span 
                  className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]"
                  title="Store and view presentations"
                >
                  slideshow
                </span>
                <span 
                  className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]"
                  title="Store and view documents"
                >
                  description
                </span>
                <span 
                  className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]"
                  title="Store and view PDFs"
                >
                  picture_as_pdf
                </span>
                <span 
                  className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]"
                  title="Store and view images"
                >
                  image
                </span>
                <span 
                  className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]"
                  title="Organize files in folders"
                >
                  folder
                </span>
                <span 
                  className="material-symbols-rounded text-navy opacity-20 w-24 h-24 flex items-center justify-center !text-[100px]"
                  title="Store and view articles"
                >
                  article
                </span>
              </div>
              <h3 className="text-2xl font-bold text-navy mb-4">
                Upload files to store for DocStorage to display
              </h3>
              <Link 
                href="/files"
                className="inline-block bg-navy text-white px-6 py-2 rounded-lg hover:bg-opacity-90 transition-all"
                title="View all your stored files"
              >
                View All Files
              </Link>
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
        </section>
      </main>
      <Footer />
    </div>
  );
}