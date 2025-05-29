// components/ModalRecuperarContraseña.jsx
import React from 'react'
import '../styles/ForgotPasswordModal.css' // crea un archivo para los estilos si no lo tienes

const ModalRecuperarContraseña = ({ visible, onClose }) => {
  const handleSubmit = (e) => {
    e.preventDefault()
    alert('Si el correo existe, se enviará un link de recuperación.')
    onClose()
  }
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) { // Asegura que el clic es en la superposición y no dentro del modal
      onClose()
    }
  }

  if (!visible) return null

  return (
    <div className="modal-overlay-recuperacion" onClick={handleOverlayClick}>
      <div className="modal-recuperacion">
        <h2>Recuperación de contraseña</h2>
        <hr />
        <p className='mail' >Ingresá tu mail para recuperar contraseña</p>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Correo@dominio.com"
            required
            className="modal-input-recuperacion"
          />
          <button type="submit" className="modal-button-recuperacion">Restablecer Contraseña</button>
        </form>
        <p className="modal-text-recuperacion">
          Al presionar “Restablecer Contraseña” se te enviará un correo con un link
        </p>
      </div>
    </div>
  )
}

export default ModalRecuperarContraseña
