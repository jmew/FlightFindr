import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Message } from '../../types';
import FlightDeals from '../deals/FlightDealsTable';
import ToolCall from './ToolCall';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
  msg: Message;
}

const MessageBubble = React.forwardRef<HTMLDivElement, MessageBubbleProps>(
  ({ msg }, ref) => {
    return (
      <div
        ref={ref}
        className={`${styles.message} ${msg.sender === 'user' ? styles.userMessage : styles.botMessage}`}
      >
        {msg.text && <ReactMarkdown>{msg.text}</ReactMarkdown>}
        {msg.tools && <ToolCall tools={msg.tools} />}
        {msg.flightData && msg.flightData.length > 0 && (
          <div className="flight-deals-container">
            <FlightDeals deals={msg.flightData} />
          </div>
        )}
      </div>
    );
  },
);

export default MessageBubble;
