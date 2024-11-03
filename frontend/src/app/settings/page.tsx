'use client'
import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import LockIcon from '@/components/LockIcon'

interface User {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export default function Settings() {
  const router = useRouter();
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    old_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [error, setError] = useState('');

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) {
      router.push('/login');
      return;
    }
    const user = JSON.parse(userData);
    setFormData(prev => ({
      ...prev,
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email
    }));
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.old_password) {
      setError('Current password is required to make any changes');
      return;
    }

    if (formData.new_password || formData.confirm_password) {
      if (formData.new_password !== formData.confirm_password) {
        setError('New passwords do not match');
        return;
      }
    }
    
    setShowConfirmModal(true);
  };

  const confirmUpdate = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://127.0.0.1:5000/auth/update-profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Update failed');
      }

      localStorage.setItem('user', JSON.stringify(data.user));
      setShowConfirmModal(false);
      setShowSuccessModal(true);
      setTimeout(() => {
        setShowSuccessModal(false);
        router.push('/dashboard');
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
      setShowConfirmModal(false);
    }
  };

  return (
    <div className="flex min-h-screen justify-center items-center">
      <LockIcon />
      <div className="w-full max-w-3xl mx-auto p-8">
        <h1 className="text-6xl font-black text-navy text-center mb-12">Update Profile</h1>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && <p className="text-red-500 text-center">{error}</p>}
          
          <div className="space-y-6 mb-8">
            <h2 className="text-2xl font-bold text-navy">Profile Information</h2>
            
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">First Name</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
                  required
                />
              </div>
              <div className="flex-1 relative">
                <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">Last Name</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
                  required
                />
              </div>
            </div>

            <div className="relative">
              <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
                required
              />
            </div>

            <div className="relative">
              <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
                Current Password
              </label>
              <input
                type="password"
                value={formData.old_password}
                onChange={(e) => setFormData({...formData, old_password: e.target.value})}
                className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
                required
              />
              <p className="text-sm text-gray-600 mt-1">
                * Required to save any changes to your profile
              </p>
            </div>
          </div>

          <div className="space-y-6 pt-6 border-t border-gray-200">
            <h2 className="text-2xl font-bold text-navy">Change Password (Optional)</h2>
            
            <div className="relative">
              <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
                New Password
              </label>
              <input
                type="password"
                value={formData.new_password}
                onChange={(e) => setFormData({...formData, new_password: e.target.value})}
                className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
              />
            </div>

            <div className="relative">
              <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
                Confirm New Password
              </label>
              <input
                type="password"
                value={formData.confirm_password}
                onChange={(e) => setFormData({...formData, confirm_password: e.target.value})}
                className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
              />
            </div>
          </div>

          <div className="flex justify-between gap-4">
            <button
              type="submit"
              className="flex-1 bg-navy text-white font-black text-xl py-4 px-8 rounded-2xl hover:bg-opacity-90 transition-all"
            >
              Update Account
            </button>
            <button
              type="button"
              onClick={() => router.push('/dashboard')}
              className="flex-1 bg-navy text-white font-black text-xl py-4 px-8 rounded-2xl hover:bg-opacity-90 transition-all"
            >
              Cancel Update
            </button>
          </div>
        </form>

        {/* Confirmation Modal */}
        {showConfirmModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white p-8 rounded-2xl max-w-md w-full mx-4">
              <h2 className="text-2xl font-bold text-navy mb-4">Confirm Update</h2>
              <p className="text-navy mb-6">Are you sure you want to update your profile?</p>
              <div className="flex justify-end gap-4">
                <button
                  onClick={() => setShowConfirmModal(false)}
                  className="px-4 py-2 text-navy hover:underline"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmUpdate}
                  className="px-4 py-2 bg-navy text-white rounded-lg hover:bg-opacity-90"
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Success Modal */}
        {showSuccessModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white p-8 rounded-2xl max-w-md w-full mx-4">
              <h2 className="text-2xl font-bold text-navy mb-4">Success!</h2>
              <p className="text-navy">Your profile has been updated successfully.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}