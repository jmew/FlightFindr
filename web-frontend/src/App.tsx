import React, { useState, useEffect } from 'react';
import './App.css';
import ChatConversation from './components/chat/ChatConversation';
import AuthModal from './components/common/AuthModal';
import { useChat } from './hooks/useChat';

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

  const handleAuthSuccess = (tokens: any) => {
    localStorage.setItem('google_auth_token', JSON.stringify(tokens));
    setIsAuthenticated(true);
    setAuthModalOpen(false);
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
  } = useChat({ isAuthenticated, onAuthRequired: handleAuthRequired, onAuthSuccess: handleAuthSuccess });

  // Effect to handle the post-login action
  useEffect(() => {
    if (isAuthenticated && pendingMessage) {
      handleSendMessage(pendingMessage);
      setPendingMessage(null);
    }
  }, [isAuthenticated, pendingMessage, handleSendMessage]);

  return (
    <main className="chat-app">
      <AuthModal show={authModalOpen} onClose={() => setAuthModalOpen(false)} onAuthSuccess={handleAuthSuccess} />
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
