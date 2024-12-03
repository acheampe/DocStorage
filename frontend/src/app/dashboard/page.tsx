'use client'
import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Footer from '@/components/Footer'
// import LockIcon from '@/components/LockIcon'
import ShareModal from '@/components/ShareModal'

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

interface PreviewData {
  type: string;
  url: string;
  filename: string;
  docId: number;
}

interface SharedFile {
  share_id: number;
  doc_id: number;
  filename: string;
  shared_date: string;
  shared_with: string;  // email of recipient
  mime_type: string;
  file_size: number;
  thumbnail_url?: string;
}

function getFileIcon(filename: string | undefined): string {
  if (!filename) return 'document'; // Default icon if no filename
  
  const ext = filename.split('.').pop()?.toLowerCase();
  
  switch (ext) {
      case 'pdf':
          return 'picture_as_pdf';
      case 'doc':
      case 'docx':
          return 'description';
      case 'xls':
      case 'xlsx':
          return 'table_chart';
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
          return 'image';
      case 'txt':
          return 'article';
      default:
          return 'document';
  }
}

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [recentFiles, setRecentFiles] = useState<File[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [imageUrls, setImageUrls] = useState<{ [key: number]: string }>({});
  const [searchResults, setSearchResults] = useState<File[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [shareModalOpen, setShareModalOpen] = useState<number>(-1);
  // const [sharedFiles, setSharedFiles] = useState<File[]>([]);
  const [sectionsCollapsed, setSectionsCollapsed] = useState({
    recent: false,
    shared: false,
    sharedByMe: false
  });
  const [sharedWithMeFiles, setSharedWithMeFiles] = useState<any[]>([]);
  const [sharedByMeFiles, setSharedByMeFiles] = useState<SharedFile[]>([]);

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
      setSuccessMessage('Files uploaded successfully!');
      // Clear the message after 3 seconds
      setTimeout(() => {
        setSuccessMessage(null);
        // Remove the query parameter
        router.replace('/dashboard');
      }, 3000);
    } else if (uploadStatus === 'partial') {
      setSuccessMessage('Some files were uploaded successfully');
      setTimeout(() => {
        setSuccessMessage(null);
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
        // Verify each file exists before adding to UI
        const verifiedFiles = [];
        for (const file of data.files) {
          const verifyResponse = await fetch(`http://127.0.0.1:5000/docs/file/${file.doc_id}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            },
            credentials: 'include'
          });
          if (verifyResponse.ok) {
            verifiedFiles.push({
              doc_id: file.doc_id,
              original_filename: file.original_filename,
              upload_date: file.upload_date,
              file_type: file.file_type
            });
          }
        }
        setRecentFiles(verifiedFiles);
      } catch (error) {
        console.error('Error fetching recent files:', error);
      }
    };

    if (user) {
      fetchRecentFiles();
    }
  }, [user]);

  useEffect(() => {
    const fetchSharedFiles = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
            console.error('No token found in localStorage');
            return;
        }
        
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            console.log('Decoded token payload:', payload);
        } catch (e) {
            console.error('Error decoding token:', e);
        }
        
        // Fetch files shared with me
        const withMeResponse = await fetch('http://127.0.0.1:5000/share/shared-with-me', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        });
        
        // Fetch files shared by me
        const byMeResponse = await fetch('http://127.0.0.1:5000/share/shared-by-me', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        });

        if (!withMeResponse.ok || !byMeResponse.ok) {
          console.error('Error fetching shared files');
          return;
        }

        const withMeData = await withMeResponse.json();
        const byMeData = await byMeResponse.json();

        console.log('Shared with me:', withMeData);
        console.log('Shared by me:', byMeData);

        // Verify each file exists before adding to state
        const verifiedWithMe = [];
        const verifiedByMe = [];

        for (const share of withMeData.shares || []) {
          try {
            const verifyResponse = await fetch(`http://127.0.0.1:5000/docs/file/${share.doc_id}`, {
              headers: { 'Authorization': `Bearer ${token}` },
              credentials: 'include'
            });
            if (verifyResponse.ok) {
              verifiedWithMe.push(share);
            }
          } catch (error) {
            console.error(`Error verifying shared file ${share.doc_id}:`, error);
          }
        }

        for (const share of byMeData.shares || []) {
          try {
            const verifyResponse = await fetch(`http://127.0.0.1:5000/docs/file/${share.doc_id}`, {
              headers: { 'Authorization': `Bearer ${token}` },
              credentials: 'include'
            });
            if (verifyResponse.ok) {
              verifiedByMe.push(share);
            }
          } catch (error) {
            console.error(`Error verifying shared file ${share.doc_id}:`, error);
          }
        }

        setSharedWithMeFiles(verifiedWithMe);
        setSharedByMeFiles(verifiedByMe);
      } catch (error) {
        console.error('Error fetching shared files:', error);
      }
    };

    if (user) {
      fetchSharedFiles();
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

  // Add debounced search
  useEffect(() => {
    const searchDocuments = async () => {
      if (!searchQuery.trim()) {
        setSearchResults([]);
        setIsSearching(false);
        return;
      }

      setIsSearching(true);
      setSearchError(null);

      try {
        const token = localStorage.getItem('token');
        const response = await fetch(
          `http://127.0.0.1:5000/search?q=${encodeURIComponent(searchQuery)}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            credentials: 'include'
          }
        );

        if (!response.ok) {
          throw new Error('Search failed');
        }

        const data = await response.json();
        
        // Verify each search result exists before adding to results
        const verifiedResults = [];
        for (const result of data.results) {
          const verifyResponse = await fetch(`http://127.0.0.1:5000/docs/file/${result.doc_id}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            },
            credentials: 'include'
          });
          
          if (verifyResponse.ok) {
            verifiedResults.push({
              doc_id: result.doc_id,
              original_filename: result.metadata.filename,
              upload_date: result.metadata.upload_date,
              file_type: result.metadata.file_type
            });
          }
        }
        
        setSearchResults(verifiedResults);
      } catch (error) {
        console.error('Error searching documents:', error);
        setSearchError('Failed to search documents');
      } finally {
        setIsSearching(false);
      }
    };

    const timeoutId = setTimeout(searchDocuments, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handlePreview = async (docId: number) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('No token found');
        return;
      }

      const response = await fetch(`http://127.0.0.1:5000/docs/preview/${docId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get('Content-Type') || '';
      const data = await response.blob();

      // Create preview data based on content type
      if (contentType.startsWith('image/')) {
        setPreviewData({
          type: 'image',
          url: URL.createObjectURL(data),
          filename: `Document ${docId}`,
          docId: docId
        });
      } else if (contentType === 'application/pdf') {
        setPreviewData({
          type: 'pdf',
          url: URL.createObjectURL(data),
          filename: `Document ${docId}`,
          docId: docId
        });
      } else {
        // For other file types, may need to download instead
        console.log('Unsupported preview type:', contentType);
        setPreviewData(null);
      }
    } catch (error) {
      console.error('Error previewing file:', error);
      setPreviewData(null);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const success = params.get('success');
    if (success) {
      setSuccessMessage(decodeURIComponent(success));
      setTimeout(() => setSuccessMessage(null), 3000);
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

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

      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg transition-all duration-500 ease-in-out z-50 flex items-center gap-2">
          <span className="material-symbols-rounded">check_circle</span>
          {successMessage}
        </div>
      )}

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
            {isSearching ? 'hourglass_empty' : 'search'}
          </span>
        </div>

        {searchError && (
          <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg">
            {searchError}
          </div>
        )}

        {/* Files Grid */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-[#002B5B]">
              {searchQuery ? 'Search Results' : 'Recent Files'}
            </h2>
            {!searchQuery && (
              <button 
                onClick={() => setSectionsCollapsed(prev => ({
                  ...prev,
                  recent: !prev.recent
                }))}
                className="text-navy hover:text-gold transition-colors"
                title={sectionsCollapsed.recent ? "Expand section" : "Collapse section"}
              >
                <span className="material-symbols-rounded">
                  {sectionsCollapsed.recent ? 'expand_more' : 'expand_less'}
                </span>
              </button>
            )}
          </div>
          {!searchQuery && (
            <Link
              href="/files"
              className="bg-[#002B5B] hover:bg-[#1B4B7D] text-white font-medium py-2 px-4 rounded"
            >
              View All Files
            </Link>
          )}
        </div>
        
        {!sectionsCollapsed.recent && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {/* Show either search results or recent files */}
            {(searchQuery ? searchResults : recentFiles).map((file) => (
              <div 
                key={file.doc_id} 
                className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer relative"
                onClick={() => handlePreview(file.doc_id)}
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
                <div className="flex justify-between items-center mt-2">
                  <p className="text-sm text-gray-600">
                    {new Date(file.upload_date).toLocaleDateString()}
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShareModalOpen(file.doc_id);
                    }}
                    className="text-navy hover:text-gold transition-colors"
                    title="Share this document"
                  >
                    <span className="material-symbols-rounded">share</span>
                  </button>
                </div>
              </div>
            ))}
            
            {/* Only show upload placeholders for recent files view */}
            {!searchQuery && Array.from({ length: Math.max(0, 6 - recentFiles.length) }).map((_, index) => (
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
        )}

        {/* Shared with Me Section */}
        {!searchQuery && (
          <>
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-[#002B5B]">Shared with Me</h2>
                <button 
                  onClick={() => setSectionsCollapsed(prev => ({
                    ...prev,
                    shared: !prev.shared
                  }))}
                  className="text-navy hover:text-gold transition-colors"
                >
                  <span className="material-symbols-rounded">
                    {sectionsCollapsed.shared ? 'expand_more' : 'expand_less'}
                  </span>
                </button>
              </div>
            </div>

            {!sectionsCollapsed.shared && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
                {sharedWithMeFiles.map((share) => (
                  <div 
                    key={share.share_id} 
                    className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer relative"
                    onClick={() => handlePreview(share.doc_id)}
                  >
                    {/* File preview/icon */}
                    <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                      <span className="material-symbols-rounded text-navy text-4xl">
                        {getFileIcon(share.filename)}
                      </span>
                    </div>
                    <h4 className="font-bold text-navy truncate">{share.filename}</h4>
                    <div className="flex justify-between items-center mt-2">
                      <p className="text-sm text-gray-600">
                        {new Date(share.created_at).toLocaleDateString()}
                      </p>
                      <span className="text-sm text-navy">
                        Shared by: {share.owner_id}
                      </span>
                    </div>
                  </div>
                ))}
                {sharedWithMeFiles.length === 0 && (
                  <div className="col-span-3 p-8 text-center text-gray-500">
                    No files have been shared with you yet.
                  </div>
                )}
              </div>
            )}

            {/* Shared by Me Section */}
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-[#002B5B]">Shared by Me</h2>
                <button 
                  onClick={() => setSectionsCollapsed(prev => ({
                    ...prev,
                    sharedByMe: !prev.sharedByMe
                  }))}
                  className="text-navy hover:text-gold transition-colors"
                >
                  <span className="material-symbols-rounded">
                    {sectionsCollapsed.sharedByMe ? 'expand_more' : 'expand_less'}
                  </span>
                </button>
              </div>
            </div>

            {!sectionsCollapsed.sharedByMe && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {sharedByMeFiles.map((share) => (
                  <div 
                    key={share.share_id} 
                    className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer relative"
                    onClick={() => handlePreview(share.doc_id)}
                  >
                    {/* File preview/icon */}
                    <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                      <span className="material-symbols-rounded text-navy text-4xl">
                        {getFileIcon(share.filename)}
                      </span>
                    </div>
                    <h4 className="font-bold text-navy truncate">{share.filename}</h4>
                    <div className="flex justify-between items-center mt-2">
                      <p className="text-sm text-gray-600">
                        {share.shared_date ? new Date(share.shared_date).toLocaleDateString() : 'N/A'}
                      </p>
                      <span className="text-sm text-navy">
                        Shared with: {share.shared_with || 'Unknown'}
                      </span>
                    </div>
                  </div>
                ))}
                {sharedByMeFiles.length === 0 && (
                  <div className="col-span-3 p-8 text-center text-gray-500">
                    You haven't shared any files yet.
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
      <Footer />

      {/* Preview Modal - Lower z-index */}
      {previewData && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40"
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
              <h3 className="text-xl font-bold truncate">{previewData.filename}</h3>
              <div className="flex items-center gap-2">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setShareModalOpen(previewData.docId);
                  }}
                  className="text-gray-500 hover:text-navy transition-colors"
                  title="Share this document"
                >
                  <span className="material-symbols-rounded">share</span>
                </button>
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
            </div>
            <div className="overflow-auto max-h-[calc(90vh-8rem)]">
              {previewData.type === 'image' ? (
                <img 
                  src={previewData.url} 
                  alt={previewData.filename}
                  className="max-w-full h-auto"
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

      {/* Share Modal - Higher z-index */}
      {shareModalOpen > -1 && (
        <ShareModal
          onClose={() => setShareModalOpen(-1)}
          selectedFiles={[shareModalOpen]}
          isBulkShare={false}
        />
      )}
    </div>
  );
}