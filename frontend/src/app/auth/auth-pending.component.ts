// =============================================================================
// 4. CREAR COMPONENTE PARA USUARIO PENDIENTE
// =============================================================================

// Crear app/auth/auth-pending.component.ts
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-auth-pending',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="auth-pending-container">
      <div class="pending-modal">
        <div class="pending-icon">
          <i class="fas fa-clock"></i>
        </div>
        <h2>Cuenta Pendiente de Aprobación</h2>
        <div class="user-info">
          <p><strong>Hola {{ userName }}</strong></p>
          <p>Tu email <strong>{{ userEmail }}</strong> no está registrado en el sistema.</p>
        </div>
        <div class="info-box">
          <i class="fas fa-info-circle"></i>
          <p>Por favor contacta al administrador del parque industrial para que registre tu cuenta.</p>
        </div>
        <div class="contact-info">
          <h4>Información de contacto:</h4>
          <p><i class="fas fa-envelope"></i> adminpolo52.com</p>
          <p><i class="fas fa-phone"></i> +54 351 XXX-XXXX</p>
        </div>
        <button class="back-button" (click)="goToLogin()">
          <i class="fas fa-arrow-left"></i>
          Volver al Login
        </button>
      </div>
    </div>
  `,
  styles: [`
    .auth-pending-container {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
    }
    .pending-modal {
      background: white;
      border-radius: 15px;
      padding: 2rem;
      text-align: center;
      max-width: 500px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    }
    .pending-icon {
      font-size: 3rem;
      color: #f39c12;
      margin-bottom: 1rem;
    }
    .info-box {
      background: #e8f4fd;
      padding: 1rem;
      border-radius: 8px;
      margin: 1rem 0;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .info-box i {
      color: #3498db;
    }
    .contact-info {
      background: #f8f9fa;
      padding: 1rem;
      border-radius: 8px;
      margin: 1rem 0;
    }
    .back-button {
      background: #6c5ce7;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 8px;
      cursor: pointer;
      margin-top: 1rem;
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

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}