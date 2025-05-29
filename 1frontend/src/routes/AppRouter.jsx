import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LoginPage from '../Pages/Auth/LoginPage'
import RegisterPage from '../Pages/Auth/RegisterPage'
import ForgotpasswordPage from '../components/ForgotpasswordPage'
import HomePage from '../Pages/Home/HomePage'
import EmpresaDashboard from '../Pages/Admin/EmpresaDashboard'


const AppRouter = () => (
  <BrowserRouter>
    <Routes>
      {/* Pública */}
      <Route path="/" element={<HomePage />} />
     
     
      {/* Auth */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotpasswordPage />} />
      <Route path="/recuperar" element={<ForgotpasswordPage />} />


     {/* Admin */}
     <Route path="/admin" element={<EmpresaDashboard />} />

      
    </Routes>
  </BrowserRouter>
)

export default AppRouter
