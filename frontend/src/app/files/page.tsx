'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '@/components/Navigation';

interface File {
  doc_id: number;
  original_filename: string;
  upload_date: string;
  file_type: string;
}

export default function Files() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingFile, setEditingFile] = useState<{ id: number; name: string } | null>(null);
  const [previewData, setPreviewData] = useState<{
    type: string;
    url: string;
    filename: string;
  } | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<File[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchAllFiles();
  }, [router]);

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
        setSearchResults(data.results.map((result: any) => ({
          doc_id: result.doc_id,
          original_filename: result.metadata.filename,
          upload_date: result.metadata.upload_date,
          file_type: result.metadata.file_type
        })));
      } catch (error) {
        console.error('Error searching documents:', error);
        setSearchError('Failed to search documents');
      } finally {
        setIsSearching(false);
      }
    };

    // Debounce the search to avoid too many requests
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
      console.log('Attempting to rename file:', editingFile);

      const response = await fetch(`http://127.0.0.1:5000/docs/documents/${editingFile.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename: editingFile.name })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Server error:', errorData);
        throw new Error('Failed to rename file');
      }
      
      const data = await response.json();
      console.log('Success response:', data);
      
      // Refresh the file list after successful rename
      await fetchAllFiles();
      
      setEditingFile(null);
      setSuccessMessage('File renamed successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      console.error('Error renaming file:', error);
      setSuccessMessage('Failed to rename file. Please try again.');
      setTimeout(() => setSuccessMessage(null), 3000);
    }
  };

  const handlePreview = async (file: File) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://127.0.0.1:5000/docs/file/${file.doc_id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to fetch file');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      // Set preview data based on file type
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
      } else {
        // For other file types, trigger download instead
        const a = document.createElement('a');
        a.href = url;
        a.download = file.original_filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Error previewing file:', error);
    }
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
                  onClick={() => {/* Share functionality to be implemented */}}
                  className="px-6 py-2 bg-gold text-white rounded-lg hover:bg-opacity-90 transition-all"
                  title="Share selected files"
                >
                  Share Selected
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <span className="material-symbols-rounded text-4xl animate-spin">hourglass_empty</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {(searchQuery ? searchResults : files).map((file) => (
              <div
                key={file.doc_id}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-colors relative ${
                  selectedFiles.includes(file.doc_id)
                    ? 'border-gold bg-yellow-50'
                    : 'border-navy hover:border-gold'
                }`}
                onClick={() => handlePreview(file)}
              >
                <div className="flex items-center justify-between mb-2" onClick={e => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedFiles.includes(file.doc_id)}
                    onChange={() => handleFileSelect(file.doc_id)}
                    className="h-5 w-5"
                  />
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
                <p className="font-medium text-navy truncate">{file.original_filename}</p>
                <p className="text-sm text-gray-500">
                  {new Date(file.upload_date).toLocaleDateString()}
                </p>
                <span className="material-symbols-rounded absolute right-2 bottom-2 text-gray-400">
                  {file.file_type.startsWith('image/') ? 'image' :
                   file.file_type === 'application/pdf' ? 'picture_as_pdf' :
                   'description'}
                </span>
              </div>
            ))}
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
                <button
                  onClick={() => {
                    const file = files.find(f => f.original_filename === previewData.filename);
                    if (file) {
                      setEditingFile({
                        id: file.doc_id,
                        name: file.original_filename
                      });
                    }
                  }}
                  className="text-navy hover:text-gold"
                  title="Rename file"
                >
                  <span className="material-symbols-rounded">edit</span>
                </button>
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
    </div>
  );
}
