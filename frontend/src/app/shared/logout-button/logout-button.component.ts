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
      (click)="showModal = true"
      [disabled]="loading"
      [attr.aria-label]="loading ? 'Cerrando sesión...' : 'Cerrar sesión'"
    >
      <span *ngIf="!loading" class="logout-icon">⏻</span>
      <span *ngIf="loading" class="logout-spinner"></span>
      <span class="logout-text">{{ loading ? 'Saliendo...' : 'Salir' }}</span>
    </button>

    <!-- Modal de confirmación -->
    <div class="modal-overlay" *ngIf="showModal" (click)="cancelLogout()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <h3>¿Cerrar sesión?</h3>
        <p>¿Estás seguro de que deseas cerrar tu sesión?</p>
        <div class="modal-buttons">
          <button class="btn-cancel" (click)="cancelLogout()">Cancelar</button>
          <button class="btn-confirm" (click)="confirmLogout()">
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  `,

  styles: [
    `
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
        0% {
          transform: rotate(0deg);
        }
        100% {
          transform: rotate(360deg);
        }
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

      .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
      }

      .modal-content {
        background: white;
        padding: 2rem;
        border-radius: 8px;
        max-width: 360px;
        width: 90%;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        text-align: center;
      }

      .modal-content h3 {
        margin-bottom: 0.5rem;
        font-size: 18px;
      }

      .modal-content p {
        margin-bottom: 1.5rem;
        font-size: 14px;
        color: #555;
      }

      .modal-buttons {
        display: flex;
        justify-content: space-around;
        gap: 1rem;
      }

      .btn-cancel,
      .btn-confirm {
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
      }

      .btn-cancel {
        background: #e0e0e0;
        color: #333;
      }

      .btn-confirm {
        background: #dc3545;
        color: white;
      }

      .btn-cancel:hover {
        background: #d5d5d5;
      }

      .btn-confirm:hover {
        background: #c82333;
      }
    `,
  ],
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
      },
    });
  }

  showModal = false;

  cancelLogout(): void {
    this.showModal = false;
  }

  confirmLogout(): void {
    this.showModal = false;
    this.logout(); // llama al método existente
  }
}
