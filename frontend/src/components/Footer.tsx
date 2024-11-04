'use client'
import React from 'react'

export default function Footer() {
  return (
    <footer className="bg-navy p-4 w-full mt-auto">
      <div className="container mx-auto flex justify-center items-center">
        <p className="text-white text-sm">
          © {new Date().getFullYear()} DocStorage. All rights reserved.
        </p>
      </div>
    </footer>
  );
}