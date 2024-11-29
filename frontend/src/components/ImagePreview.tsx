'use client'
import React, { useState } from 'react'

interface ImagePreviewProps {
  src: string
  alt: string
  onClose: () => void
}

export default function ImagePreview({ src, alt, onClose }: ImagePreviewProps) {
  const [imageError, setImageError] = useState(false);

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div className="relative max-w-4xl max-h-[90vh]" onClick={e => e.stopPropagation()}>
        {!imageError ? (
          <img 
            src={src} 
            alt={alt} 
            className="max-w-full max-h-[90vh] object-contain bg-gray-50 rounded"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="bg-gray-50 p-8 rounded text-center">
            <span className="material-symbols-rounded text-navy text-6xl mb-4">
              broken_image
            </span>
            <p className="text-navy">Failed to load image</p>
          </div>
        )}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-white hover:text-gold"
        >
          <span className="material-symbols-rounded text-3xl">close</span>
        </button>
      </div>
    </div>
  )
}