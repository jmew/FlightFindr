import React from 'react';
import {
  SiAerlingus,
  SiAeroflot,
  SiAeromexico,
  SiAirasia,
  SiAircanada,
  SiAirchina,
  SiAirfrance,
  SiAirindia,
  SiAirserbia,
  SiAirtransat,
  SiAmericanairlines,
  SiAna,
  SiAvianca,
  SiBritishairways,
  SiChinaeasternairlines,
  SiChinasouthernairlines,
  SiCopaairlines,
  SiDelta,
  SiEasyjet,
  SiEmirates,
  SiEthiopianairlines,
  SiEtihadairways,
  SiIberia,
  SiJapanairlines,
  SiJetblue,
  SiKlm,
  SiLotpolishairlines,
  SiLufthansa,
  SiNorwegian,
  SiQantas,
  SiQatarairways,
  SiRyanair,
  SiS7airlines,
  SiSaudia,
  SiSingaporeairlines,
  SiSouthwestairlines,
  SiTurkishairlines,
  SiUnitedairlines,
  SiVirginatlantic,
  SiWizzair,
  SiChase,
  SiAmericanexpress,
} from '@icons-pack/react-simple-icons';
import { FaCreditCard, FaPlane } from 'react-icons/fa';
import CitiLogo from './CitiLogo';

const AIRLINE_LOGO_MAP: { [key: string]: React.ReactNode } = {
  'Aer Lingus': <SiAerlingus color="default" />,
  'Aeroflot': <SiAeroflot color="default" />,
  'Aeroméxico': <SiAeromexico color="default" />,
  'AirAsia': <SiAirasia color="default" />,
  'Air Canada': <SiAircanada color="default" />,
  'Air China': <SiAirchina color="default" />,
  'Air France': <SiAirfrance color="default" />,
  'Air India': <SiAirindia color="default" />,
  'Air Serbia': <SiAirserbia color="default" />,
  'Air Transat': <SiAirtransat color="default" />,
  'American Airlines': <SiAmericanairlines color="default" />,
  'ANA': <SiAna color="default" />,
  'Avianca': <SiAvianca color="default" />,
  'British Airways': <SiBritishairways color="default" />,
  'China Eastern Airlines': <SiChinaeasternairlines color="default" />,
  'China Southern Airlines': <SiChinasouthernairlines color="default" />,
  'Copa Airlines': <SiCopaairlines color="default" />,
  'Delta': <SiDelta color="default" />,
  'easyJet': <SiEasyjet color="default" />,
  'Emirates': <SiEmirates color="default" />,
  'Ethiopian Airlines': <SiEthiopianairlines color="default" />,
  'Etihad Airways': <SiEtihadairways color="default" />,
  'Iberia': <SiIberia color="default" />,
  'Japan Airlines': <SiJapanairlines color="default" />,
  'JetBlue': <SiJetblue color="default" />,
  'KLM': <SiKlm color="default" />,
  'LOT Polish Airlines': <SiLotpolishairlines color="default" />,
  'Lufthansa': <SiLufthansa color="default" />,
  'Norwegian': <SiNorwegian color="default" />,
  'Qantas': <SiQantas color="default" />,
  'Qatar Airways': <SiQatarairways color="default" />,
  'Ryanair': <SiRyanair color="default" />,
  'S7 Airlines': <SiS7airlines color="default" />,
  'Saudia': <SiSaudia color="default" />,
  'Singapore Airlines': <SiSingaporeairlines color="default" />,
  'Southwest Airlines': <SiSouthwestairlines color="default" />,
  'Turkish Airlines': <SiTurkishairlines color="default" />,
  'United': <SiUnitedairlines color="default" />,
  'Virgin Atlantic': <SiVirginatlantic color="default" />,
  'Wizz Air': <SiWizzair color="default" />,
};

const BANK_LOGO_MAP: { [key: string]: React.ReactNode } = {
  'Chase': <SiChase color="default" />,
  'American Express': <SiAmericanexpress color="default" />,
  'Citi': <CitiLogo />,
};

const getLogo = (name: string, type: 'airline' | 'bank') => {
  const map = type === 'airline' ? AIRLINE_LOGO_MAP : BANK_LOGO_MAP;
  const foundKey = Object.keys(map).find(key => name.toLowerCase().includes(key.toLowerCase()));
  
  if (foundKey) {
    const logoComponent = map[foundKey];
    if (logoComponent) {
      return logoComponent;
    }
  }
  
  return type === 'airline' ? <FaPlane /> : <FaCreditCard />;
};

interface LogoProps {
  name: string;
  type: 'airline' | 'bank';
}

const Logo: React.FC<LogoProps> = ({ name, type }) => {
  return <span className={`logo-icon ${type}-logo`}>{getLogo(name, type)}</span>;
};

export default Logo;