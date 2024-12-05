import React, { useState } from 'react';

interface ShareModalProps {
  onClose: () => void;
  isBulkShare?: boolean;
  selectedFiles?: number[];
  selectedCount?: number;
  infoMessage?: React.ReactNode;
}

interface UserLookupResponse {
  user_id: number;
  email: string;
}

export default function ShareModal({ onClose, isBulkShare, selectedFiles, selectedCount, infoMessage }: ShareModalProps) {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isValidatingEmail, setIsValidatingEmail] = useState(false);

  const lookupUserByEmail = async (email: string): Promise<number> => {
    try {
      const token = localStorage.getItem('token');
      console.log('Debug - Token:', token ? token.substring(0, 20) + '...' : 'Missing');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch(
        `http://127.0.0.1:5000/auth/users/lookup?email=${encodeURIComponent(email)}`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        }
      );

      console.log('Debug - Response status:', response.status);
      const responseText = await response.text();
      console.log('Debug - Response body:', responseText);

      if (!response.ok) {
        throw new Error(`Failed to validate recipient: ${response.status} ${response.statusText}`);
      }

      const data = JSON.parse(responseText);
      if (!data.user_id) {
        throw new Error('User not found');
      }

      return data.user_id;
    } catch (error) {
      console.error('Lookup error:', error);
      throw error;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    setIsValidatingEmail(true);

    try {
      if (!selectedFiles?.length) {
        throw new Error('No file selected');
      }

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      const recipientId = await lookupUserByEmail(email);

      const sharePromises = selectedFiles.map(docId => {
        const payload = {
          doc_id: docId,
          recipient_id: recipientId
        };
        console.log('Share Request Payload:', payload);

        return fetch('http://127.0.0.1:5000/share', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include',
          body: JSON.stringify(payload)
        });
      });

      const responses = await Promise.all(sharePromises);
      
      const failedResponses = responses.filter(response => !response.ok);
      if (failedResponses.length > 0) {
        throw new Error(`Failed to share ${failedResponses.length} files`);
      }

      setSuccessMessage(`${selectedFiles.length} ${selectedFiles.length === 1 ? 'file' : 'files'} shared successfully!`);
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (error) {
      console.error('Share error:', error);
      setError(error instanceof Error ? error.message : 'Failed to share files');
    } finally {
      setIsLoading(false);
      setIsValidatingEmail(false);
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

          {isValidatingEmail && (
            <div className="mb-4 p-3 bg-blue-50 text-blue-700 rounded-lg text-sm">
              Validating recipient email...
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
              disabled={isLoading || isValidatingEmail}
              className="px-4 py-2 bg-navy text-white rounded hover:bg-opacity-90 disabled:opacity-50"
            >
              {isLoading ? 'Sharing...' : 
               isValidatingEmail ? 'Validating...' : 
               'Share'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
} 