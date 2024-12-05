'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '@/components/Navigation';
import ShareModal from '@/components/ShareModal';
import { getFileIcon } from '@/utils/fileIcons';

interface File {
  doc_id: number;
  original_filename: string;
  upload_date: string;
  file_type: string;
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

interface PreviewData {
  type: 'image' | 'pdf' | 'text';
  url: string;
  filename: string;
  docId: number;
  isSharedWithMe: boolean;
}

export default function Files() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingFile, setEditingFile] = useState<{ id: number; name: string } | null>(null);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<File[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [shareModalOpen, setShareModalOpen] = useState<number>(-1);
  const [imageUrls, setImageUrls] = useState<{ [key: number]: string }>({});
  const [sharedWithMeFiles, setSharedWithMeFiles] = useState<SharedFile[]>([]);
  const [activeTab, setActiveTab] = useState<'my-files' | 'shared'>('my-files');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchAllFiles();
    fetchSharedFiles();
  }, [router]);

  useEffect(() => {
    const searchDocuments = async () => {
      if (!searchQuery.trim()) {
        setSearchResults([]);
        setIsSearching(false);
        setSearchError(null);
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
        
        // Verify each file exists before adding to UI
        const verifiedFiles = [];
        for (const file of data.results) {
          const verifyResponse = await fetch(`http://127.0.0.1:5000/docs/file/${file.doc_id}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            },
            credentials: 'include'
          });
          if (verifyResponse.ok) {
            verifiedFiles.push({
              doc_id: file.doc_id,
              original_filename: file.metadata.filename,
              upload_date: file.metadata.upload_date,
              file_type: file.metadata.file_type
            });
          }
        }
        setSearchResults(verifiedFiles);
      } catch (error) {
        console.error('Error searching documents:', error);
        setSearchError('Failed to search documents');
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    };

    const timeoutId = setTimeout(searchDocuments, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const fetchAllFiles = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://127.0.0.1:5000/docs/documents', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to fetch files');
      
      const data = await response.json();
      const sortedFiles = data.sort((a: File, b: File) => 
        new Date(b.upload_date).getTime() - new Date(a.upload_date).getTime()
      );
      setFiles(sortedFiles);
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching files:', error);
      setIsLoading(false);
    }
  };

  const fetchSharedFiles = async () => {
    try {
      const token = localStorage.getItem('token');
      const userData = localStorage.getItem('user');
      if (!token || !userData) {
        console.error('No token or user data found');
        return;
      }

      const user = JSON.parse(userData);

      // Fetch files shared with me
      const withMeResponse = await fetch(`http://127.0.0.1:5000/share/shared-with-me?recipient_id=${user.user_id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include'
      });

      if (!withMeResponse.ok) {
        throw new Error('Failed to fetch shared files');
      }

      const withMeData = await withMeResponse.json();
      console.log('Shared with me:', withMeData);
      setSharedWithMeFiles(withMeData.shares || []);

    } catch (error) {
      console.error('Error fetching shared files:', error);
    }
  };

  const handleFileSelect = (docId: number) => {
    setSelectedFiles(prev => 
      prev.includes(docId) 
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const handleSelectAll = () => {
    if (selectedFiles.length === files.length) {
      setSelectedFiles([]);
    } else {
      setSelectedFiles(files.map(file => file.doc_id));
    }
  };

  const handleDelete = async () => {
    if (!selectedFiles.length) return;
    
    const confirmed = window.confirm('Are you sure you want to delete the selected files?');
    if (!confirmed) return;

    try {
      const token = localStorage.getItem('token');
      
      await Promise.all(selectedFiles.map(docId =>
        fetch(`http://127.0.0.1:5000/docs/documents/${docId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      ));

      setSuccessMessage(`${selectedFiles.length} ${selectedFiles.length === 1 ? 'file' : 'files'} deleted successfully`);
      setTimeout(() => setSuccessMessage(null), 3000);

      fetchAllFiles(); // Refresh the file list
      setSelectedFiles([]); // Clear selection
    } catch (error) {
      console.error('Error deleting files:', error);
      setSuccessMessage('Failed to delete files. Please try again.');
      setTimeout(() => setSuccessMessage(null), 3000);
    }
  };

  const handleDownload = async () => {
    if (!selectedFiles.length) return;

    try {
        const token = localStorage.getItem('token');
        let successCount = 0;
        
        for (const docId of selectedFiles) {
            try {
                const response = await fetch(`http://127.0.0.1:5000/docs/documents/${docId}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (!response.ok) throw new Error('Download failed');
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = files.find(f => f.doc_id === docId)?.original_filename || 'download';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                successCount++;
            } catch (error) {
                console.error(`Error downloading file ${docId}:`, error);
            }
        }

        // Show success message based on how many files were downloaded
        if (successCount === selectedFiles.length) {
            setSuccessMessage(`${successCount} ${successCount === 1 ? 'file' : 'files'} downloaded successfully`);
        } else if (successCount > 0) {
            setSuccessMessage(`${successCount} out of ${selectedFiles.length} files downloaded successfully`);
        } else {
            setSuccessMessage('Failed to download files. Please try again.');
        }
        
        // Clear the message after 3 seconds
        setTimeout(() => setSuccessMessage(null), 3000);
        
        // Clear selection after download
        setSelectedFiles([]);
        
    } catch (error) {
        console.error('Error downloading files:', error);
        setSuccessMessage('Failed to download files. Please try again.');
        setTimeout(() => setSuccessMessage(null), 3000);
    }
  };

  const handleRename = async () => {
    if (!editingFile) return;

    try {
      const token = localStorage.getItem('token');
      const newFilename = editingFile.name;
      
      // Get the timestamp and user directory from the existing file path
      const timestamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0].replace('T', '_');
      const userDir = `${localStorage.getItem('userId')}/`;
      
      // Construct the new filename with timestamp
      const newTimestampedFilename = `${timestamp}_${newFilename}`;
      // Construct the new file path
      const newFilePath = `${userDir}${newTimestampedFilename}`;

      const response = await fetch(`http://127.0.0.1:5000/docs/file/${editingFile.id}/rename`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          new_filename: newFilename,
          new_timestamped_filename: newTimestampedFilename,
          new_file_path: newFilePath
        })
      });

      if (!response.ok) {
        throw new Error('Failed to rename file');
      }

      // Update local state
      setFiles(prevFiles => 
        prevFiles.map(file => 
          file.doc_id === editingFile.id 
            ? { 
                ...file, 
                original_filename: newFilename,
                filename: newTimestampedFilename,
                file_path: newFilePath 
              } 
            : file
        )
      );

      setEditingFile(null);
      setSuccessMessage('File renamed successfully');
    } catch (error) {
      console.error('Error renaming file:', error);
      setError('Failed to rename file');
    }
  };

  const handlePreview = async (docId: number, isSharedWithMe: boolean, filename: string, shareId?: number) => {
    try {
      console.log(`Previewing file: docId=${docId}, shareId=${shareId}, isSharedWithMe=${isSharedWithMe}`);
      
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('No token found');
        return;
      }

      // Use share endpoints for shared files
      const endpoint = isSharedWithMe
        ? `http://127.0.0.1:5000/share/preview/${shareId}/content`
        : `http://127.0.0.1:5000/docs/file/${docId}`;

      console.log(`Using endpoint: ${endpoint}`);
      
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

      // For non-previewable files, ask for download first
      if (!isPreviewable) {
        const userConfirmed = window.confirm(
          `"${filename}" cannot be previewed in the browser. Would you like to download it instead?`
        );
        
        if (!userConfirmed) return;

        const downloadEndpoint = isSharedWithMe
          ? `http://127.0.0.1:5000/share/preview/${shareId}/content`
          : `http://127.0.0.1:5000/docs/file/${docId}`;

        const downloadResponse = await fetch(downloadEndpoint, {
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
          docId: docId,
          isSharedWithMe: isSharedWithMe
        });
      } else if (contentType === 'application/pdf') {
        setPreviewData({
          type: 'pdf',
          url: URL.createObjectURL(data),
          filename: filename,
          docId: docId,
          isSharedWithMe: isSharedWithMe
        });
      } else if (contentType.startsWith('text/')) {
        const text = await data.text();
        setPreviewData({
          type: 'text',
          url: text,
          filename: filename,
          docId: docId,
          isSharedWithMe: isSharedWithMe
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
      return '/placeholder-image.png';
    }
  };

  useEffect(() => {
    const loadImages = async () => {
      const newImageUrls: { [key: number]: string } = {};
      
      for (const file of files) {
        if (file.file_type.startsWith('image/')) {
          try {
            const thumbnailUrl = await fetchThumbnail(file.doc_id);
            if (thumbnailUrl) {
              newImageUrls[file.doc_id] = thumbnailUrl;
            }
          } catch (error) {
            console.error(`Error loading thumbnail for file ${file.doc_id}:`, error);
          }
        }
      }
      
      setImageUrls(newImageUrls);
    };

    if (files.length > 0) {
      loadImages();
    }

    return () => {
      // Cleanup URLs on unmount
      Object.values(imageUrls).forEach(url => URL.revokeObjectURL(url));
    };
  }, [files]);

  const handleShareSuccess = () => {
    setSuccessMessage('Document shared successfully!');
    setTimeout(() => {
      setSuccessMessage(null);
    }, 3000);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navigation />
      
      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg transition-all duration-500 ease-in-out z-50 flex items-center gap-2">
          <span className="material-symbols-rounded">check_circle</span>
          {successMessage}
        </div>
      )}
      
      <div className="sticky top-0 bg-white shadow-md z-10 py-4 px-4 border-b">
        <div className="container mx-auto">
          <div className="flex items-center mb-4">
            <h1 className="text-2xl font-bold text-navy whitespace-nowrap w-[150px]">All Files</h1>
            <div className="flex-1 flex justify-center max-w-3xl">
              <div className="relative w-full">
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-4 py-2 border-2 border-navy rounded-lg focus:outline-none focus:border-gold"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 material-symbols-rounded text-navy">
                  {isSearching ? 'hourglass_empty' : 'search'}
                </span>
              </div>
            </div>
            <div className="w-[150px] flex justify-end">
              <button
                onClick={() => router.push('/uploadFiles')}
                className="px-4 py-2 bg-gold text-white rounded-lg hover:bg-opacity-90 transition-all flex items-center gap-2"
                title="Upload new file"
              >
                <span className="material-symbols-rounded">upload_file</span>
                Upload File
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-4">
            <button
              onClick={handleSelectAll}
              className="px-6 py-2 bg-navy text-white rounded-lg hover:bg-opacity-90 transition-all"
            >
              {selectedFiles.length === files.length ? 'Deselect All' : 'Select All'}
            </button>
            {selectedFiles.length > 0 && (
              <>
                <button
                  onClick={handleDelete}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-opacity-90 transition-all"
                  title="Delete selected files"
                >
                  Delete Selected
                </button>
                <button
                  onClick={handleDownload}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-opacity-90 transition-all"
                  title="Download selected files"
                >
                  Download Selected
                </button>
                <button
                  onClick={() => {
                    if (selectedFiles.length > 0) {
                      setShareModalOpen(-2); // Special value for bulk share
                    }
                  }}
                  disabled={selectedFiles.length === 0}
                  className="px-4 py-2 bg-gold text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Share Selected
                </button>
              </>
            )}
          </div>

          <div className="flex gap-4 mt-4">
            <button
              onClick={() => setActiveTab('my-files')}
              className={`px-4 py-2 rounded-lg ${
                activeTab === 'my-files' 
                  ? 'bg-navy text-white' 
                  : 'text-navy hover:bg-gray-100'
              }`}
            >
              My Files
            </button>
            <button
              onClick={() => setActiveTab('shared')}
              className={`px-4 py-2 rounded-lg ${
                activeTab === 'shared' 
                  ? 'bg-navy text-white' 
                  : 'text-navy hover:bg-gray-100'
              }`}
            >
              Shared with Me
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-navy"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {activeTab === 'my-files' ? (
              // My Files content
              (searchQuery ? searchResults : files).map((file) => (
                <div
                  key={file.doc_id}
                  className={`p-4 border-2 rounded-lg cursor-pointer transition-colors relative ${
                    selectedFiles.includes(file.doc_id)
                      ? 'border-gold bg-yellow-50'
                      : 'border-navy hover:border-gold'
                  }`}
                  onClick={() => handlePreview(file.doc_id, false, file.original_filename)}
                >
                  <div className="flex items-center justify-between mb-2" onClick={e => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedFiles.includes(file.doc_id)}
                      onChange={() => handleFileSelect(file.doc_id)}
                      className="h-5 w-5"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShareModalOpen(file.doc_id);
                        }}
                        className="text-navy hover:text-gold"
                        title="Share file"
                      >
                        <span className="material-symbols-rounded">share</span>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingFile({ 
                            id: file.doc_id, 
                            name: file.original_filename 
                          });
                        }}
                        className="text-navy hover:text-gold"
                        title="Rename file"
                      >
                        <span className="material-symbols-rounded">edit</span>
                      </button>
                    </div>
                  </div>

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

                  <p className="font-medium text-navy truncate">{file.original_filename}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(file.upload_date).toLocaleDateString()}
                  </p>
                </div>
              ))
            ) : (
              // Shared with Me content
              Array.isArray(sharedWithMeFiles) ? sharedWithMeFiles.map((share) => (
                <div
                  key={share.share_id}
                  className="p-4 border-2 border-navy rounded-lg hover:border-gold transition-colors cursor-pointer relative"
                  onClick={() => handlePreview(
                    share.doc_id,
                    true,  // isSharedWithMe = true
                    share.original_filename || share.display_name || share.filename || 'Unknown Filename',
                    share.share_id  // Pass the share_id
                  )}
                >
                  <div className="mb-2">
                    {share.file_type?.startsWith('image/') ? (
                      <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50 relative">
                        {imageUrls[share.doc_id] ? (
                          <img 
                            src={imageUrls[share.doc_id]}
                            alt={share.original_filename}
                            className="w-full h-40 object-cover rounded"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                              const parent = target.parentElement;
                              if (parent) {
                                const icon = document.createElement('span');
                                icon.className = 'material-symbols-rounded text-navy text-4xl';
                                icon.textContent = getFileIcon(share.original_filename);
                                parent.appendChild(icon);
                              }
                            }}
                          />
                        ) : (
                          <span className="material-symbols-rounded text-navy text-4xl">
                            {getFileIcon(share.original_filename)}
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="w-full h-40 mb-2 flex items-center justify-center bg-gray-50">
                        <span className="material-symbols-rounded text-navy text-4xl">
                          {getFileIcon(share.original_filename)}
                        </span>
                      </div>
                    )}
                  </div>
                  <h4 className="font-bold text-navy truncate">
                    {share.original_filename}
                  </h4>
                  <div className="flex justify-between items-center mt-2">
                    <p className="text-sm text-gray-600">
                      {new Date(share.shared_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              )) : (
                <div className="col-span-full text-center text-gray-500 py-8">
                  No shared files found
                </div>
              )
            )}
          </div>
        )}
      </div>

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
                <div className="flex gap-2">
                  {!previewData.isSharedWithMe && (
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingFile({ id: previewData.docId, name: previewData.filename });
                      }}
                      className="text-gray-500 hover:text-navy transition-colors"
                      title="Rename this document"
                    >
                      <span className="material-symbols-rounded">edit</span>
                    </button>
                  )}
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
                </div>
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

      {editingFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96" onClick={e => e.stopPropagation()}>
            <h3 className="text-xl font-bold mb-4">Rename File</h3>
            <input
              type="text"
              value={editingFile.name}
              onChange={e => setEditingFile({ ...editingFile, name: e.target.value })}
              className="w-full px-3 py-2 border-2 border-navy rounded-lg mb-4 focus:outline-none focus:border-gold"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditingFile(null)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleRename}
                className="px-4 py-2 bg-gold text-white rounded-lg hover:bg-opacity-90"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {searchError && (
        <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg">
          {searchError}
        </div>
      )}

      {shareModalOpen !== -1 && (
        <ShareModal
          onClose={() => {
            setShareModalOpen(-1);
            setSelectedFiles([]); // Clear selections after sharing
          }}
          selectedFiles={shareModalOpen === -2 ? selectedFiles : [shareModalOpen]}
          onSuccess={handleShareSuccess}
        />
      )}
    </div>
  );
}
