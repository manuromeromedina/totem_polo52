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
      <i *ngIf="!loading" class="fas fa-sign-out-alt logout-icon"></i>
      <i *ngIf="loading" class="fas fa-spinner logout-spinner"></i>
      <span class="logout-text">{{
        loading ? 'Saliendo...' : 'Cerrar sesión'
      }}</span>
    </button>

    <!-- Modal de confirmación -->
    <div class="modal-overlay" *ngIf="showModal" (click)="cancelLogout()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <div class="icon-container">
            <i class="fas fa-sign-out-alt"></i>
          </div>
          <h3>¿Cerrar sesión?</h3>
          <p>¿Estás seguro de que deseas cerrar tu sesión actual?</p>
        </div>

        <div class="modal-buttons">
          <button class="secondary-button" (click)="cancelLogout()">
            <i class="fas fa-times"></i>
            Cancelar
          </button>
          <button class="primary-button" (click)="confirmLogout()">
            <i class="fas fa-sign-out-alt"></i>
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
        gap: 10px;
        padding: 12px 20px;
        background: linear-gradient(
          135deg,
          #8b0000 0%,
          #b22222 50%,
          #dc143c 100%
        );
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        min-height: 44px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
          Oxygen, Ubuntu, Cantarell, sans-serif;
        position: relative;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(139, 0, 0, 0.2);
      }

      .logout-btn:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(139, 0, 0, 0.3);
      }

      .logout-btn:active:not(:disabled) {
        transform: translateY(0);
        box-shadow: 0 4px 12px rgba(139, 0, 0, 0.25);
      }

      .logout-btn:disabled {
        background: #cbd5e0;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
        color: #a0aec0;
      }

      .logout-icon {
        font-size: 16px;
        transition: transform 0.3s ease;
      }

      .logout-btn:hover:not(:disabled) .logout-icon {
        transform: translateX(2px);
      }

      .logout-spinner {
        font-size: 16px;
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
        font-size: 0.95rem;
        font-weight: 600;
        letter-spacing: 0.02em;
      }

      .logout-btn:focus {
        outline: 2px solid #b22222;
        outline-offset: 2px;
      }

      .logout-btn:focus:not(:focus-visible) {
        outline: none;
      }

      /* Modal Overlay */
      .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(122, 122, 122, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        animation: fadeIn 0.3s ease-out;
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
        }
        to {
          opacity: 1;
        }
      }

      /* Modal Content */
      .modal-content {
        background: white;
        border-radius: 20px;
        box-shadow: 0 25px 50px rgba(29, 29, 29, 0.3);
        overflow: hidden;
        width: 90%;
        max-width: 420px;
        animation: slideIn 0.3s ease-out;
      }

      @keyframes slideIn {
        from {
          opacity: 0;
          transform: translateY(20px) scale(0.95);
        }
        to {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }

      /* Modal Header */
      .modal-header {
        text-align: center;
        padding: 30px 30px 25px;
        background: #f8f9fa;
        border-bottom: 3px solid #e9ecef;
        color: #2d3748;
        position: relative;
      }

      .modal-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(
          90deg,
          transparent,
          rgba(255, 255, 255, 0.3),
          transparent
        );
      }

      .icon-container {
        margin-bottom: 15px;
      }

      .icon-container i {
        font-size: 2.5rem;
        color: #b22222;
        filter: drop-shadow(2px 2px 4px rgba(178, 34, 34, 0.2));
      }

      .modal-header h3 {
        margin: 0 0 10px 0;
        font-size: 1.5rem;
        font-weight: 600;
        color: #2d3748;
      }

      .modal-header p {
        margin: 0;
        font-size: 0.95rem;
        color: #718096;
        font-weight: 400;
        line-height: 1.4;
      }

      /* Modal Buttons */
      .modal-buttons {
        display: flex;
        gap: 15px;
        padding: 25px 30px;
        justify-content: center;
      }

      .primary-button,
      .secondary-button {
        flex: 1;
        padding: 12px 20px;
        border: none;
        border-radius: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        font-family: inherit;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        min-height: 44px;
      }

      .primary-button {
        background: linear-gradient(
          135deg,
          #8b0000 0%,
          #b22222 50%,
          #dc143c 100%
        );
        color: white;
        box-shadow: 0 2px 8px rgba(139, 0, 0, 0.2);
      }

      .primary-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(139, 0, 0, 0.3);
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
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      }

      .primary-button:active,
      .secondary-button:active {
        transform: translateY(0);
      }

      .primary-button:focus,
      .secondary-button:focus {
        outline: 2px solid #b22222;
        outline-offset: 2px;
      }

      /* Responsive Design */
      @media (max-width: 768px) {
        .logout-btn {
          padding: 10px 16px;
          font-size: 0.9rem;
          min-height: 40px;
          gap: 8px;
        }

        .logout-icon,
        .logout-spinner {
          font-size: 14px;
        }

        .logout-text {
          font-size: 0.9rem;
        }

        .modal-content {
          margin: 20px;
          max-width: calc(100% - 40px);
        }

        .modal-header {
          padding: 25px 25px 20px;
        }

        .modal-header h3 {
          font-size: 1.3rem;
        }

        .modal-header p {
          font-size: 0.9rem;
        }

        .icon-container i {
          font-size: 2rem;
        }

        .modal-buttons {
          padding: 20px 25px;
          gap: 12px;
        }

        .primary-button,
        .secondary-button {
          padding: 12px 16px;
          font-size: 0.9rem;
        }
      }

      @media (max-width: 480px) {
        .logout-text {
          display: none;
        }

        .logout-btn {
          padding: 10px 12px;
          min-width: 44px;
          justify-content: center;
          gap: 0;
        }

        .modal-buttons {
          flex-direction: column;
          gap: 10px;
        }

        .modal-header {
          padding: 20px 20px 15px;
        }

        .modal-buttons {
          padding: 15px 20px;
        }
      }

      /* Dark mode support */
      @media (prefers-color-scheme: dark) {
        .logout-btn:disabled {
          background: #495057;
          color: #6c757d;
        }
      }

      /* High contrast support */
      @media (prefers-contrast: high) {
        .logout-btn {
          border: 2px solid currentColor;
        }

        .primary-button,
        .secondary-button {
          border: 2px solid currentColor;
        }
      }

      /* Reduced motion support */
      @media (prefers-reduced-motion: reduce) {
        .logout-btn,
        .primary-button,
        .secondary-button,
        .modal-overlay,
        .modal-content,
        .logout-icon {
          transition: none;
          animation: none;
        }

        .logout-spinner {
          animation: none;
        }
      }
    `,
  ],
})
export class LogoutButtonComponent {
  loading = false;
  showModal = false;

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

  cancelLogout(): void {
    this.showModal = false;
  }

  confirmLogout(): void {
    this.showModal = false;
    this.logout();
  }
}
