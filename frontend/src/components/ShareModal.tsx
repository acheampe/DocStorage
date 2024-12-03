import React, { useState } from 'react';

interface ShareModalProps {
  onClose: () => void;
  isBulkShare?: boolean;
  selectedFiles?: number[];
  selectedCount?: number;
  infoMessage?: React.ReactNode;
}

export default function ShareModal({ onClose, isBulkShare, selectedFiles, selectedCount, infoMessage }: ShareModalProps) {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      if (!selectedFiles?.length) {
        throw new Error('No file selected');
      }

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch('http://127.0.0.1:5000/share', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify({
          doc_id: selectedFiles[0],
          recipient_email: email,
        })
      });

      if (!response.ok) {
        let errorMessage = 'Failed to share file';
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorMessage;
        } catch (e) {
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setSuccessMessage('File shared successfully!');
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (error) {
      console.error('Share error:', error);
      setError(error instanceof Error ? error.message : 'Failed to share file');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      <div className="absolute inset-0 bg-black bg-opacity-25"></div>
      
      <div 
        className="relative bg-white rounded-lg p-6 w-full max-w-md mx-4 shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-2xl font-bold text-navy mb-4">
          {isBulkShare 
            ? `Share ${selectedCount} Files`
            : 'Share File'}
        </h2>

        {infoMessage}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-navy font-medium mb-2">
              Recipient Email
              <span className="text-sm font-normal text-gray-600 ml-2">
                (must be a DocStorage user)
              </span>
            </label>
            <div className="relative">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border-2 border-navy rounded-lg focus:outline-none focus:border-gold"
                placeholder="Enter recipient's email"
                required
              />
              <span className="material-symbols-rounded absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                mail
              </span>
            </div>
            <p className="mt-2 text-sm text-gray-600">
              <strong>Note:</strong> The recipient must have a DocStorage account to access shared files.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}

          {successMessage && (
            <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
              {successMessage}
            </div>
          )}

          <div className="flex justify-end gap-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-navy text-white rounded hover:bg-opacity-90 disabled:opacity-50"
            >
              {isLoading ? 'Sharing...' : 'Share'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
} 