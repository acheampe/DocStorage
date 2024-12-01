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
  const [imageUrls, setImageUrls] = useState<{ [key: number]: string }>({});
  const [previewUrls, setPreviewUrls] = useState<{ [key: number]: string }>({});
  const [previewData, setPreviewData] = useState<{
    type: string;
    url: string;
    filename: string;
  } | null>(null);

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

  const fetchThumbnail = async (fileId: number): Promise<string> => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/docs/file/${fileId}/thumbnail`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const blob = await response.blob();
      return URL.createObjectURL(blob);
    } catch (error) {
      console.error('Error fetching thumbnail:', error);
      // Return a placeholder image URL or null
      return '/placeholder-image.png';
    }
  };

  useEffect(() => {
    const loadImages = async () => {
      const newImageUrls: { [key: number]: string } = {};
      
      for (const file of recentFiles) {
        try {
          const thumbnailUrl = await fetchThumbnail(file.doc_id);
          if (thumbnailUrl) {
            newImageUrls[file.doc_id] = thumbnailUrl;
          }
        } catch (error) {
          console.error(`Error loading thumbnail for file ${file.doc_id}:`, error);
        }
      }
      
      setImageUrls(newImageUrls);
    };

    if (recentFiles.length > 0) {
      loadImages();
    }

    return () => {
      Object.values(imageUrls).forEach(url => URL.revokeObjectURL(url));
    };
  }, [recentFiles]);

  const fetchFullImage = async (fileId: number): Promise<string> => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://127.0.0.1:5000/docs/file/${fileId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const blob = await response.blob();
      return URL.createObjectURL(blob);
    } catch (error) {
      console.error('Error fetching full image:', error);
      return '/placeholder-image.png';
    }
  };

  useEffect(() => {
    if (previewImage) {
      fetchFullImage(previewImage.id).then(url => {
        setPreviewUrls(prev => ({
          ...prev,
          [previewImage.id]: url
        }));
      });
    }
    
    // Cleanup function
    return () => {
      if (previewImage && previewUrls[previewImage.id]) {
        URL.revokeObjectURL(previewUrls[previewImage.id]);
      }
    };
  }, [previewImage]);

  const handlePreview = async (file: File) => {
    try {
      const token = localStorage.getItem('token');
      
      // For Office documents and text files, include token in URL
      if (
        file.file_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || // docx
        file.file_type === 'application/msword' || // doc
        file.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || // xlsx
        file.file_type === 'application/vnd.ms-excel' || // xls
        file.file_type === 'application/vnd.openxmlformats-officedocument.presentationml.presentation' || // pptx
        file.file_type === 'application/vnd.ms-powerpoint' || // ppt
        file.file_type === 'text/plain' // txt
      ) {
        // Create a blob URL with authorization
        const response = await fetch(`http://127.0.0.1:5000/docs/file/${file.doc_id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) throw new Error('Failed to fetch file');
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        // Open in new tab and clean up after delay
        window.open(url, '_blank');
        setTimeout(() => {
          URL.revokeObjectURL(url);
        }, 1000);
        return;
      }

      // For other file types (images, PDFs), continue with existing preview logic
      const response = await fetch(`http://127.0.0.1:5000/docs/file/${file.doc_id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to fetch file');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      if (file.file_type.startsWith('image/')) {
        setPreviewData({
          type: 'image',
          url,
          filename: file.original_filename
        });
      } else if (file.file_type === 'application/pdf') {
        setPreviewData({
          type: 'pdf',
          url,
          filename: file.original_filename
        });
      }
    } catch (error) {
      console.error('Error previewing file:', error);
    }
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
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-[#002B5B]">Recent Files</h2>
          <Link
            href="/files"
            className="bg-[#002B5B] hover:bg-[#1B4B7D] text-white font-medium py-2 px-4 rounded"
          >
            View All Files
          </Link>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {recentFiles.slice(0, 6).map((file) => (
            <div 
              key={file.doc_id} 
              className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer"
              onClick={() => handlePreview(file)}
            >
              <div className="mb-2">
                {file.file_type.startsWith('image/') ? (
                  <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50 relative">
                    {imageUrls[file.doc_id] ? (
                      <img 
                        src={imageUrls[file.doc_id]}
                        alt={file.original_filename}
                        className="w-full h-40 object-cover rounded"
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
                    ) : (
                      <span className="material-symbols-rounded text-navy text-4xl animate-pulse">
                        hourglass_empty
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                    <span className="material-symbols-rounded text-navy text-4xl">
                      {getFileIcon(file.original_filename)}
                    </span>
                  </div>
                )}
              </div>
              <h4 className="font-bold text-navy truncate">{file.original_filename}</h4>
              <p className="text-sm text-gray-600 mt-auto">
                {new Date(file.upload_date).toLocaleDateString()}
              </p>
            </div>
          ))}
          {Array.from({ length: Math.max(0, 6 - recentFiles.length) }).map((_, index) => (
            <Link
              key={`empty-${index}`}
              href="/uploadFiles"
              className="p-4 border-2 border-dashed border-navy rounded-lg hover:border-gold transition-colors cursor-pointer flex flex-col"
            >
              <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                <span className="material-symbols-rounded text-navy text-4xl">
                  add_circle
                </span>
              </div>
              <h4 className="font-bold text-navy text-center">Upload More Files</h4>
              <p className="text-sm text-gray-600 mt-auto text-center">
                Click to add files
              </p>
            </Link>
          ))}
        </div>
      </main>
      <Footer />
      {previewData && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => {
            URL.revokeObjectURL(previewData.url);
            setPreviewData(null);
          }}
        >
          <div 
            className="bg-white rounded-lg p-4 max-w-4xl max-h-[90vh] w-full mx-4 overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-2 flex-1 mr-4">
                <h3 className="text-xl font-bold truncate">{previewData.filename}</h3>
              </div>
              <button 
                onClick={() => {
                  URL.revokeObjectURL(previewData.url);
                  setPreviewData(null);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <span className="material-symbols-rounded">close</span>
              </button>
            </div>
            <div className="overflow-auto max-h-[calc(90vh-8rem)]">
              {previewData.type === 'image' ? (
                <img 
                  src={previewData.url} 
                  alt={previewData.filename}
                  className="max-w-full h-auto mx-auto"
                />
              ) : previewData.type === 'pdf' ? (
                <iframe
                  src={previewData.url}
                  className="w-full h-[80vh]"
                  title={previewData.filename}
                />
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}