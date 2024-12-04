'use client'
import React, { useState, useEffect } from 'react'

interface ImagePreviewProps {
  src: string
  alt: string
  onClose: () => void
}

export default function ImagePreview({ src, alt, onClose }: ImagePreviewProps) {
  const [imageError, setImageError] = useState(false);
  const [imageSrc, setImageSrc] = useState<string | null>(null);

  useEffect(() => {
    const fetchImage = async () => {
      try {
        const token = localStorage.getItem('token');
        console.log('Fetching image:', src);
        
        const response = await fetch(src, {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Server response:', errorText);
          throw new Error('Failed to load image');
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setImageSrc(url);
      } catch (error) {
        console.error('Error fetching image:', error);
        setImageError(true);
      }
    };

    fetchImage();
    
    return () => {
      if (imageSrc) {
        URL.revokeObjectURL(imageSrc);
      }
    };
  }, [src]);

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div className="relative max-w-4xl max-h-[90vh]" onClick={e => e.stopPropagation()}>
        {!imageError ? (
          imageSrc ? (
            <img 
              src={imageSrc}
              alt={alt} 
              className="max-w-full max-h-[90vh] object-contain bg-gray-50 rounded"
            />
          ) : (
            <div className="bg-gray-50 p-8 rounded text-center">
              <span className="material-symbols-rounded text-navy text-6xl mb-4">
                hourglass_empty
              </span>
              <p className="text-navy">Loading image...</p>
            </div>
          )
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
  );
}