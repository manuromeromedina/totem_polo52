import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LoginPage from '../Pages/LoginPage'
import RegisterPage from '../Pages/RegisterPage'
import ForgotpasswordPage from '../components/ForgotpasswordPage'


const AppRouter = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotpasswordPage />} />
      <Route path="/recuperar" element={<ForgotpasswordPage />} />

      
    </Routes>
  </BrowserRouter>
)

export default AppRouter
