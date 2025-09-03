import React from 'react';
import {
  SiChase,
  SiAmericanexpress,
} from '@icons-pack/react-simple-icons';
import { FaCreditCard, FaPlane } from 'react-icons/fa';
import CitiLogo from './CitiLogo';

const BANK_LOGO_MAP: { [key: string]: React.ReactNode } = {
  'Chase': <SiChase color="default" />,
  'American Express': <SiAmericanexpress color="default" />,
  'Citi': <CitiLogo />,
};

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
  return <span className={`logo-icon ${type}-logo`}>{getLogo(type, name, code)}</span>;
};

export default Logo;