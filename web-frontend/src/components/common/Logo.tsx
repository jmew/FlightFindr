import React from 'react';
import {
  SiChase,
} from '@icons-pack/react-simple-icons';
import { FaCreditCard, FaPlane } from 'react-icons/fa';
import CitiLogo from './CitiLogo';

const BANK_LOGO_MAP: { [key: string]: React.ReactNode } = {
  'Chase': <SiChase color="default" />,
  'Amex': <img src="https://upload.wikimedia.org/wikipedia/commons/7/7e/American_Express_Square_Logo.png" alt="American Express" style={{ width: '24px', height: '24px', borderRadius: '3px' }} />,
  'American Exp': <img src="https://upload.wikimedia.org/wikipedia/commons/7/7e/American_Express_Square_Logo.png" alt="American Express" style={{ width: '24px', height: '24px', borderRadius: '3px' }} />,
  'American Express': <img src="https://upload.wikimedia.org/wikipedia/commons/7/7e/American_Express_Square_Logo.png" alt="American Express" style={{ width: '24px', height: '24px', borderRadius: '3px' }} />,
  'Capital One': <img src="https://diversiq.com/wp-content/uploads/2024/04/Capital-One-Logo-Square.png" alt="Capital One" style={{ width: '24px', height: '24px', borderRadius: '3px' }} />,
  'Citi': <CitiLogo />,
};

const IGNORED_BANKS = ['Bilt', 'WF'];

const getLogo = (type: 'airline' | 'bank', name?: string, code?: string) => {
  if (type === 'airline') {
    if (code) {
      return (
        <img
          src={`https://www.gstatic.com/flights/airline_logos/70px/${code}.png`}
          alt={name}
          className="airline-logo-img"
          width="30"
          height="30"
        />
      );
    }
    return <FaPlane />;
  }

  // Bank logos
  if (name) {
    if (IGNORED_BANKS.some(ignoredBank => name.toLowerCase().includes(ignoredBank.toLowerCase()))) {
      return null; // Explicitly ignore Bilt and WF
    }

    const foundKey = Object.keys(BANK_LOGO_MAP).find(key => name.toLowerCase().includes(key.toLowerCase()));
    if (foundKey) {
      const logoComponent = BANK_LOGO_MAP[foundKey];
      if (logoComponent) {
        return logoComponent;
      }
    }
  }
  
  return <FaCreditCard />;
};

interface LogoProps {
  name: string;
  type: 'airline' | 'bank';
  code?: string;
}

const Logo: React.FC<LogoProps> = ({ name, type, code }) => {
  const logo = getLogo(type, name, code);
  if (!logo) return null; // Don't render anything if the logo is ignored

  if (type === 'bank') {
    return (
      <div className="tooltip-container">
        <span className={`logo-icon ${type}-logo`}>{logo}</span>
        <span className="tooltip-text">{name}</span>
      </div>
    );
  }

  return <span className={`logo-icon ${type}-logo`}>{logo}</span>;
};

export default Logo;