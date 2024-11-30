'use client'
import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Footer from '@/components/Footer'
// import LockIcon from '@/components/LockIcon'
import ImagePreview from '@/components/ImagePreview'

interface User {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
}

interface File {
  doc_id: number;
  original_filename: string;
  upload_date: string;
  file_type: string;
}

function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return 'picture_as_pdf';
    case 'doc':
    case 'docx':
      return 'description';
    case 'ppt':
    case 'pptx':
      return 'slideshow';
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
      return 'image';
    default:
      return 'article';
  }
}

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [recentFiles, setRecentFiles] = useState<File[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<{id: number, filename: string} | null>(null);

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
        router.replace('/dashboard');
      }, 3000);
    } else if (uploadStatus === 'partial') {
      setUploadMessage('Some files were uploaded successfully');
      setTimeout(() => {
        setUploadMessage(null);
        router.replace('/dashboard');
      }, 3000);
    }
  }, [router]);

  useEffect(() => {
    const fetchRecentFiles = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch('http://127.0.0.1:5000/docs/recent', {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Failed to fetch recent files');
        }
        const data = await response.json();
        setRecentFiles(data.files.map((file: { 
          doc_id: number; 
          original_filename: string; 
          upload_date: string;
          file_type: string;
        }) => ({
          doc_id: file.doc_id,
          original_filename: file.original_filename,
          upload_date: file.upload_date,
          file_type: file.file_type
        })));
      } catch (error) {
        console.error('Error fetching recent files:', error);
      }
    };

    if (user) {
      fetchRecentFiles();
    }
  }, [user]);

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
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-navy">Recent Files</h2>
            {recentFiles.length > 0 && (
              <Link 
                href="/files"
                className="bg-navy text-white px-6 py-2 rounded-lg hover:bg-opacity-90 transition-all"
                title="View all your stored files"
              >
                View All Files
              </Link>
            )}
          </div>
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
              {recentFiles.map((file) => (
                <div 
                  key={file.doc_id} 
                  className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer flex flex-col"
                  onClick={() => {
                    if (file.file_type.startsWith('image/')) {
                      setPreviewImage({
                        id: file.doc_id,
                        filename: file.original_filename
                      });
                    }
                  }}
                >
                  <div className="mb-2">
                    {file.file_type.startsWith('image/') ? (
                      <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50 relative">
                        <img 
                          src={`http://127.0.0.1:5000/docs/file/${file.doc_id}?token=${localStorage.getItem('token')}`}
                          alt={file.original_filename}
                          className="w-full h-40 object-cover rounded"
                          crossOrigin="use-credentials"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                            const parent = target.parentElement;
                            if (parent) {
                              const icon = document.createElement('span');
                              icon.className = 'material-symbols-rounded text-navy text-4xl';
                              icon.textContent = getFileIcon(file.original_filename);
                              parent.appendChild(icon);
                            }
                          }}
                        />
                      </div>
                    ) : (
                      <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                        <span className="material-symbols-rounded text-navy text-4xl">
                          {getFileIcon(file.original_filename)}
                        </span>
                      </div>
                    )}
                    <h4 className="font-bold text-navy truncate">{file.original_filename}</h4>
                  </div>
                  <p className="text-sm text-gray-600 mt-auto">
                    {new Date(file.upload_date).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
      <Footer />
      {previewImage && (
        <ImagePreview
          src={`http://127.0.0.1:5000/docs/file/${previewImage.id}`}
          alt={previewImage.filename}
          onClose={() => setPreviewImage(null)}
        />
      )}
    </div>
  );
}