import React from 'react';
import { Menu, Moon, Sun } from 'lucide-react';
import brandLogo from '../assets/Header_Brandname_logo.png';
import './Header.css';

const Header = ({ toggleSidebar, theme, toggleTheme, showMenu, isLanding }) => {
  return (
    <header className="header glass">
      <div className="header-inner">
        <div className="header-left">
          {showMenu && (
            <button className="menu-btn icon-btn" onClick={toggleSidebar} aria-label="Toggle Navigation">
              <Menu size={24} />
            </button>
          )}
          <div className="brand-group">
            <img src={brandLogo} alt="PregAI Logo" className="brand-logo" />
            <h1 className="brand-name">PregAI</h1>
            {isLanding && (
              <nav className="nav-links">
                <a href="#faq" className="nav-link">Questions</a>
                <a href="#resources" className="nav-link">Learning room</a>
                <a href="#support" className="nav-link">Support</a>
              </nav>
            )}
          </div>
        </div>
        
        <div className="header-right">
          <button className="theme-toggle" onClick={toggleTheme} title="Toggle Theme">
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
