import React from 'react';
import '../../styles/HomePage.css'; // Importamos el CSS separado
import NavBar from '../../components/NavBar'
export default function HomePage() {
  return (
    <div className="homepage">
        <NavBar showLoginButton={true} />

      {/* Contenido */}
      <main className="main-content">
        Bienvenido al Parque Industrial Polo 52
      </main>
    </div>
  );
}
