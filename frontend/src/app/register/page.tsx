'use client'
import React, { useState } from 'react'
import Link from 'next/link'
import LockIcon from '@/components/LockIcon'
import { validatePassword } from '@/utils/passwordValidation'
import { useRouter } from 'next/navigation'

export default function Register() {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    password_confirmation: ''
  });
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const passwordValidation = validatePassword(formData.password);
    if (!passwordValidation.isValid) {
      setError(passwordValidation.message);
      return;
    }

    if (formData.password !== formData.password_confirmation) {
      setError('Passwords do not match');
      return;
    }

    try {
      const response = await fetch('http://127.0.0.1:5000/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Registration failed');
      }

      // After successful registration, perform login
      const loginResponse = await fetch('http://127.0.0.1:5000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password
        }),
      });

      const loginData = await loginResponse.json();
      if (!loginResponse.ok) {
        throw new Error(loginData.error || 'Login failed');
      }

      localStorage.setItem('token', loginData.token);
      localStorage.setItem('user', JSON.stringify(loginData.user));
      
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    }
  };

  return (
    <div className="flex min-h-screen justify-center items-center">
      <LockIcon />

      {/* Left Section - Form */}
      <div className="w-2/3 py-12 px-20 relative">
        <h1 className="text-6xl font-black text-navy text-center mb-12">Create Account</h1>
        
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-6">
        {error && <p className="text-red-500 text-center">{error}</p>}
        
        <div className="flex gap-4">
            <div className="flex-1 relative">
            <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
                First Name
            </label>
            <input
                type="text"
                placeholder="First Name"
                className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
                value={formData.first_name}
                onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                required
            />
            </div>
            <div className="flex-1 relative">
            <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
                Last Name
            </label>
            <input
                type="text"
                placeholder="Last Name"
                className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
                value={formData.last_name}
                onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                required
            />
            </div>
        </div>

        <div className="relative">
            <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
            Email
            </label>
            <input
            type="email"
            placeholder="Email"
            className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            required
            />
        </div>

        <div className="relative">
            <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
            Password
            </label>
            <input
            type="password"
            placeholder="Password"
            className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            required
            />
            <p className="text-sm text-gray-600 mt-1">
              Min. 8 characters with uppercase, lowercase, number & special character
            </p>
        </div>

        <div className="relative">
            <label className="absolute -top-3 left-4 bg-white px-2 text-navy font-medium">
            Confirm Password
            </label>
            <input
            type="password"
            placeholder="Confirm Password"
            className="w-full p-4 border-4 border-gold border-opacity-45 rounded-2xl"
            value={formData.password_confirmation}
            onChange={(e) => setFormData({...formData, password_confirmation: e.target.value})}
            required
            />
            <p className="text-sm text-gray-600 mt-1">
              Re-enter password to confirm
            </p>
        </div>

        <div className="flex flex-col items-center gap-4">
            <button
            type="submit"
            className="bg-navy text-white font-black text-xl py-2 px-8 rounded-2xl hover:bg-opacity-90 transition-all"
            >
            Create Account
            </button>
            <Link href="/login" className="text-sm">
            Already have an account? <span className="text-navy font-bold">Login</span>
            </Link>
        </div>
        </form>
      </div>

      {/* Right Section - Navy Background */}
      <div className="w-1/3 bg-navy rounded-l-[25px] flex flex-col items-center justify-center text-center p-8 min-h-screen">
        <h2 className="text-6xl font-bold text-gold mb-4">DocStorage</h2>
        <p className="text-3xl font-bold text-white">
          Secure, Share, and Reference your documents
        </p>
      </div>
    </div>
  );
}