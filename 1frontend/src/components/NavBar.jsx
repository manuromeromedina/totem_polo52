import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/HomePage.css'; // o el path correcto a tu CSS

const NavBar = ({ showLoginButton = false }) => {
  return (
    <div className="NavBar">
        {/* Navbar */}
        <header className="navbar">
          <div className="logo-container">
            <img
              src="/logo-negro-fn.png"
              alt="Polo 52"
              className="logo"
            />
          </div>
          {showLoginButton && (
             <Link to="/login" className="login-button">Iniciar Sesión</Link>
      )}
        </header>
      </div> 
  );
};

export default NavBar;
