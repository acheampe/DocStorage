'use client'
import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import LockIcon from '@/components/LockIcon'

export default function Login() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch('http://127.0.0.1:5000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }
      
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  return (
    <div className="flex min-h-screen justify-center items-center">
      <LockIcon />

      {/* Left Section - Form */}
      <div className="w-2/3 py-12 px-20 relative">
        <h1 className="text-6xl font-black text-navy text-center mb-12">Login</h1>
        
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-6">
          {error && <p className="text-red-500 text-center">{error}</p>}

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
          </div>

          <div className="text-sm text-left">
            <Link href="/forgot-password" className="text-navy hover:underline">
              Forgot Password? <span className="text-navy font-bold">Retrieve</span>
            </Link>
          </div>

          <div className="flex flex-col items-center gap-4">
            <button
              type="submit"
              className="bg-navy text-white font-black text-xl py-2 px-8 rounded-2xl hover:bg-opacity-90 transition-all"
            >
              Login
            </button>
            <Link href="/register" className="text-sm">
              Don't have an account? <span className="text-navy font-bold">Register</span>
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