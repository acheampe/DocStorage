'use client'
import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Footer from '@/components/Footer'

interface FileWithPreview extends File {
  preview?: string;
}

export default function UploadFiles() {
  const router = useRouter();
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);

  // Auth protection pattern from dashboard
  useEffect(() => {
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
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    router.push('/');
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).map(file => {
        if (file.type.startsWith('image/')) {
          const token = localStorage.getItem('token');
          const preview = file.type.startsWith('image/') 
            ? URL.createObjectURL(file)  // Use blob URL for local preview before upload
            : null;
          return Object.assign(file, { preview });
        }
        return file;
      });
      setFiles(prev => [...prev, ...newFiles]);
      setError('');
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => {
      const newFiles = [...prev];
      if (newFiles[index].preview) {
        URL.revokeObjectURL(newFiles[index].preview!);
      }
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      console.log('Files to upload:', files.length);
      
      files.forEach((file, index) => {
        console.log(`Appending file ${index + 1}:`, file.name);
        formData.append('files[]', file);
      });

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch('http://127.0.0.1:5000/docs/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Upload failed');
      }

      const result = await response.json();
      console.log('Upload response:', result);

      await new Promise(resolve => setTimeout(resolve, 1000));
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Cleanup previews on unmount
  useEffect(() => {
    return () => {
      files.forEach(file => {
        if (file.preview) {
          URL.revokeObjectURL(file.preview);
        }
      });
    };
  }, [files]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const dropZone = e.currentTarget as HTMLElement;
    dropZone.classList.add('border-navy');
    dropZone.classList.remove('border-gold', 'border-opacity-45');
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const dropZone = e.currentTarget as HTMLElement;
    dropZone.classList.remove('border-navy');
    dropZone.classList.add('border-gold', 'border-opacity-45');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const dropZone = e.currentTarget as HTMLElement;
    dropZone.classList.remove('border-navy');
    dropZone.classList.add('border-gold', 'border-opacity-45');

    if (e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files).map(file => {
        if (file.type.startsWith('image/')) {
          const preview = URL.createObjectURL(file);
          return Object.assign(file, { preview });
        }
        return file;
      });
      setFiles(droppedFiles);
      setError('');
    }
  };

  // Add this function to get authenticated file URL
  const getFileUrl = (fileId: number) => {
    const token = localStorage.getItem('token');
    return `http://127.0.0.1:5000/docs/file/${fileId}`;
  };

  // Add this function to create headers for file requests
  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Authorization': `Bearer ${token}`
    };
  };

  // Add this function to handle file previews
  const getFilePreviewUrl = (fileId: number) => {
    const token = localStorage.getItem('token');
    return `http://127.0.0.1:5000/docs/file/${fileId}?token=${token}`;
  };

  // Modify the file preview component to use authenticated requests
  const FilePreview = ({ file, index }: { file: FileWithPreview; index: number }) => {
    const [previewError, setPreviewError] = useState(false);

    return (
      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center space-x-3">
          <span className="material-symbols-rounded text-navy">
            {file.type.startsWith('image/') ? 'image' : 'description'}
          </span>
          <span className="text-navy truncate max-w-xs">
            {file.name}
          </span>
        </div>
        <button
          type="button"
          onClick={() => removeFile(index)}
          className="text-red-500 hover:text-red-700"
          title="Remove file"
        >
          <span className="material-symbols-rounded">close</span>
        </button>
      </div>
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-white">
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

      <main className="flex-grow container mx-auto p-8">
        <h1 className="text-6xl font-black text-navy text-center mb-12">Upload Files</h1>
        
        <div className="max-w-3xl mx-auto">
          {error && (
            <p className="text-red-500 text-center mb-4 p-3 bg-red-50 rounded-lg">
              {error}
            </p>
          )}
          
          <form onSubmit={handleFileUpload} className="space-y-6">
            <div className="relative">
              <label 
                className="block w-full p-8 border-4 border-dashed border-gold border-opacity-45 rounded-2xl text-center cursor-pointer hover:border-opacity-70 transition-all"
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
                  title="Select the file(s) you want to upload"
                />
                <div className="space-y-2">
                  <span className="material-symbols-rounded text-navy text-4xl">
                    upload_file
                  </span>
                  <p className="text-navy font-medium">
                    Drop files here or click to select
                  </p>
                  <p className="text-sm text-gray-500">
                    Supported files: PDF, DOC, DOCX, TXT, JPG, PNG
                  </p>
                </div>
              </label>
            </div>

            {/* Selected Files Preview */}
            {files.length > 0 && (
              <div className="space-y-4 mt-4">
                <h3 className="font-medium text-navy">Selected Files:</h3>
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <FilePreview key={index} file={file} index={index} />
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-center gap-4">
              <button
                type="submit"
                disabled={uploading || files.length === 0}
                className={`bg-navy text-white font-black text-xl py-2 px-8 rounded-2xl transition-all
                  ${uploading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-opacity-90'}`}
                title="Upload the selected files"
              >
                {uploading ? 'Uploading...' : 'Upload'}
              </button>
              <Link
                href="/dashboard"
                className="bg-navy text-white font-black text-xl py-2 px-8 rounded-2xl hover:bg-opacity-90 transition-all"
                title="Cancel the upload and return to the dashboard"
              >
                Cancel
              </Link>
            </div>
          </form>
        </div>
      </main>
      <Footer />
    </div>
  );
}