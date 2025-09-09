import React, { useState } from 'react';
import { Tabs, Tab } from 'react-bootstrap';
import MultiCityForm from './MultiCityForm';
import styles from './WelcomeScreen.module.css';

interface WelcomeScreenProps {
  handleSendMessage: (message: string) => void;
  isChatEmpty: boolean;
  onTabSelect: (key: string) => void;
}

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  handleSendMessage,
  isChatEmpty,
  onTabSelect,
}) => {
  const [key, setKey] = useState('single-flight');

  if (!isChatEmpty) {
    return null; // Don't render if chat has started
  }

  const handleTabSelect = (k: string | null) => {
    const newKey = k || 'single-flight';
    setKey(newKey);
    onTabSelect(newKey);
  };

  return (
    <div className={styles.welcomeContainer}>
      <h1 className={styles.welcomeTitle}>
        Meet <span className={styles.welcomeTitleName}>Miles</span>, your AI-powered flight finder
      </h1>
      <div className={styles.searchFormContainer}>
        <Tabs
          id="search-tabs"
          activeKey={key}
          onSelect={handleTabSelect}
          className={`mb-3 ${styles.navTabs}`}
          justify
        >
          <Tab eventKey="single-flight" title="One-way / Round-trip">
            {/* <p className="text-muted text-center">
              Start a conversation below to find the best flight deals. For example: "Find me a business class flight from SFO to Tokyo in the next 3 months"
            </p> */}
          </Tab>
          <Tab eventKey="multi-city" title="Multi-City Itinerary">
            <MultiCityForm handleSendMessage={handleSendMessage} />
          </Tab>
        </Tabs>
      </div>
    </div>
  );
};

export default WelcomeScreen;
