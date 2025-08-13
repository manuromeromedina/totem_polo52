// app/auth/auth-pending.component.ts
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-auth-pending',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="auth-pending-container">
      <div class="pending-box">
        <!-- Header con estilo del reset password -->
        <div class="header">
          <h2>
            <i class="fas fa-user-clock" style="margin-right: 12px; font-size: 1.5rem"></i>
            Cuenta No Registrada
          </h2>
          <p class="subtitle">Necesitas que te creen una cuenta</p>
        </div>

        <!-- Contenido principal -->
        <div class="content">
          <!-- Saludo personalizado -->
          <div class="user-greeting">
            <div class="avatar-container">
              <i class="fas fa-user"></i>
            </div>
            <h3>¡Hola <strong>{{ userName }}</strong>!</h3>
            <p class="user-email">
              <i class="fas fa-envelope"></i>
              {{ userEmail }}
            </p>
          </div>

          <!-- Mensaje principal -->
          <div class="status-message">
            <div class="status-icon">
              <i class="fas fa-user-plus"></i>
            </div>
            <div class="status-text">
              <h4>Tu email no está registrado</h4>
              <p>Necesitas contactar al administrador del Polo 52 para que te cree una cuenta en el sistema.</p>
            </div>
          </div>

          <!-- Información de contacto -->
          <div class="contact-section">
            <h4>
              <i class="fas fa-phone-alt"></i>
              Enviar Email al Admin
            </h4>
            <div class="contact-items">
              <div class="contact-item">
                <i class="fas fa-envelope"></i>
                <div class="contact-details">
                  <span class="contact-label">Email</span>
                  <span class="contact-value">admin&#64;polo52.com</span>
                </div>
              </div>
              <div class="contact-item">
                <i class="fas fa-phone"></i>
                <div class="contact-details">
                  <span class="contact-label">Teléfono</span>
                  <span class="contact-value">+54 351 XXX-XXXX</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Botones de acción -->
          <div class="button-group">
            <button type="button" class="primary-button" (click)="contactAdmin()">
              <i class="fas fa-paper-plane"></i>
              Enviar Email al Admin
            </button>
            <button type="button" class="secondary-button" (click)="goToLogin()">
              <i class="fas fa-arrow-left"></i>
              Volver al Login
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    /* Contenedor principal con imagen de fondo */
    .auth-pending-container {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      /* Fallback si no tienes la imagen: 
      background: url('/assets/images/iniciosesion.jpg') center/cover no-repeat; */
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      display: flex;
      justify-content: center;
      align-items: center;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      margin: 0;
      padding: 20px;
      box-sizing: border-box;
    }

    /* Overlay oscuro sobre la imagen */
    .auth-pending-container::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(122, 122, 122, 0.6);
      z-index: 1;
    }

    /* Modal de pending centrado */
    .pending-box {
      position: relative;
      z-index: 2;
      background: white;
      border-radius: 20px;
      box-shadow: 0 25px 50px rgba(29, 29, 29, 0.3);
      overflow: hidden;
      width: 100%;
      max-width: 450px;
      max-height: 90vh;
      animation: fadeIn 0.5s ease-out;
    }

    /* Header del formulario */
    .header {
      text-align: center;
      padding: 30px 30px 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      position: relative;
    }

    .header h2 {
      font-size: 1.8rem;
      font-weight: 600;
      margin: 0 0 8px 0;
      text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }

    .header .subtitle {
      font-size: 0.95rem;
      opacity: 0.9;
      margin: 0;
      font-weight: 300;
    }

    /* Contenido principal */
    .content {
      padding: 25px;
    }

    /* Saludo del usuario */
    .user-greeting {
      text-align: center;
      margin-bottom: 18px;
    }

    .avatar-container {
      width: 60px;
      height: 60px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 12px;
      box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
    }

    .avatar-container i {
      font-size: 1.6rem;
      color: white;
    }

    .user-greeting h3 {
      font-size: 1.2rem;
      color: #2d3748;
      margin: 0 0 6px 0;
      font-weight: 600;
    }

    .user-email {
      color: #718096;
      font-size: 0.9rem;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }

    .user-email i {
      color: #a0aec0;
    }

    /* Mensaje de estado */
    .status-message {
      display: flex;
      align-items: flex-start;
      gap: 15px;
      padding: 20px;
      background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
      border-radius: 12px;
      border-left: 4px solid #f39c12;
      margin-bottom: 20px;
    }

    .status-icon {
      flex-shrink: 0;
    }

    .status-icon i {
      font-size: 1.6rem;
      color: #e67e22;
    }

    .status-text h4 {
      color: #856404;
      margin: 0 0 8px 0;
      font-size: 1.1rem;
      font-weight: 600;
    }

    .status-text p {
      color: #856404;
      margin: 0;
      line-height: 1.5;
      font-size: 0.9rem;
    }

    /* Caja de instrucciones */
    .instructions-box {
      background: #e6f3ff;
      border-radius: 12px;
      margin-bottom: 25px;
      border-left: 4px solid #3182ce;
      overflow: hidden;
    }

    .instructions-header {
      background: rgba(49, 130, 206, 0.1);
      padding: 15px 20px;
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      color: #2c5282;
      border-bottom: 1px solid rgba(49, 130, 206, 0.2);
    }

    .instructions-header i {
      color: #3182ce;
      font-size: 1.1rem;
    }

    .instructions-content {
      padding: 15px 20px;
    }

    .instructions-content p {
      margin: 0;
      color: #2c5282;
      line-height: 1.5;
      font-size: 0.9rem;
    }

    /* Sección de contacto */
    .contact-section {
      background: #f7fafc;
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 20px;
      border: 1px solid #e2e8f0;
    }

    .contact-section h4 {
      color: #2d3748;
      margin: 0 0 15px 0;
      font-size: 1rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .contact-section h4 i {
      color: #4a5568;
    }

    .contact-items {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .contact-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px;
      background: white;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
    }

    .contact-item i {
      width: 20px;
      text-align: center;
      color: #667eea;
      font-size: 1rem;
    }

    .contact-details {
      display: flex;
      flex-direction: column;
      flex: 1;
    }

    .contact-label {
      font-size: 0.8rem;
      color: #718096;
      font-weight: 500;
    }

    .contact-value {
      font-size: 0.9rem;
      color: #2d3748;
      font-weight: 600;
    }

    /* Grupo de botones */
    .button-group {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-top: 25px;
    }

    .primary-button,
    .secondary-button {
      width: 100%;
      padding: 12px 15px;
      border: none;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
      position: relative;
      overflow: hidden;
      font-family: inherit;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }

    .primary-button {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }

    .primary-button:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
    }

    .secondary-button {
      background: #f7fafc;
      color: #4a5568;
      border: 2px solid #e2e8f0;
    }

    .secondary-button:hover {
      background: #e2e8f0;
      border-color: #cbd5e0;
      transform: translateY(-1px);
    }

    /* Animaciones */
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.7; }
      100% { opacity: 1; }
    }

    /* Estados de foco para accesibilidad */
    .primary-button:focus,
    .secondary-button:focus {
      outline: 2px solid #667eea;
      outline-offset: 2px;
    }

    /* Responsive */
    @media (max-width: 768px) {
      .auth-pending-container {
        padding: 15px;
      }

      .pending-box {
        max-width: 95%;
      }

      .header {
        padding: 25px 25px 18px;
      }

      .header h2 {
        font-size: 1.6rem;
      }

      .content {
        padding: 25px;
      }

      .contact-items {
        gap: 10px;
      }

      .contact-item {
        padding: 8px;
      }
    }

    @media (max-width: 480px) {
      .auth-pending-container {
        padding: 10px;
      }

      .header {
        padding: 20px 20px 15px;
      }

      .header h2 {
        font-size: 1.4rem;
      }

      .content {
        padding: 20px;
      }

      .status-message {
        flex-direction: column;
        text-align: center;
        gap: 10px;
      }

      .contact-item {
        flex-direction: column;
        text-align: center;
        gap: 8px;
      }

      .avatar-container {
        width: 60px;
        height: 60px;
      }

      .avatar-container i {
        font-size: 1.6rem;
      }
    }

    /* Mejoras visuales adicionales */
    .header::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    }
  `]
})
export class AuthPendingComponent implements OnInit {
  userName = '';
  userEmail = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      this.userName = params['name'] || 'Usuario';
      this.userEmail = params['email'] || '';
    });
  }

  contactAdmin(): void {
    // Abrir cliente de email con información pre-llenada
    const subject = encodeURIComponent('Solicitud de creación de cuenta - Polo 52');
    const body = encodeURIComponent(`
Hola,

Soy ${this.userName} y me he autenticado con Google usando el email ${this.userEmail}.

Mi email no está registrado en el sistema del Parque Industrial Polo 52.

Por favor, podrían crear mi cuenta en el sistema para poder acceder.

Gracias,
${this.userName}
    `);
    
    window.location.href = `mailto:admin&#64;polo52.com?subject=${subject}&body=${body}`;
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}