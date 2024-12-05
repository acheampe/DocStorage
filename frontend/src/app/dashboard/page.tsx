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
  original_filename: string;
  display_name: string;
  filename?: string;
  shared_date: string;
  shared_with: string;
  file_type?: string;
}

interface ImageUrls {
  [key: number]: string;
}

function getFileIcon(filename: string | undefined): string {
  if (!filename) return 'description'; // Default icon
  
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
      return 'description';
  }
}

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [recentFiles, setRecentFiles] = useState<File[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [imageUrls, setImageUrls] = useState<ImageUrls>({});
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
        if (!token) {
          console.error('No token found');
          return;
        }

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
        setRecentFiles(data.files || []);

        // Only fetch thumbnails for image files
        const imageFiles = data.files.filter((file: File) => file.file_type?.startsWith('image/'));
        
        if (imageFiles.length > 0) {
          const thumbnailPromises = imageFiles.map(async (file: File) => {
            try {
              const thumbnailUrl = await fetchThumbnail(file.doc_id);
              return { id: file.doc_id, url: thumbnailUrl };
            } catch (error) {
              console.error(`Error fetching thumbnail for file ${file.doc_id}:`, error);
              return null;
            }
          });

          const thumbnails = await Promise.all(thumbnailPromises);
          const newImageUrls: ImageUrls = {};
          thumbnails.forEach(thumb => {
            if (thumb) {
              newImageUrls[thumb.id] = thumb.url;
            }
          });
          setImageUrls(newImageUrls);
        }

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
          console.error('No token found');
          return;
        }

        // Fetch files shared with me (using the correct endpoint)
        const withMeResponse = await fetch('http://127.0.0.1:5000/share/shared-with-me', {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        });

        // Fetch files shared by me (using the correct endpoint)
        const byMeResponse = await fetch('http://127.0.0.1:5000/share/shared-by-me', {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        });

        if (!withMeResponse.ok || !byMeResponse.ok) {
          throw new Error('Failed to fetch shared files');
        }

        const withMeData = await withMeResponse.json();
        const byMeData = await byMeResponse.json();

        console.log('Shared with me:', withMeData);
        console.log('Shared by me:', byMeData);

        // Update state with the fetched data
        setSharedWithMeFiles(withMeData.shares || []);
        setSharedByMeFiles(byMeData.shares || []);

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

  const fetchThumbnail = async (docId: number, isShared: boolean = false) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        isShared 
          ? `http://127.0.0.1:5000/share/file/${docId}/thumbnail`
          : `http://127.0.0.1:5000/docs/file/${docId}/thumbnail`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const blob = await response.blob();
      return URL.createObjectURL(blob);
    } catch (error) {
      console.error('Error fetching thumbnail:', error);
      return '/placeholder-image.png';
    }
  };

  useEffect(() => {
    const loadImages = async () => {
      const newImageUrls: ImageUrls = {};
      
      // Load thumbnails only for image files in recent files
      const recentImageFiles = recentFiles.filter(file => file.file_type?.startsWith('image/'));
      for (const file of recentImageFiles) {
        try {
          const thumbnailUrl = await fetchThumbnail(file.doc_id, false);
          if (thumbnailUrl) {
            newImageUrls[file.doc_id] = thumbnailUrl;
          }
        } catch (error) {
          console.error(`Error loading thumbnail for file ${file.doc_id}:`, error);
        }
      }
      
      // Load thumbnails only for image files in shared files
      const sharedImageFiles = sharedWithMeFiles.filter(file => file.file_type?.startsWith('image/'));
      for (const file of sharedImageFiles) {
        try {
          const thumbnailUrl = await fetchThumbnail(file.doc_id, true);
          if (thumbnailUrl) {
            newImageUrls[file.doc_id] = thumbnailUrl;
          }
        } catch (error) {
          console.error(`Error loading thumbnail for shared file ${file.doc_id}:`, error);
        }
      }
      
      setImageUrls(newImageUrls);
    };

    if (recentFiles.length > 0 || sharedWithMeFiles.length > 0) {
      loadImages();
    }

    return () => {
      Object.values(imageUrls).forEach(url => URL.revokeObjectURL(url));
    };
  }, [recentFiles, sharedWithMeFiles]);

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
        const userData = localStorage.getItem('user');
        const user = userData ? JSON.parse(userData) : null;

        if (!user?.user_id) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `http://127.0.0.1:5000/docs/search?q=${encodeURIComponent(searchQuery)}`,
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
        setSearchResults(data.results.map((result: any) => ({
          doc_id: result.doc_id,
          original_filename: result.metadata.filename,
          upload_date: result.metadata.upload_date,
          file_type: result.metadata.file_type,
          shared_by: result.metadata.owner_id,
          shared_with: result.metadata.recipient_id
        })));
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

  const handlePreview = async (docId: number, isSharedWithMe: boolean = false, filename: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('No token found');
        return;
      }

      // Get file extension
      const fileExt = filename.split('.').pop()?.toLowerCase();
      
      // Define previewable types
      const previewableTypes = {
        image: ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
        pdf: ['pdf'],
        text: ['txt', 'md', 'csv']
      };

      // Check if file is previewable
      const isPreviewable = Object.values(previewableTypes)
        .flat()
        .includes(fileExt || '');

      // Use appropriate endpoints based on whether the file is shared
      const endpoint = isSharedWithMe 
        ? `http://127.0.0.1:5000/share/preview/${docId}`
        : `http://127.0.0.1:5000/docs/file/${docId}`;
      
      // For non-previewable files, ask for download first
      if (!isPreviewable) {
        const userConfirmed = window.confirm(
          `"${filename}" cannot be previewed in the browser. Would you like to download it instead?`
        );
        
        if (!userConfirmed) {
          return;
        }

        const downloadResponse = await fetch(endpoint, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': '*/*'
          },
          credentials: 'include'
        });

        if (!downloadResponse.ok) {
          throw new Error(`Download failed: ${downloadResponse.status} ${downloadResponse.statusText}`);
        }

        const blob = await downloadResponse.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        return;
      }

      // For previewable files, fetch and set preview data
      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': '*/*'
        },
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`File access failed: ${response.status} ${response.statusText}`);
      }

      const contentType = response.headers.get('Content-Type') || '';
      const data = await response.blob();

      if (contentType.startsWith('image/')) {
        setPreviewData({
          type: 'image',
          url: URL.createObjectURL(data),
          filename: filename,
          docId: docId
        });
      } else if (contentType === 'application/pdf') {
        setPreviewData({
          type: 'pdf',
          url: URL.createObjectURL(data),
          filename: filename,
          docId: docId
        });
      } else if (contentType.startsWith('text/')) {
        const text = await data.text();
        setPreviewData({
          type: 'text',
          url: text,
          filename: filename,
          docId: docId
        });
      } else {
        const userConfirmed = window.confirm(
          `"${filename}" cannot be previewed in the browser. Would you like to download it instead?`
        );
        
        if (userConfirmed) {
          const url = window.URL.createObjectURL(data);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        }
      }
    } catch (error) {
      console.error('Error handling file:', error);
      alert(error instanceof Error ? error.message : 'Failed to handle file');
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
            {(searchQuery ? searchResults : recentFiles).map((file) => (
              <div 
                key={file.doc_id} 
                className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer relative"
                onClick={() => handlePreview(file.doc_id, false, file.original_filename)}
              >
                <div className="mb-2">
                  {file.file_type?.startsWith('image/') ? (
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
                        <span className="material-symbols-rounded text-navy text-4xl">
                          {getFileIcon(file.original_filename)}
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
                    className="material-symbols-rounded text-navy hover:text-gold transition-colors cursor-pointer"
                    title="Share this document"
                  >
                    <span className="material-symbols-rounded">share</span>
                  </button>
                </div>
              </div>
            ))}
            
            {/* Upload placeholders */}
            {!searchQuery && Array.from({ length: Math.max(0, 6 - recentFiles.length) }).map((_, index) => (
              <Link
                key={`empty-${index}`}
                href="/uploadFiles"
                className="p-4 border-2 border-dashed border-navy rounded-lg hover:border-gold transition-colors"
              >
                <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                  <span className="material-symbols-rounded text-navy text-4xl">
                    add_circle
                  </span>
                </div>
                <h4 className="font-bold text-navy text-center">Upload More Files</h4>
                <p className="text-sm text-gray-600 text-center">Click to add files</p>
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
                    onClick={() => handlePreview(share.doc_id, true, share.filename)}
                  >
                    <div className="mb-2">
                      {share.file_type?.startsWith('image/') ? (
                        <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50 relative">
                          {imageUrls[share.doc_id] ? (
                            <img 
                              src={imageUrls[share.doc_id]}
                              alt={share.filename}
                              className="w-full h-40 object-cover rounded"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                                const parent = target.parentElement;
                                if (parent) {
                                  const icon = document.createElement('span');
                                  icon.className = 'material-symbols-rounded text-navy text-4xl';
                                  icon.textContent = getFileIcon(share.filename);
                                  parent.appendChild(icon);
                                }
                              }}
                            />
                          ) : (
                            <span className="material-symbols-rounded text-navy text-4xl">
                              {getFileIcon(share.filename)}
                            </span>
                          )}
                        </div>
                      ) : (
                        <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                          <span className="material-symbols-rounded text-navy text-4xl">
                            {getFileIcon(share.filename)}
                          </span>
                        </div>
                      )}
                    </div>
                    <h4 className="font-bold text-navy truncate">{share.filename}</h4>
                    <div className="flex justify-between items-center mt-2">
                      <p className="text-sm text-gray-600">
                        {new Date(share.shared_date).toLocaleDateString()}
                      </p>
                      <p className="text-sm text-navy">
                        Shared by: {share.owner_id}
                      </p>
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
                    onClick={() => handlePreview(share.doc_id, false, share.original_filename)}
                  >
                    <div className="mb-2">
                      <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                        <span className="material-symbols-rounded text-navy text-4xl">
                          {getFileIcon(share.original_filename)}
                        </span>
                      </div>
                    </div>
                    <h4 className="font-bold text-navy truncate">{share.original_filename}</h4>
                    <div className="flex justify-between items-center mt-2">
                      <p className="text-sm text-gray-600">
                        {new Date(share.shared_date).toLocaleDateString()}
                      </p>
                      <span className="text-sm text-navy">
                        Shared with: {share.shared_with}
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

      {/* Preview Modal */}
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
              ) : previewData.type === 'text' ? (
                <pre className="whitespace-pre-wrap font-mono p-4 bg-gray-50 rounded">
                  {previewData.url}
                </pre>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Share Modal */}
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