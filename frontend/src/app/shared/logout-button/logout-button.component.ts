import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthenticationService } from '../../auth/auth.service';

@Component({
  selector: 'app-logout-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button 
      class="logout-btn" 
      (click)="logout()" 
      [disabled]="loading"
      [attr.aria-label]="loading ? 'Cerrando sesión...' : 'Cerrar sesión'">
      <span *ngIf="!loading" class="logout-icon">⏻</span>
      <span *ngIf="loading" class="logout-spinner"></span>
      <span class="logout-text">{{ loading ? 'Saliendo...' : 'Salir' }}</span>
    </button>
  `,
  styles: [`
    .logout-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 20px;
      background: #dc3545;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      min-height: 40px;
      font-family: inherit;
    }

    .logout-btn:hover:not(:disabled) {
      background: #c82333;
      transform: translateY(-1px);
      box-shadow: 0 2px 4px rgba(220, 53, 69, 0.2);
    }

    .logout-btn:disabled {
      background: #6c757d;
      cursor: not-allowed;
      transform: none;
    }

    .logout-icon {
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .logout-spinner {
      width: 16px;
      height: 16px;
      border: 2px solid transparent;
      border-top: 2px solid currentColor;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .logout-text {
      font-size: 14px;
      font-weight: 500;
    }

    .logout-btn:focus {
      outline: 2px solid #dc3545;
      outline-offset: 2px;
    }

    .logout-btn:focus:not(:focus-visible) {
      outline: none;
    }

    /* Responsive */
    @media (max-width: 768px) {
      .logout-btn {
        padding: 8px 16px;
        font-size: 13px;
        min-height: 36px;
      }
      
      .logout-text {
        font-size: 13px;
      }
      
      .logout-icon {
        font-size: 14px;
      }
    }

    @media (max-width: 480px) {
      .logout-text {
        display: none;
      }
      
      .logout-btn {
        padding: 8px 12px;
        min-width: 40px;
        justify-content: center;
      }
    }

    /* Dark mode */
    @media (prefers-color-scheme: dark) {
      .logout-btn:disabled {
        background: #495057;
      }
    }

    /* High contrast */
    @media (prefers-contrast: high) {
      .logout-btn {
        border: 2px solid currentColor;
      }
    }
  `]
})
export class LogoutButtonComponent {
  loading = false;

  constructor(private authService: AuthenticationService) {}

  logout(): void {
    if (this.loading) return;
    
    this.loading = true;
    
    this.authService.logout().subscribe({
      next: () => {
        this.loading = false;
      },
      error: (error) => {
        console.error('Error during logout:', error);
        this.loading = false;
        // El servicio ya maneja la limpieza y redirección en caso de error
      }
    });
  }
}