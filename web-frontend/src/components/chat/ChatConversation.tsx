import React, { useEffect, useRef, useState, useLayoutEffect } from 'react';
import { FiSend, FiSquare } from 'react-icons/fi';
import type { Message } from '../../types';
import MessageList from './MessageList';
import SuggestionBubbles from './SuggestionBubbles';
import WelcomeScreen from '../home/WelcomeScreen';

interface ChatConversationProps {
  messages: Message[];
  input: string;
  setInput: (input: string) => void;
  isLoading: boolean;
  thought: string | null;
  elapsedTime: number;
  handleFormSubmit: (e: React.FormEvent) => void;
  handleSuggestionClick: (suggestion: string) => void;
  handleStop: () => void;
}

const placeholderSuggestions = [
  'Find me the best flight deals from Seattle to Hong Kong on October 4th',
  'What are the cheapest points options for a business class ticket to Tokyo?',
  'Show me award flights from LAX to London next month',
];

const suggestionBubbles = [
  'SEA -> JFK Oct 4',
  'HKG -> HND Dec 12',
  'LHR -> DOH Feb 4',
];

import styles from './ChatConversation.module.css';

const ChatConversation: React.FC<ChatConversationProps> = ({
  messages,
  input,
  setInput,
  isLoading,
  thought,
  elapsedTime,
  handleFormSubmit,
  handleSuggestionClick,
  handleStop,
}) => {
  const lastMessageRef = useRef<HTMLDivElement | null>(null);
  const isChatEmpty = messages.length === 0;
  const [placeholder, setPlaceholder] = useState('');
  const [suggestionIndex, setSuggestionIndex] = useState(0);

  useEffect(() => {
    // Prevent body scroll on mobile when the welcome screen is visible.
    if (isChatEmpty && window.innerWidth <= 768) {
      document.body.classList.add('empty-chat-mobile-lock');
    } else {
      document.body.classList.remove('empty-chat-mobile-lock');
    }
    // Cleanup function to remove the class when the component unmounts
    return () => {
      document.body.classList.remove('empty-chat-mobile-lock');
    };
  }, [isChatEmpty]);

  useEffect(() => {
    if (isChatEmpty) {
      const interval = setInterval(() => {
        setSuggestionIndex((prev) => (prev + 1) % placeholderSuggestions.length);
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [isChatEmpty]);

  useEffect(() => {
    if (isChatEmpty) {
      let i = 0;
      const currentSuggestion = placeholderSuggestions[suggestionIndex];
      const typingEffect = setInterval(() => {
        setPlaceholder(currentSuggestion.substring(0, i + 1));
        i++;
        if (i === currentSuggestion.length) {
          clearInterval(typingEffect);
        }
      }, 30);
      return () => clearInterval(typingEffect);
    }
  }, [isChatEmpty, suggestionIndex]);

  useLayoutEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.sender === 'user') {
      lastMessageRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length]);

  return (
    <div className={`${styles.mainContent} ${isChatEmpty ? styles.emptyChat : ''}`}>
      <WelcomeScreen handleSendMessage={handleSuggestionClick} isChatEmpty={isChatEmpty} />
      {!isChatEmpty && (
        <div className={styles.chatConversation}>
          <MessageList
            messages={messages}
            isLoading={isLoading}
            thought={thought}
            elapsedTime={elapsedTime}
            lastMessageRef={lastMessageRef}
          />
        </div>
      )}
      <div className={styles.inputArea}>
        <form className={styles.inputForm} onSubmit={handleFormSubmit}>
          <input
            type="text"
            className={styles.inputField}
            placeholder={
              isChatEmpty
                ? placeholder
                : "Tell me where you'd like to fly to"
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          {isLoading ? (
            <button
              type="button"
              className={styles.stopButton}
              onClick={handleStop}
            >
              <FiSquare className={styles.sendIcon} />
            </button>
          ) : (
            <button
              type="submit"
              className={styles.sendButton}
              disabled={!input.trim()}
            >
              <FiSend className={styles.sendIcon} />
            </button>
          )}
        </form>
        {isChatEmpty && (
          <SuggestionBubbles
            suggestions={suggestionBubbles}
            onSuggestionClick={handleSuggestionClick}
          />
        )}
      </div>
    </div>
  );
};

export default ChatConversation;
