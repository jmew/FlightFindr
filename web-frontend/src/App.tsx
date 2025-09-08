import './App.css';
import ChatConversation from './components/chat/ChatConversation';
import { useChat } from './hooks/useChat';

const App: React.FC = () => {
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
  } = useChat();

  return (
    <main className="chat-app">
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
