
// Crear app/auth/auth-error.component.ts
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-auth-error',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="auth-error-container">
      <div class="error-modal">
        <div class="error-icon">
          <i class="fas fa-exclamation-triangle"></i>
        </div>
        <h2>Error de Autenticación</h2>
        <p>Hubo un problema al autenticarte con Google.</p>
        <div class="error-detail" *ngIf="errorMessage">
          <strong>Detalle:</strong> {{ errorMessage }}
        </div>
        <div class="suggestions">
          <h4>Posibles soluciones:</h4>
          <ul>
            <li>Verifica tu conexión a internet</li>
            <li>Intenta cerrar y abrir el navegador</li>
            <li>Contacta al administrador si el problema persiste</li>
          </ul>
        </div>
        <button class="retry-button" (click)="goToLogin()">
          <i class="fas fa-redo"></i>
          Intentar de nuevo
        </button>
      </div>
    </div>
  `,
  styles: [`
    .auth-error-container {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
    }
    .error-modal {
      background: white;
      border-radius: 15px;
      padding: 2rem;
      text-align: center;
      max-width: 500px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    }
    .error-icon {
      font-size: 3rem;
      color: #e74c3c;
      margin-bottom: 1rem;
    }
    .error-detail {
      background: #ffeaea;
      padding: 1rem;
      border-radius: 8px;
      margin: 1rem 0;
      color: #c0392b;
    }
    .suggestions {
      text-align: left;
      background: #f8f9fa;
      padding: 1rem;
      border-radius: 8px;
      margin: 1rem 0;
    }
    .retry-button {
      background: #e74c3c;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 8px;
      cursor: pointer;
      margin-top: 1rem;
    }
  `]
})
export class AuthErrorComponent implements OnInit {
  errorMessage = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      this.errorMessage = params['message'] || 'Error desconocido';
    });
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}
