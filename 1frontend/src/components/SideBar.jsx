import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import '../styles/SideBar.css';


const Sidebar = ({ empresaNombre }) => {
  const [active, setActive] = useState("informacion");

  const navItems = [
    { id: "informacion", label: "Información" },
    { id: "servicios", label: "Servicios" },
    { id: "contacto", label: "Contacto" },
    { id: "ubicacion", label: "Ubicación" }
  ];

  return (
    <div className="container">
      <aside className="sidebar">
        <div className="empresa">
          <div className="avatar" />
          <span>{empresaNombre}</span>
        </div>
        <nav>
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-button ${active === item.id ? "active" : ""}`}
              onClick={() => setActive(item.id)}
            >
              {item.label}
            </button>
          ))}
          <div className="cerrar-sesion">Cerrar Sesión</div>
        </nav>
      </aside>
      <main className="content">
        <h1>{navItems.find(item => item.id === active).label}</h1>
      </main>
    </div>
  );
};

export default Sidebar;
