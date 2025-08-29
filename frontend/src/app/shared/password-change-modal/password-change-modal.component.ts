// shared/password-change-modal/password-change-modal.component.ts
import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { NgForm, FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthenticationService } from '../../auth/auth.service';
import { Subject } from 'rxjs';
import { Router } from '@angular/router';

interface PasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface PasswordErrors {
  general?: string;
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
  passwordReused?: boolean;
  wrongCurrent?: boolean;
  passwordMismatch?: boolean;
}

@Component({
  selector: 'app-password-change-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './password-change-modal.component.html',
  styleUrls: ['./password-change-modal.component.css'],
})
export class PasswordChangeModalComponent implements OnInit {
  // Campos del formulario - INCLUYE contraseña actual
  currentPassword = '';
  newPassword = '';
  confirmPassword = '';
  showModal: boolean = false;

  // Estados
  message = '';
  error = '';
  loading = false;

  // Validaciones específicas
  currentPasswordError = '';
  passwordReused = false;
  validatingPassword = false;

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {}

  ngOnInit() {
    console.log(
      '🔐 Iniciando componente de cambio de contraseña para usuario logueado'
    );
  }

  openModal() {
    this.showModal = true;
  }

  closeModal() {
    this.showModal = false;
    this.clearForm();
  }

  // Validación en tiempo real de nueva contraseña
  onNewPasswordChange() {
    this.passwordReused = false;
    this.error = '';
    this.currentPasswordError = '';

    // Si la contraseña cumple requisitos básicos, validar contra historial
    if (
      this.newPassword &&
      this.isPasswordValid() &&
      this.newPassword.length >= 8
    ) {
      this.validateAgainstHistory();
    }
  }

  // Validar que la contraseña no haya sido utilizada antes
  validateAgainstHistory() {
    if (!this.newPassword || !this.currentPassword) return;

    this.validatingPassword = true;

    // Payload para validar (puedes implementar un endpoint específico)
    const validationPayload = {
      current_password: this.currentPassword,
      new_password: this.newPassword,
      confirm_password: this.newPassword,
      validate_only: true,
    };

    // Simular validación - implementa validatePasswordDirect en tu servicio
    setTimeout(() => {
      this.validatingPassword = false;
      // this.authService.validatePasswordDirect(validationPayload).subscribe(...)
    }, 800);
  }

  // MÉTODO PRINCIPAL - Cambio de contraseña para usuarios LOGUEADOS
  onChangePassword(form: NgForm) {
    console.log('🚀 Iniciando cambio de contraseña para usuario logueado...');

    // Limpiar mensajes y errores previos
    this.error = '';
    this.message = '';
    this.currentPasswordError = '';
    this.passwordReused = false;

    // Validaciones del formulario
    if (form.invalid) {
      this.error = 'Por favor, completa todos los campos correctamente.';
      return;
    }

    // VALIDACIÓN CRÍTICA: Contraseña actual es obligatoria
    if (!this.currentPassword || this.currentPassword.trim() === '') {
      this.currentPasswordError =
        'Debes ingresar tu contraseña actual para confirmar tu identidad.';
      this.error = 'La contraseña actual es obligatoria.';
      return;
    }

    // Validar que las contraseñas nuevas coincidan
    if (this.newPassword !== this.confirmPassword) {
      this.error = 'Las contraseñas nuevas no coinciden.';
      return;
    }

    // Validaciones de seguridad de la nueva contraseña
    const passwordValidation = this.validatePassword(this.newPassword);
    if (!passwordValidation.isValid) {
      this.error = passwordValidation.message;
      return;
    }

    // Verificar que no sea igual a la contraseña actual
    if (this.currentPassword === this.newPassword) {
      this.error = 'La nueva contraseña debe ser diferente a la actual.';
      return;
    }

    // Iniciar proceso de cambio con validación de contraseña actual
    this.loading = true;

    // DTO para usuarios logueados - CON current_password obligatorio
    const changeData = {
      current_password: this.currentPassword,
      new_password: this.newPassword,
      confirm_password: this.confirmPassword,
    };

    // Usar endpoint específico para usuarios logueados
    this.authService.changePasswordDirect(changeData).subscribe({
      next: (response) => {
        console.log('✅ Cambio de contraseña exitoso:', response);
        this.loading = false;

        if (response.success) {
          this.message =
            response.message ||
            'Contraseña actualizada correctamente. El cambio es efectivo inmediatamente.';

          // Limpiar campos por seguridad
          this.clearForm();

          // Opcional: Mostrar mensaje y redirigir después
          setTimeout(() => {
            this.goBack();
          }, 3000);
        } else {
          this.handleChangeError(response);
        }
      },
      error: (err) => {
        console.error('❌ Error en cambio de contraseña:', err);
        this.loading = false;
        this.handleChangeError(err.error || err);
      },
    });
  }

  // Manejar errores específicos del cambio de contraseña
  handleChangeError(errorResponse: any) {
    // Error de contraseña actual incorrecta
    if (
      errorResponse.wrong_current ||
      errorResponse.error?.includes('contraseña actual') ||
      errorResponse.detail?.includes('incorrecta')
    ) {
      this.currentPasswordError =
        'La contraseña actual es incorrecta. Verifica e intenta nuevamente.';
      this.error = 'Contraseña actual incorrecta.';
    }
    // Error de contraseña reutilizada
    else if (
      errorResponse.password_reused ||
      errorResponse.error?.includes('utilizado anteriormente')
    ) {
      this.passwordReused = true;
      this.error =
        'No puedes usar una contraseña que ya hayas utilizado anteriormente. Elige una diferente.';
    }
    // Error de contraseñas que no coinciden
    else if (
      errorResponse.passwords_mismatch ||
      errorResponse.error?.includes('no coinciden')
    ) {
      this.error =
        'Las contraseñas no coinciden. Verifica e intenta nuevamente.';
    }
    // Errores generales
    else if (errorResponse.detail) {
      this.error = errorResponse.detail;
    } else if (errorResponse.error) {
      this.error = errorResponse.error;
    } else {
      this.error = 'Error al cambiar la contraseña. Inténtalo nuevamente.';
    }
  }

  // Limpiar formulario por seguridad
  clearForm() {
    this.currentPassword = '';
    this.newPassword = '';
    this.confirmPassword = '';
    this.currentPasswordError = '';
    this.passwordReused = false;
  }

  // Navegación
  goBack() {
    // Redirigir al dashboard o página anterior
    this.router.navigate(['/dashboard']); // Cambia por tu ruta
  }

  // Validaciones de contraseña
  validatePassword(password: string): { isValid: boolean; message: string } {
    if (!password) {
      return { isValid: false, message: 'La contraseña es requerida.' };
    }

    if (password.length < 8) {
      return {
        isValid: false,
        message: 'La contraseña debe tener al menos 8 caracteres.',
      };
    }

    if (!/[A-Z]/.test(password)) {
      return {
        isValid: false,
        message: 'La contraseña debe tener al menos una letra mayúscula.',
      };
    }

    if (!/[0-9]/.test(password)) {
      return {
        isValid: false,
        message: 'La contraseña debe tener al menos un número.',
      };
    }

    return { isValid: true, message: '' };
  }

  isPasswordValid(): boolean {
    return this.validatePassword(this.newPassword).isValid;
  }

  doPasswordsMatch(): boolean {
    return (
      this.newPassword === this.confirmPassword &&
      this.confirmPassword.length > 0
    );
  }

  getPasswordRequirements() {
    const password = this.newPassword;
    return {
      minLength: password.length >= 8,
      hasUppercase: /[A-Z]/.test(password),
      hasNumber: /[0-9]/.test(password),
      notReused: !this.passwordReused,
    };
  }

  // Validación completa del formulario para usuarios logueados
  isFormValid(): boolean {
    return (
      // VALIDACIÓN CLAVE: Contraseña actual obligatoria
      this.currentPassword.trim() !== '' &&
      // Validaciones estándar
      this.isPasswordValid() &&
      this.doPasswordsMatch() &&
      !this.passwordReused &&
      !this.validatingPassword &&
      // Verificar que no sea igual a la actual
      this.currentPassword !== this.newPassword
    );
  }
}
