import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

// Interfaces para manejo de errores
export interface FormError {
  field: string;
  message: string;
  type: 'required' | 'invalid' | 'duplicate' | 'server' | 'validation';
}

@Component({
  selector: 'app-password-change-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <!-- Password Change Modal -->
    <div class="modal-overlay" *ngIf="isVisible" (click)="onClose()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>{{ title || '¿Cambiar contraseña?' }}</h3>
          <p>
            {{
              subtitle ||
                '¿Estás seguro de que deseas solicitar un enlace de cambio de contraseña?'
            }}
          </p>
        </div>

        <!-- Error Display -->
        <div *ngIf="errors && errors.length > 0" class="error-container">
          <div class="error-message" *ngFor="let error of errors">
            {{ error.message }}
          </div>
        </div>

        <!-- Information section -->
        <div class="info-section">
          <div class="info-item">
            <i class="fas fa-envelope"></i>
            <span class="info-text"
              >Se enviará un enlace seguro a tu email registrado</span
            >
          </div>
          <div class="info-item">
            <i class="fas fa-search"></i>
            <span class="info-text"
              >Revisa tu bandeja de entrada y carpeta de spam</span
            >
          </div>
          <div class="info-item">
            <i class="fas fa-clock"></i>
            <span class="info-text">El enlace expira en 24 horas</span>
          </div>
        </div>

        <div class="modal-buttons">
          <button
            class="secondary-button"
            (click)="onClose()"
            [disabled]="loading"
          >
            {{ cancelText || 'Cancelar' }}
          </button>
          <button
            class="primary-button"
            (click)="onConfirm()"
            [disabled]="loading"
          >
            <i *ngIf="loading" class="fas fa-spinner fa-spin"></i>
            {{
              loading
                ? loadingText || 'Enviando...'
                : confirmText || 'Enviar Email'
            }}
          </button>
        </div>
      </div>
    </div>
  `,

  styles: [
    `
      /* Modal Overlay */
      .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(99, 99, 99, 0.6);
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
        border-radius: 10px;
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
        background: #f0f0f0ff;
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

      .modal-header h3 {
        margin: 0 0 10px 0;
        font-size: 1.5rem;
        font-weight: 600;
        color: #1b212bff;
      }

      .modal-header p {
        margin: 0;
        font-size: 0.95rem;
        color: #718096;
        font-weight: 400;
        line-height: 1.4;
      }

      /* Error Display */
      .error-container {
        padding: 15px 30px;
        background: #fef2f2;
        border-bottom: 1px solid #fecaca;
      }

      .error-message {
        color: #dc2626;
        font-size: 0.9rem;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .error-message:last-child {
        margin-bottom: 0;
      }

      /* Info Section */
      .info-section {
        padding: 15px 30px;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
      }

      .info-item {
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .info-item:last-child {
        margin-bottom: 0;
      }

      .info-item i {
        color: #b22222;
        font-size: 14px;
        width: 16px;
        text-align: center;
        flex-shrink: 0;
      }

      .info-text {
        color: #4a5568;
        font-size: 0.9rem;
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

      .primary-button:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(139, 0, 0, 0.3);
      }

      .secondary-button {
        background: #f7fafc;
        color: #4a5568;
        border: 2px solid #e2e8f0;
      }

      .secondary-button:hover:not(:disabled) {
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

      .primary-button:disabled,
      .secondary-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
      }

      /* Loading spinner */
      .fa-spin {
        animation: fa-spin 1s infinite linear;
      }

      @keyframes fa-spin {
        from {
          transform: rotate(0deg);
        }
        to {
          transform: rotate(360deg);
        }
      }

      /* Responsive Design */
      @media (max-width: 768px) {
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

      /* High contrast support */
      @media (prefers-contrast: high) {
        .primary-button,
        .secondary-button {
          border: 2px solid currentColor;
        }
      }

      /* Reduced motion support */
      @media (prefers-reduced-motion: reduce) {
        .primary-button,
        .secondary-button,
        .modal-overlay,
        .modal-content {
          transition: none;
          animation: none;
        }

        .fa-spin {
          animation: none;
        }
      }
    `,
  ],
})
export class PasswordChangeModalComponent {
  // Inputs para configurar el modal
  @Input() isVisible: boolean = false;
  @Input() loading: boolean = false;
  @Input() errors: FormError[] = [];

  // Textos personalizables
  @Input() title: string = '¿Cambiar contraseña?';
  @Input() subtitle: string =
    '¿Estás seguro de que deseas solicitar un enlace de cambio de contraseña?';
  @Input() cancelText: string = 'Cancelar';
  @Input() confirmText: string = 'Enviar Email';
  @Input() loadingText: string = 'Enviando...';

  // Outputs para eventos
  @Output() close = new EventEmitter<void>();
  @Output() confirm = new EventEmitter<void>();

  onClose(): void {
    this.close.emit();
  }

  onConfirm(): void {
    this.confirm.emit();
  }
}
