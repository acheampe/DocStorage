'use client'
import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Footer from '@/components/Footer'

export default function UploadFiles() {
  const router = useRouter();
  const [files, setFiles] = useState<FileList | null>(null);
  const [error, setError] = useState('');

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

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files || files.length === 0) return;

    try {
        const token = localStorage.getItem('token');
        const formData = new FormData();
        
        Array.from(files).forEach(file => {
            formData.append('files[]', file);
            console.log('Appending file:', file.name);
        });

        console.log('Sending request to:', 'http://127.0.0.1:5000/docs/upload');
        
        const response = await fetch('http://127.0.0.1:5000/docs/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        console.log('Response status:', response.status);
        const data = await response.json();
        
        if (response.status === 201) {
            if (data.errors) {
                // Some files failed but at least one succeeded
                setError(`Some files failed to upload: ${data.errors.join(', ')}`);
                // Wait 2 seconds before redirecting
                setTimeout(() => {
                    router.push('/dashboard?upload=partial');
                }, 2000);
            } else {
                router.push('/dashboard?upload=success');
            }
            return;
        }

        throw new Error(data.error || 'Upload failed');
    } catch (err) {
        console.error('Upload error:', err);
        setError(err instanceof Error ? err.message : 'Upload failed');
    }
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
        <h1 className="text-6xl font-black text-navy text-center mb-12">Upload File</h1>
        
        <div className="max-w-3xl mx-auto">
          {error && <p className="text-red-500 text-center mb-4">{error}</p>}
          
          <form onSubmit={handleFileUpload} className="space-y-6">
            <div className="relative">
              <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">Select File</label>
              <input
                type="file"
                multiple
                onChange={(e) => setFiles(e.target.files)}
                className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
                required
                title="Select the file(s) you want to upload"
              />
            </div>

            <div className="flex justify-center gap-4">
              <button
                type="submit"
                className="bg-navy text-white font-black text-xl py-2 px-8 rounded-2xl hover:bg-opacity-90 transition-all"
                title="Upload the selected files"
              >
                Upload
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