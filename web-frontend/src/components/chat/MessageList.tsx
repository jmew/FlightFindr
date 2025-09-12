import type { Message } from '../../types';
import MessageBubble from './MessageBubble';
import styles from './MessageList.module.css';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  thought: string | null;
  elapsedTime: number;
  lastMessageRef: React.RefObject<HTMLDivElement | null>;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  thought,
  elapsedTime,
  lastMessageRef,
}) => (
  <div className="chat-conversation">
    {messages.map((msg, index) => {
      let userQuery: string | undefined;
      if (msg.sender === 'bot' && msg.flightData) {
        for (let i = index - 1; i >= 0; i--) {
          if (messages[i].sender === 'user') {
            userQuery = messages[i].text;
            break;
          }
        }
      }
      return (
        <MessageBubble
          key={index}
          msg={msg}
          userQuery={userQuery}
          ref={index === messages.length - 1 ? lastMessageRef : null}
        />
      );
    })}
    {isLoading && (
      <div className={styles.thoughtDisplay}>
        <svg className={styles.spinner} viewBox="0 0 50 50">
          <circle
            className={styles.path}
            cx="25"
            cy="25"
            r="20"
            fill="none"
            strokeWidth="4"
          />
        </svg>
        {thought && (
          <span className={styles.thought}>
            {thought} ({elapsedTime}s, This may take up to 2 minutes)
          </span>
        )}
      </div>
    )}
  </div>
);

export default MessageList;
