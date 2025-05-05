import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../services/authService'
import Input from '../components/Input'
import Button from '../components/Button'
import { Link } from 'react-router-dom';
import '../styles/main.css' 
import '../styles/AlertModal.css' 
import '../styles/modal.css' 
import ModalRecuperarContraseña from '../components/ForgotpasswordPage'



const LoginPage = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')  
  const [showModal, setShowModal] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await login(email, password)
      alert('Inicio de sesión exitoso')
      navigate('/') // Redirige al home o página de éxito
    } catch (error) {
      alert('Error al iniciar sesión')
    }

  }


  return (
    <>
    <form onSubmit={handleSubmit} className="form-container">
      <h2>Iniciar sesión</h2>
      <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Correo" />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Contraseña" />
      <Button type="submit">Iniciar sesión</Button>
      <p className='texto-chico'>
        ¿No tienes cuenta? <a href="/register">Registrate aquí</a>  
      </p>
      <p className='texto-chico'>
         ¿Olvidaste tu contraseña?{' '}
         <span onClick={() => setShowModal(true)}>
           Recuperala aquí
        </span>
      </p>
    </form>
    <ModalRecuperarContraseña visible={showModal} onClose={() => setShowModal(false)} />
    </>

    
  )
}

export default LoginPage
