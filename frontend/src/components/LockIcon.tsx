'use client'
import { useRouter } from 'next/navigation'

export default function LockIcon() {
  const router = useRouter();

  const handleClick = () => {
    const token = localStorage.getItem('token');
    if (token) {
      router.push('/dashboard');
    } else {
      router.push('/');
    }
  };

  return (
    <div className="fixed top-5 left-5">
      <span 
        className="material-symbols-rounded text-gold text-5xl cursor-pointer hover:opacity-80 transition-all" 
        onClick={handleClick}
      >
        lock
      </span>
    </div>
  );
}