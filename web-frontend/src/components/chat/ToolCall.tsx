import { useState } from 'react';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';
import type { Tool } from '../../types';
import PlaneIcon from '../../assets/plane-icon.svg';
import styles from './ToolCall.module.css';

interface ToolCallProps {
  tools: Tool[];
}

const ToolCall = ({ tools }: ToolCallProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={styles.toolCallContainer}>
      <button
        className={styles.toolCallToggle}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <img src={PlaneIcon} className={styles.toolCallIcon} alt="Tool" />
        <span>{isExpanded ? 'Hide thinking' : 'Show thinking'}</span>
        {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
      </button>
      {isExpanded &&
        tools.map((tool, index) => (
          <div key={index} className={styles.toolCallCard}>
            <p className={styles.toolCallHeader}>
              <strong>Tool Call:</strong> {tool.name}
            </p>
            <pre className={styles.toolCallArgs}>
              <code>{JSON.stringify(tool.args, null, 2)}</code>
            </pre>
            {tool.result && tool.name !== 'check_flight_points_prices' && (
              <>
                <p>
                  <strong>Result:</strong>
                </p>
                <pre className={styles.toolCallResult}>
                  <code>{tool.result}</code>
                </pre>
              </>
            )}
            {tool.error && (
              <>
                <p>
                  <strong>Error:</strong>
                </p>
                <pre className={styles.toolCallError}>
                  <code>{tool.error}</code>
                </pre>
              </>
            )}
          </div>
        ))}
    </div>
  );
};

export default ToolCall;
