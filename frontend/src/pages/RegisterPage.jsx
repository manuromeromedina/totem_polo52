import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { register } from '../services/authService'
import Input from '../components/Input'
import Button from '../components/Button'
import '../styles/main.css'

const RegisterPage = () => {
  const [nombre, setNombre] = useState('')
  const [apellido, setApellido] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [repeatPassword, setRepeatPassword] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password !== repeatPassword) {
      alert('Las contraseñas no coinciden')
      return
    }
    try {
      await register({ nombre, apellido, email, password })      
      alert('Registro exitoso')
      navigate('/login') // Redirige a la página de login después del registro
    } catch (error) {
      alert('Error al registrar')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="form-container">
      <h2>Registrarse</h2>
      <Input type="text" value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre" />
      <Input type="text" value={apellido} onChange={(e) => setApellido(e.target.value)} placeholder="Apellido" />
      <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Correo" />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Contraseña" />
      <Input type="password" value={repeatPassword} onChange={(e) => setRepeatPassword(e.target.value)} placeholder="Repetir Contraseña" />
      <Button type="submit">Registrarse</Button>
      <p className='texto-chico'>
        ¿Ya tienes cuenta? <a href="/login">Inicia sesión aquí</a>
      </p>
    </form>
  )
}

export default RegisterPage
