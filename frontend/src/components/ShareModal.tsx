import React, { useState } from 'react';

interface ShareModalProps {
  docId: number;
  onClose: () => void;
  onShare?: (email: string, permissions: SharePermissions) => Promise<void>;
  isBulkShare?: boolean;
  selectedCount?: number;
  className?: string;
  infoMessage?: React.ReactNode;
}

interface SharePermissions {
  can_view: boolean;
  can_download: boolean;
  can_reshare: boolean;
}

export default function ShareModal({ docId, onClose, onShare, isBulkShare, selectedCount, className, infoMessage }: ShareModalProps) {
  const [email, setEmail] = useState('');
  const [permissions, setPermissions] = useState<SharePermissions>({
    can_view: true,
    can_download: false,
    can_reshare: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    try {
      await onShare(email, permissions);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to share document');
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

          <div className="mb-6">
            <label className="block text-navy font-medium mb-2">Permissions</label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={permissions.can_view}
                  onChange={(e) => setPermissions({...permissions, can_view: e.target.checked})}
                  className="mr-2"
                  disabled
                />
                Can View
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={permissions.can_download}
                  onChange={(e) => setPermissions({...permissions, can_download: e.target.checked})}
                  className="mr-2"
                />
                Can Download
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={permissions.can_reshare}
                  onChange={(e) => setPermissions({...permissions, can_reshare: e.target.checked})}
                  className="mr-2"
                />
                Can Reshare
              </label>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              {error}
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