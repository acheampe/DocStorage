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
  upload_date?: string;
  file_type: string;
  is_shared?: boolean;
  shared_by?: number;
  content?: string;
  share_id?: number;
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

// Add this function near the top of your component
const deduplicateSearchResults = (results: File[]) => {
  const seen = new Set<string>();
  return results.filter(file => {
    // Use original_filename as the unique key since that's what we're searching by
    const filename = file.original_filename?.toLowerCase();
    if (!filename || seen.has(filename)) return false;
    seen.add(filename);
    return true;
  });
};

// Normalize text by removing special characters and extra spaces
const normalizeText = (text: string): string => {
  return text
    .toLowerCase()
    .replace(/[_-]/g, ' ')    // Replace underscores and hyphens with spaces
    .replace(/\s+/g, ' ')     // Replace multiple spaces with single space
    .trim();                  // Remove leading/trailing spaces
};

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
  const [activeTab, setActiveTab] = useState<'recent' | 'shared-with-me' | 'shared-by-me'>('recent');

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

        // Fetch files shared with me
        const withMeResponse = await fetch('http://127.0.0.1:5000/share/shared-with-me', {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        });

        // Fetch files shared by me
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

        // Update state with the fetched data directly without verification
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

  const fetchThumbnail = async (docId: number, isShared: boolean = false, shareId?: number) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        isShared 
          ? `http://127.0.0.1:5000/share/preview/${shareId}/thumbnail`
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

  // Modify the search useEffect
  useEffect(() => {
    const searchDocuments = async () => {
      const currentQuery = searchQuery.trim().toLowerCase();
      
      try {
        if (!currentQuery) {
          setSearchResults([]);
          setIsSearching(false);
          return;
        }

        setIsSearching(true);
        setSearchError(null);

        const token = localStorage.getItem('token');
        if (!token) {
          console.error('No token found');
          setIsSearching(false);
          return;
        }

        console.log("\n=== Frontend Search Debug ===");
        console.log("Search query:", currentQuery);

        const response = await fetch(
          `http://127.0.0.1:5000/search?q=${encodeURIComponent(currentQuery)}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            },
            credentials: 'include'
          }
        );

        if (!response.ok) {
          throw new Error(`Search failed: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
          throw new Error(data.error);
        }

        console.log("Backend returned results:", data.results.length);
        console.log("Sample filenames:", data.results.slice(0, 3).map((f: File) => f.original_filename));

        // Split the search query into parts and normalize
        const queryParts = currentQuery
          .split(/[\s_]+/)
          .filter(part => part.length > 0);
        
        console.log("Query parts:", queryParts);

        // Filter results to match all parts of the query
        const filteredResults = data.results.filter((file: File) => {
          if (!file.original_filename) return false;
          
          const normalizedFilename = normalizeText(file.original_filename);
          const normalizedParts = queryParts.map(part => normalizeText(part));
          
          console.log("\nChecking file:", normalizedFilename);
          console.log("Using normalized parts:", normalizedParts);
          
          return normalizedParts.every(part => {
            const hasMatch = normalizedFilename.includes(part);
            console.log(`- Part "${part}": ${hasMatch ? '✓' : '✗'}`);
            return hasMatch;
          });
        });

        console.log("\nFiltered results:", filteredResults.length);
        console.log("Filtered filenames:", filteredResults.map(f => f.original_filename));

        if (searchQuery.trim() === currentQuery) {
          const uniqueResults = deduplicateSearchResults(filteredResults);
          console.log("Final unique results:", uniqueResults.length);
          setSearchResults(uniqueResults);
        }

      } catch (error) {
        console.error('Search error:', error);
        setSearchError(error instanceof Error ? error.message : 'Search failed');
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    };

    const timeoutId = setTimeout(searchDocuments, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handlePreview = async (docId: number, isSharedWithMe: boolean = false, filename: string, shareId?: number) => {
    try {
      console.log(`Previewing file: docId=${docId}, shareId=${shareId}, isSharedWithMe=${isSharedWithMe}`);
      
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('No token found');
        return;
      }

      // Use share endpoints for shared files
      const endpoint = isSharedWithMe && shareId
        ? `http://127.0.0.1:5000/share/content/${shareId}`  // New share service endpoint
        : `http://127.0.0.1:5000/docs/file/${docId}`;      // Existing doc service endpoint

      console.log(`Using endpoint: ${endpoint}`);
      
      // Get file extension
      const fileExt = filename.split('.').pop()?.toLowerCase();
      
      // Define previewable types
      const previewableTypes = {
        image: ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
        pdf: ['pdf'],
        text: ['txt', 'md', 'csv']
      };

      const isPreviewable = Object.values(previewableTypes)
        .flat()
        .includes(fileExt || '');

      // For non-previewable files, ask for download first
      if (!isPreviewable) {
        const userConfirmed = window.confirm(
          `"${filename}" cannot be previewed in the browser. Would you like to download it instead?`
        );
        
        if (!userConfirmed) return;

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

      // For previewable files
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

  const handleShareSuccess = () => {
    setSuccessMessage('Document shared successfully!');
    setTimeout(() => {
      setSuccessMessage(null);
    }, 3000);
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

      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg transition-all duration-500 ease-in-out z-50 flex items-center gap-2">
          <span className="material-symbols-rounded">check_circle</span>
          {successMessage}
        </div>
      )}

      {/* Main Content */}
      <main className="flex-grow container mx-auto p-8">
        {/* Welcome and Upload section */}
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

        {/* Tabs and View All Files button container */}
        {!searchQuery ? (
          <div className="flex justify-between items-center mb-6">
            <div className="flex gap-8">
              <button
                onClick={() => setActiveTab('recent')}
                className={`text-lg font-semibold ${
                  activeTab === 'recent' ? 'text-navy border-b-2 border-navy' : 'text-gray-500'
                }`}
              >
                Recent Files
              </button>
              <button
                onClick={() => setActiveTab('shared-with-me')}
                className={`text-lg font-semibold ${
                  activeTab === 'shared-with-me' ? 'text-navy border-b-2 border-navy' : 'text-gray-500'
                }`}
              >
                Shared with Me
              </button>
              <button
                onClick={() => setActiveTab('shared-by-me')}
                className={`text-lg font-semibold ${
                  activeTab === 'shared-by-me' ? 'text-navy border-b-2 border-navy' : 'text-gray-500'
                }`}
              >
                Shared by Me
              </button>
            </div>
            
            <Link
              href="/files"
              className="bg-[#002B5B] hover:bg-[#1B4B7D] text-white font-medium py-2 px-4 rounded transition-colors"
            >
              View All Files
            </Link>
          </div>
        ) : (
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-navy">
              {isSearching ? (
                <span className="flex items-center gap-2">
                  <span className="material-symbols-rounded animate-spin">hourglass_empty</span>
                  Searching...
                </span>
              ) : searchResults.length > 0 ? (
                `Search Results (${searchResults.length})`
              ) : (
                'Search Results'
              )}
            </h2>
          </div>
        )}

        {searchError && (
          <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg">
            {searchError}
          </div>
        )}

        {searchQuery && searchResults.length === 0 && !isSearching && !searchError ? (
          <div className="text-center mt-4 text-gray-600">
            No results found for "{searchQuery}"
          </div>
        ) : null}

        {/* Files Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {searchQuery ? 
            searchResults.map((file, index) => (
              <FileCard
                key={`search-${file.doc_id}-${file.share_id || 'private'}-${index}`}
                file={file}
                imageUrl={imageUrls[file.doc_id]}
                onPreview={() => handlePreview(file.doc_id, file.is_shared, file.original_filename, file.share_id)}
                onShare={!file.is_shared ? () => setShareModalOpen(file.doc_id) : undefined}
                isShared={file.is_shared}
              />
            ))
            : (
              <>
                {activeTab === 'recent' && recentFiles.map((file, index) => (
                  <FileCard
                    key={`recent-${file.doc_id}-${index}`}
                    file={file}
                    imageUrl={imageUrls[file.doc_id]}
                    onPreview={() => handlePreview(file.doc_id, file.is_shared, file.original_filename)}
                    onShare={() => setShareModalOpen(file.doc_id)}
                  />
                ))}

                {activeTab === 'shared-with-me' && sharedWithMeFiles.map((file, index) => (
                  <FileCard
                    key={`shared-with-${file.doc_id}-${file.share_id}-${index}`}
                    file={file}
                    imageUrl={imageUrls[file.doc_id]}
                    onPreview={() => handlePreview(file.doc_id, true, file.original_filename, file.share_id)}
                    isShared={true}
                  />
                ))}

                {activeTab === 'shared-by-me' && sharedByMeFiles.map((file, index) => (
                  <FileCard
                    key={`shared-by-${file.doc_id}-${file.share_id}-${index}`}
                    file={file}
                    imageUrl={imageUrls[file.doc_id]}
                    onPreview={() => handlePreview(file.doc_id, true, file.original_filename, file.share_id)}
                    isShared={true}
                  />
                ))}
              </>
            )}
        </div>

        {/* Preview Modal */}
        {previewData && (
          <PreviewModal
            previewData={previewData}
            onClose={() => setPreviewData(null)}
            onShare={() => setShareModalOpen(previewData.docId)}
          />
        )}

        {/* Share Modal */}
        {shareModalOpen !== -1 && (
          <ShareModal
            onClose={() => setShareModalOpen(-1)}
            selectedFiles={[shareModalOpen]}
            onSuccess={handleShareSuccess}
          />
        )}

        {isSearching && <div>Searching...</div>}
      </main>
    </div>
  );
}

// FileCard component with restored styling
interface FileCardProps {
  file: any;
  imageUrl?: string;
  onPreview: () => void;
  onShare?: () => void;
  isShared?: boolean;
  isOwner?: boolean;
}

function FileCard({ file, imageUrl, onPreview, onShare, isShared }: FileCardProps) {
  // Helper function to format date
  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'No date';
    
    // Try parsing the date string
    const date = new Date(dateString);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.warn('Invalid date:', dateString);
      return 'No date';
    }
    
    return date.toLocaleDateString();
  };

  // Get the appropriate date field based on the file type
  const displayDate = file.shared_date || file.upload_date;

  return (
    <div 
      className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer relative"
      onClick={onPreview}
    >
      <div className="mb-2">
        {file.file_type?.startsWith('image/') ? (
          <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50 relative">
            {imageUrl ? (
              <img 
                src={imageUrl}
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
          {formatDate(displayDate)}
        </p>
        {!isShared && onShare && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onShare();
            }}
            className="text-navy hover:text-gold transition-colors"
            title="Share this document"
          >
            <span className="material-symbols-rounded">share</span>
          </button>
        )}
      </div>
    </div>
  );
}

// Optional: Separate PreviewModal component
interface PreviewModalProps {
  previewData: PreviewData;
  onClose: () => void;
  onShare?: () => void;
}

function PreviewModal({ previewData, onClose, onShare }: PreviewModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-navy">{previewData.filename}</h3>
          <div className="flex items-center gap-4">
            {onShare && (
              <button 
                onClick={onShare}
                className="text-navy hover:text-gold transition-colors"
                title="Share this document"
              >
                <span className="material-symbols-rounded">share</span>
              </button>
            )}
            <button 
              onClick={() => {
                const a = document.createElement('a');
                a.href = previewData.url;
                a.download = previewData.filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              }}
              className="text-navy hover:text-gold transition-colors"
              title="Download this document"
            >
              <span className="material-symbols-rounded">download</span>
            </button>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              <span className="material-symbols-rounded">close</span>
            </button>
          </div>
        </div>
        <div className="overflow-auto flex-grow">
          {previewData.type === 'image' ? (
            <img src={previewData.url} alt={previewData.filename} className="max-w-full h-auto" />
          ) : previewData.type === 'pdf' ? (
            <iframe src={previewData.url} className="w-full h-full min-h-[600px]" title={previewData.filename} />
          ) : (
            <pre className="whitespace-pre-wrap font-mono p-4 bg-gray-50 rounded">
              {previewData.url}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}