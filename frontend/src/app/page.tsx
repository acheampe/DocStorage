'use client'
import React from 'react'
import Link from 'next/link'
import LockIcon from '@/components/LockIcon'

export default function Home() {
  return (
    <div className="flex min-h-screen relative overflow-hidden">
      {/* Left Section */}
      <div className="w-1/3 bg-navy p-8 flex flex-col items-center justify-center space-y-6 rounded-r-[25px] -ml-16 pl-16">
        <LockIcon />
        <Link href="/login" className="w-64 bg-gold text-white py-3 rounded-full text-lg font-semibold hover:bg-opacity-85 transition-all text-center"
          title="Sign in to your existing account">
          Login
        </Link>
        <Link href="/register" className="w-64 bg-gold text-white py-3 rounded-full text-lg font-semibold hover:bg-opacity-85 transition-all text-center"
          title="Create a new account to start storing documents">
          Register New User
        </Link>
      </div>

      {/* Right Section */}
      <div className="w-2/3 flex flex-col items-center justify-center p-8">
        <h1 className="text-6xl font-bold text-gold mb-4">DocStorage</h1>
        <h2 className="text-2xl font-bold text-navy text-center">
          Secure, Share, and Reference your documents
        </h2>
      </div>
    </div>
  );
}