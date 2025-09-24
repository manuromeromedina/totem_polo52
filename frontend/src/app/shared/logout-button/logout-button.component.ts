import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthenticationService } from '../../auth/auth.service';

@Component({
  selector: 'app-logout-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <!-- Botón igual al de "Nuevo vehículo / Editar datos" -->
    <button
      class="btn primary"
      type="button"
      (click)="showModal = true"
      [disabled]="loading"
    >
      <span class="material-symbols-outlined">
        {{ loading ? 'hourglass_top' : 'logout' }}
      </span>
      <span>{{ loading ? 'Saliendo…' : 'Cerrar sesión' }}</span>
    </button>

    <!-- Modal de confirmación con el mismo look & feel -->
    <div class="overlay" *ngIf="showModal" (click)="cancelLogout()">
      <div class="modal modal--sm" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>¿Cerrar sesión?</h3>
          <button
            type="button"
            class="icon-btn"
            (click)="cancelLogout()"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        <div class="modal-body">
          <p>¿Estás seguro de que querés cerrar tu sesión actual?</p>
        </div>

        <div class="modal-actions">
          <button class="btn ghost" type="button" (click)="cancelLogout()">
            <span class="material-symbols-outlined">close</span>
            Cancelar
          </button>
          <button
            class="btn danger"
            type="button"
            (click)="confirmLogout()"
            [disabled]="loading"
          >
            <span class="material-symbols-outlined">logout</span>
            Salir
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      /* ====== Botones (mismo diseño que admin empresas) ====== */
      .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-weight: 500;
        cursor: pointer;
        border: none;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        font-family: 'Inter', sans-serif;
      }
      .btn .material-symbols-outlined {
        font-size: 20px;
        line-height: 1;
      }

      .btn.primary {
        background: #a20000;
        color: #fff;
      }
      .btn.primary:hover {
        background: #870000;
      }
      .btn.primary:disabled {
        opacity: 0.7;
        cursor: default;
      }

      .btn.ghost {
        background: #f5f5f5;
        color: #444;
      }
      .btn.ghost:hover {
        background: #eaeaea;
      }

      .btn.danger {
        color: #a20000;
        background: #fff0f0;
        border: 1px solid #f5b5b5;
      }
      .btn.danger:hover {
        background: #ffe8e8;
      }

      .btn:focus-visible {
        outline: 2px solid rgba(162, 0, 0, 0.25);
        outline-offset: 2px;
      }

      /* ====== Overlay & Modal (idéntico a los formularios) ====== */
      .overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        animation: fadeIn 0.2s ease;
      }
      .modal {
        background: #fff;
        border-radius: 12px;
        padding: 1.5rem;
        width: min(820px, 95vw);
        max-height: 90vh;
        overflow: auto;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        animation: slideIn 0.2s ease;
      }
      .modal--sm {
        width: min(360px, 90vw);
      }

      .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      }
      .modal-header h3 {
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0;
        font-family: 'Inter', sans-serif;
      }

      .icon-btn {
        border: none;
        background: transparent;
        font-size: 1.2rem;
        cursor: pointer;
        transition: transform 0.2s ease;
      }
      .icon-btn:hover {
        transform: scale(1.08);
      }

      .modal-body p {
        margin: 0 0 0.5rem;
        color: #333;
        font-family: 'Inter', sans-serif;
      }

      .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.8rem;
        margin-top: 1rem;
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
        }
        to {
          opacity: 1;
        }
      }
      @keyframes slideIn {
        from {
          transform: translateY(-10px);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }
    `,
  ],
})
export class LogoutButtonComponent {
  loading = false;
  showModal = false;

  constructor(private authService: AuthenticationService) {}

  private doLogout(): void {
    if (this.loading) return;
    this.loading = true;
    this.authService.logout().subscribe({
      next: () => {
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  cancelLogout(): void {
    this.showModal = false;
  }
  confirmLogout(): void {
    this.showModal = false;
    this.doLogout();
  }
}
