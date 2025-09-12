import React, { useState, useEffect } from 'react';
import './App.css';
import ChatConversation from './components/chat/ChatConversation';
import AuthModal from './components/common/AuthModal';
import { useChat } from './hooks/useChat';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';

const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    if (import.meta.env.DEV) {
      const urlParams = new URLSearchParams(window.location.search);
      const forceOauth = urlParams.get('force_oauth') === 'true';
      return !forceOauth;
    }
    return !!localStorage.getItem('google_auth_token');
  });

  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);

  const handleAuthRequired = (message: string) => {
    setPendingMessage(message);
    setAuthModalOpen(true);
  };

  const {
    messages,
    input,
    setInput,
    isLoading,
    thought,
    elapsedTime,
    handleFormSubmit,
    handleSendMessage,
    handleStop,
  } = useChat({ isAuthenticated, onAuthRequired: handleAuthRequired });

  // Effect to handle the post-login action
  useEffect(() => {
    if (isAuthenticated && pendingMessage) {
      handleSendMessage(pendingMessage);
      setPendingMessage(null);
    }
  }, [isAuthenticated, pendingMessage, handleSendMessage]);

  // Effect to listen for the auth popup message
  useEffect(() => {
    const handleAuthMessage = (event: MessageEvent) => {
      const expectedOrigin = new URL(API_BASE_URL).origin;
      if (event.origin !== expectedOrigin) {
        return;
      }
      
      if (event.data && event.data.access_token) {
        localStorage.setItem('google_auth_token', JSON.stringify(event.data));
        setIsAuthenticated(true);
        setAuthModalOpen(false);
      }
    };

    window.addEventListener('message', handleAuthMessage);

    return () => {
      window.removeEventListener('message', handleAuthMessage);
    };
  }, []); // Empty dependency array ensures this runs only once

  return (
    <main className="chat-app">
      <AuthModal show={authModalOpen} onClose={() => setAuthModalOpen(false)} />
      <ChatConversation
        messages={messages}
        input={input}
        setInput={setInput}
        isLoading={isLoading}
        thought={thought}
        elapsedTime={elapsedTime}
        handleFormSubmit={handleFormSubmit}
        handleSuggestionClick={handleSendMessage}
        handleStop={handleStop}
      />
    </main>
  );
};

export default App;
