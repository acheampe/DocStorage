'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ImagePreview from '@/components/ImagePreview';
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
  const [previewImage, setPreviewImage] = useState<{ id: number; filename: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingFile, setEditingFile] = useState<{ id: number; name: string } | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchAllFiles();
  }, [router]);

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

      fetchAllFiles(); // Refresh the file list
      setSelectedFiles([]); // Clear selection
    } catch (error) {
      console.error('Error deleting files:', error);
    }
  };

  const handleDownload = async () => {
    if (!selectedFiles.length) return;

    try {
      const token = localStorage.getItem('token');
      
      selectedFiles.forEach(async (docId) => {
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
      });
    } catch (error) {
      console.error('Error downloading files:', error);
    }
  };

  const handleRename = async () => {
    if (!editingFile) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://127.0.0.1:5000/docs/documents/${editingFile.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename: editingFile.name })
      });

      if (!response.ok) throw new Error('Failed to rename file');
      
      // Update local state
      setFiles(files.map(file => 
        file.doc_id === editingFile.id 
          ? { ...file, original_filename: editingFile.name }
          : file
      ));
      setEditingFile(null);
    } catch (error) {
      console.error('Error renaming file:', error);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navigation />
      
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
                  search
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {files.map((file) => (
            <div
              key={file.doc_id}
              className={`p-4 border-2 rounded-lg cursor-pointer transition-colors relative ${
                selectedFiles.includes(file.doc_id)
                  ? 'border-gold bg-yellow-50'
                  : 'border-navy hover:border-gold'
              }`}
              onClick={() => handleFileSelect(file.doc_id)}
            >
              <div className="flex items-center justify-between mb-2">
                <input
                  type="checkbox"
                  checked={selectedFiles.includes(file.doc_id)}
                  onChange={() => handleFileSelect(file.doc_id)}
                  onClick={(e) => e.stopPropagation()}
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
            </div>
          ))}
        </div>
      </div>

      {previewImage && (
        <ImagePreview
          src={`http://127.0.0.1:5000/docs/file/${previewImage.id}`}
          alt={previewImage.filename}
          onClose={() => setPreviewImage(null)}
        />
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
    </div>
  );
}
