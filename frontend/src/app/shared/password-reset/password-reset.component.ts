import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthenticationService } from '../../auth/auth.service';
import { NgForm, FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-reset-password-public',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './password-reset.component.html',
  styleUrls: ['./password-reset.component.css'],
})
export class ResetPasswordPublicComponent implements OnInit {
  token = '';
  // SIN currentPassword - usuarios no logueados NO necesitan contraseña actual
  newPassword = '';
  confirmPassword = '';
  message = '';
  error = '';
  loading = false;
  tokenExpired = false;
  tokenUsed = false;

  // Propiedades para validación
  userEmail?: string;
  userName?: string;
  passwordReused = false;
  validatingPassword = false;

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private router: Router
  ) {}

  ngOnInit() {
    this.token = this.route.snapshot.queryParamMap.get('token') || '';

    console.log(
      '🔍 Token de recuperación recibido:',
      this.token ? this.token.substring(0, 20) + '...' : 'NO TOKEN'
    );

    if (!this.token) {
      this.error =
        'Token no válido o ausente. Por favor, verifica el enlace de recuperación.';
    } else {
      this.verifyTokenValidity();
    }
  }

  // Verificar validez del token y obtener información del usuario
  verifyTokenValidity() {
    this.loading = true;
    this.error = '';

    this.authService.verifyResetToken(this.token).subscribe({
      next: (response) => {
        this.loading = false;
        if (response.valid) {
          console.log('✅ Token de recuperación válido');
          this.userEmail = response.email || '';
          this.userName = response.user_name || '';
        } else {
          this.handleTokenError(response);
        }
      },
      error: (err) => {
        this.loading = false;
        console.error('❌ Error verificando token:', err);
        this.error = 'Error al verificar el enlace de recuperación.';
      },
    });
  }

  // Manejar errores de token (expirado, usado, etc.)
  handleTokenError(response: any) {
    if (response.expired) {
      this.tokenExpired = true;
      this.error =
        'Este enlace de recuperación ha expirado. Los enlaces expiran después de 1 hora por seguridad.';
    } else if (response.used) {
      this.tokenUsed = true;
      this.error =
        'Este enlace de recuperación ya fue utilizado. Solo se puede usar una vez por seguridad.';
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

    // Para usuarios no logueados usamos un endpoint diferente de validación
    const validationPayload = {
      token: this.token,
      new_password: this.newPassword,
      confirm_password: this.newPassword,
      validate_only: true,
    };

    // Simulamos la validación con un timeout (puedes implementar un endpoint específico)
    setTimeout(() => {
      this.validatingPassword = false;
      // Aquí puedes hacer una llamada real al backend para validar
      // this.authService.validatePasswordResetPublic(validationPayload).subscribe(...)
    }, 1000);
  }

  // MÉTODO PRINCIPAL - Reset para usuarios NO logueados
  onResetPassword(form: NgForm) {
    console.log('🚀 Iniciando reset password para usuario NO logueado...');

    // Limpiar mensajes previos
    this.error = '';
    this.message = '';
    this.passwordReused = false;

    // Validaciones del formulario
    if (form.invalid) {
      this.error = 'Por favor, completa todos los campos correctamente.';
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

    // Iniciar proceso de reset para usuarios NO logueados
    this.loading = true;

    // DTO para usuarios NO logueados - SIN current_password
    const resetData = {
      token: this.token,
      new_password: this.newPassword,
      confirm_password: this.confirmPassword,
    };

    // Usar endpoint específico para usuarios NO logueados
    this.authService.resetPasswordSecure(resetData).subscribe({
      next: (response) => {
        console.log('✅ Reset exitoso para usuario no logueado:', response);
        this.loading = false;

        if (response.success) {
          this.message =
            response.message ||
            'Contraseña restablecida con éxito. Ya puedes iniciar sesión con tu nueva contraseña. Redirigiendo al login...';

          // Limpiar formulario por seguridad
          this.newPassword = '';
          this.confirmPassword = '';

          // Redirigir después de 4 segundos (más tiempo para leer el mensaje)
          setTimeout(() => {
            this.router.navigate(['/login'], {
              queryParams: { message: 'password-reset-success' },
            });
          }, 4000);
        } else {
          this.handleResetError(response);
        }
      },
      error: (err) => {
        console.error('❌ Error en reset para usuario no logueado:', err);
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
      this.error = 'Error al restablecer la contraseña. Inténtalo nuevamente.';
    }
  }

  // Navegación
  requestNewLink() {
    this.router.navigate(['/forgot-password']);
  }

  goToLogin() {
    this.router.navigate(['/login']);
  }

  // Validaciones de contraseña (sin cambios)
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

  // Validación completa del formulario para usuarios NO logueados
  isFormValid(): boolean {
    return (
      // SIN validación de currentPassword
      this.isPasswordValid() &&
      this.doPasswordsMatch() &&
      !this.passwordReused &&
      !this.validatingPassword
    );
  }
}
