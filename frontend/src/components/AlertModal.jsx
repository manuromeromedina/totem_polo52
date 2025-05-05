// src/components/AlertModal.jsx

import React from 'react';
import '../styles/AlertModal.css';  // Asegúrate de tener un archivo CSS para los estilos del modal

const AlertModal = ({ message, error, onClose }) => {
  return (
    <div className="modal-overlay">
      <div className={`modal ${error ? 'error' : 'success'}`}>
        <p>{message}</p>
        <button onClick={onClose}>Cerrar</button>
      </div>
    </div>
  );
};

export default AlertModal;
