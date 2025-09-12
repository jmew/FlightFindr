import React from 'react';
import styles from './AuthModal.module.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';

interface AuthModalProps {
  show: boolean;
  onClose: () => void;
}

const AuthModal: React.FC<AuthModalProps> = ({ show, onClose }) => {
  if (!show) {
    return null;
  }

  const handleLogin = () => {
    const authUrl = `${API_BASE_URL}/auth/google`;
    window.open(authUrl, 'authWindow', 'width=500,height=600');
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <h2>Authentication Required</h2>
        <p>Please sign in with your Google account to continue.</p>
        <button onClick={handleLogin} className={styles.loginButton}>
            Sign in with Google
        </button>
        <button onClick={onClose} className={styles.closeButton}>
            Cancel
        </button>
      </div>
    </div>
  );
};

export default AuthModal;
