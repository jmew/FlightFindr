import type { Message } from '../../types';
import MessageBubble from '../MessageBubble';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  thought: string | null;
  elapsedTime: number;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  thought,
  elapsedTime,
}) => (
  <div className="chat-conversation">
    {messages.map((msg, index) => (
      <MessageBubble key={index} msg={msg} />
    ))}
    {isLoading && (
      <div className="thought-display">
        <svg className="spinner" viewBox="0 0 50 50">
          <circle
            className="path"
            cx="25"
            cy="25"
            r="20"
            fill="none"
            strokeWidth="4"
          />
        </svg>
        {thought && (
          <span className="thought">
            {thought} ({elapsedTime}s, This may take up to 2 minutes...)
          </span>
        )}
      </div>
    )}
  </div>
);

export default MessageList;