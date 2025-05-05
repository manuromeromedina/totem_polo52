import { useState } from "react";
import AlertModal from "../components/AlertModal";
import './ForgotPasswordPage.css';

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [modal, setModal] = useState({ show: false, message: "", error: false });

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const res = await fetch("http://localhost:3000/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.message || "Error desconocido");
      }

      setModal({ show: true, message: "El email de recuperación fue enviado", error: false });
    } catch (error) {
      setModal({ show: true, message: error.message, error: true });
    }
  };

  return (
    <div className="forgot-container">
      <h2>Recuperar Contraseña</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Ingresá tu email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <button type="submit">Enviar</button>
      </form>

      {modal.show && <AlertModal message={modal.message} error={modal.error} onClose={() => setModal({ show: false })} />}
    </div>
  );
};

export default ForgotPasswordPage;



