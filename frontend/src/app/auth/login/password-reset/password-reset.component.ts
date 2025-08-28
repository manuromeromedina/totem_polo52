import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthenticationService } from '../../auth.service';
import { NgForm, FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './password-reset.component.html',
  styleUrls: ['./password-reset.component.css'],
})
export class ResetPasswordComponent implements OnInit {
  token = '';
  currentPassword = '';
  newPassword = '';
  confirmPassword = '';
  message = '';
  error = '';
  loading = false;
  tokenExpired = false;
  tokenUsed = false;

  // Nuevas propiedades para validación
  userEmail?: string;
  userName?: string;

  passwordReused = false;
  requiresCurrentPassword = true; // El backend requiere contraseña actual
  validatingPassword = false; // Para mostrar spinner durante validación

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private router: Router
  ) {}

  ngOnInit() {
    this.token = this.route.snapshot.queryParamMap.get('token') || '';

    console.log(
      '🔍 Token recibido:',
      this.token ? this.token.substring(0, 20) + '...' : 'NO TOKEN'
    );

    if (!this.token) {
      this.error = 'Token no válido o ausente. Por favor, verifica el enlace.';
    } else {
      this.verifyTokenValidity();
    }
  }

  // Verificar validez del token y obtener información del usuario
  verifyTokenValidity() {
    this.loading = true;

    this.authService.verifyResetToken(this.token).subscribe({
      next: (response) => {
        this.loading = false;
        if (response.valid) {
          console.log('Token válido');
          this.userEmail = response.email || '';
          this.userName = response.user_name || '';
        } else {
          this.handleTokenError(response);
        }
      },
      error: (err) => {
        this.loading = false;
        console.error('❌ Token inválido:', err);
        this.error = 'Error al verificar el enlace de recuperación.';
      },
    });
  }

  // Manejar errores de token (expirado, usado, etc.)
  handleTokenError(response: any) {
    if (response.expired) {
      this.tokenExpired = true;
      this.error =
        'Este enlace de recuperación ha expirado. Por favor, solicita uno nuevo.';
    } else if (response.used) {
      this.tokenUsed = true;
      this.error =
        'Este enlace de recuperación ya fue utilizado. Por favor, solicita uno nuevo.';
    } else {
      this.error = response.error || 'Enlace de recuperación inválido.';
    }
  }

  // Validación en tiempo real de nueva contraseña
  onNewPasswordChange() {
    this.passwordReused = false;
    this.error = '';

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
    if (!this.newPassword || !this.token) return;

    this.validatingPassword = true;

    // Crear un payload para validación (sin cambiar la contraseña aún)
    const validationPayload = {
      token: this.token,
      current_password: this.currentPassword,
      new_password: this.newPassword,
      confirm_password: this.newPassword, // Para esta validación usamos la misma
      validate_only: true, // Flag para indicar que solo queremos validar
    };

    // Llamar al endpoint de validación (necesitarás agregarlo al servicio)
    this.authService.validatePasswordReset(validationPayload).subscribe({
      next: (response) => {
        this.validatingPassword = false;
        if (response.password_reused) {
          this.passwordReused = true;
          this.error =
            'No puedes usar una contraseña que ya hayas utilizado anteriormente.';
        } else {
          this.passwordReused = false;
          this.error = '';
        }
      },
      error: (err) => {
        this.validatingPassword = false;
        // No mostrar error aquí para no confundir al usuario
        // Solo marcar como no reutilizada si hay error de validación
        this.passwordReused = false;
      },
    });
  }

  onResetPassword(form: NgForm) {
    console.log('🚀 Iniciando reset password con validación completa...');

    // Limpiar mensajes previos
    this.error = '';
    this.message = '';
    this.passwordReused = false;

    // Validaciones del formulario
    if (form.invalid) {
      this.error = 'Por favor, completa todos los campos correctamente.';
      return;
    }

    if (!this.currentPassword.trim()) {
      this.error =
        'Debes ingresar tu contraseña actual para confirmar el cambio.';
      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.error = 'Las contraseñas no coinciden.';
      return;
    }

    // Validaciones de contraseña
    const passwordValidation = this.validatePassword(this.newPassword);
    if (!passwordValidation.isValid) {
      this.error = passwordValidation.message;
      return;
    }

    if (!this.token) {
      this.error =
        'Token no válido. Por favor, solicita un nuevo enlace de reset.';
      return;
    }

    // Iniciar proceso de reset con validación completa
    this.loading = true;

    const resetData = {
      token: this.token,
      current_password: this.currentPassword,
      new_password: this.newPassword,
      confirm_password: this.confirmPassword,
    };

    this.authService.resetPasswordSecure(resetData).subscribe({
      next: (response) => {
        console.log('✅ Reset exitoso:', response);
        this.loading = false;

        if (response.success) {
          this.message =
            response.message ||
            'Contraseña actualizada con éxito. Redirigiendo al login...';

          // Limpiar formulario por seguridad
          this.currentPassword = '';
          this.newPassword = '';
          this.confirmPassword = '';

          // Redirigir después de 3 segundos
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 3000);
        } else {
          this.handleResetError(response);
        }
      },
      error: (err) => {
        console.error('❌ Error en reset:', err);
        this.loading = false;
        this.handleResetError(err.error || err);
      },
    });
  }

  // Manejar errores específicos del reset
  handleResetError(errorResponse: any) {
    if (errorResponse.expired || errorResponse.error?.includes('expirado')) {
      this.tokenExpired = true;
      this.error =
        'El enlace de recuperación ha expirado. Por favor, solicita uno nuevo.';
    } else if (
      errorResponse.used ||
      errorResponse.error?.includes('utilizado')
    ) {
      this.tokenUsed = true;
      this.error =
        'Este enlace de recuperación ya fue utilizado. Por favor, solicita uno nuevo.';
    } else if (
      errorResponse.password_reused ||
      errorResponse.error?.includes('utilizado anteriormente')
    ) {
      this.passwordReused = true;
      this.error =
        'No puedes usar una contraseña que ya hayas utilizado anteriormente. Elige una diferente.';
    } else if (
      errorResponse.wrong_current ||
      errorResponse.error?.includes('contraseña actual')
    ) {
      this.error =
        'La contraseña actual es incorrecta. Verifica e intenta nuevamente.';
    } else if (
      errorResponse.passwords_mismatch ||
      errorResponse.error?.includes('no coinciden')
    ) {
      this.error =
        'Las contraseñas no coinciden. Verifica e intenta nuevamente.';
    } else if (errorResponse.detail) {
      this.error = errorResponse.detail;
    } else if (errorResponse.error) {
      this.error = errorResponse.error;
    } else {
      this.error = 'Error al actualizar la contraseña. Inténtalo nuevamente.';
    }
  }

  // Métodos de utilidad (sin cambios)
  requestNewLink() {
    this.router.navigate(['/forgot-password']);
  }

  goToLogin() {
    this.router.navigate(['/login']);
  }

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

  // Nuevo método para obtener el estado de validación completo
  isFormValid(): boolean {
    return (
      this.currentPassword.trim() !== '' &&
      this.isPasswordValid() &&
      this.doPasswordsMatch() &&
      !this.passwordReused &&
      !this.validatingPassword
    );
  }
}
