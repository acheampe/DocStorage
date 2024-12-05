import React, { useState } from 'react';

interface User {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
}

interface ShareModalProps {
  onClose: () => void;
  selectedFiles: number[];
  onSuccess?: () => void;
}

interface UserLookupResponse {
  user_id: number;
  email: string;
}

export default function ShareModal({ onClose, selectedFiles, onSuccess }: ShareModalProps) {
  const [selectedUser, setSelectedUser] = useState<number | null>(null);
  const [email, setEmail] = useState<string>('');
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isValidatingEmail, setIsValidatingEmail] = useState(false);

  const lookupUserByEmail = async (email: string): Promise<number> => {
    setIsValidatingEmail(true);
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

      setSelectedUser(data.user_id);
      return data.user_id;
    } catch (error) {
      console.error('Lookup error:', error);
      throw error;
    } finally {
      setIsValidatingEmail(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    try {
      const recipientId = await lookupUserByEmail(email);
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      // First, get the document metadata
      const docId = selectedFiles[0]; // Assuming single file for now
      const metadataResponse = await fetch(`http://127.0.0.1:5000/docs/file/${docId}/metadata`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include'
      });

      if (!metadataResponse.ok) {
        throw new Error('Failed to fetch document metadata');
      }

      const documentMetadata = await metadataResponse.json();
      console.log('Debug - Document metadata:', documentMetadata);

      // Now create the share
      const shareResponse = await fetch('http://127.0.0.1:5000/share', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
        body: JSON.stringify({
          doc_id: docId,
          recipient_id: recipientId,
          document_metadata: {
            original_filename: documentMetadata.original_filename,
            file_path: documentMetadata.file_path,
            file_type: documentMetadata.file_type
          }
        })
      });

      console.log('Debug - Share request payload:', JSON.stringify({
        doc_id: docId,
        recipient_id: recipientId,
        document_metadata: documentMetadata
      }, null, 2));

      if (!shareResponse.ok) {
        const errorData = await shareResponse.json();
        throw new Error(errorData.error || 'Share request failed');
      }

      // Call onSuccess callback
      if (onSuccess) {
        onSuccess();
      }
      
      // Close modal
      onClose();

    } catch (error) {
      console.error('Share error:', error);
      setError(error instanceof Error ? error.message : 'Failed to share files');
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
          Share File
        </h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

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