import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { register } from '../services/authService'
import Input from '../components/Input'
import Button from '../components/Button'

const RegisterPage = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await register(email, password)
      alert('Registro exitoso')
      navigate('/login') // Redirige a la página de login después del registro
    } catch (error) {
      alert('Error al registrar')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="form-container">
      <h2>Registrarse</h2>
      <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Correo" />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Contraseña" />
      <Button type="submit">Registrarse</Button>
      <p>
        ¿Ya tienes cuenta? <a href="/login">Inicia sesión aquí</a>
      </p>
    </form>
  )
}

export default RegisterPage
