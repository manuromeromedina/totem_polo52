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
  newPassword = '';
  confirmPassword = '';
  message = '';
  error = '';
  loading = false;
  tokenExpired = false;
  tokenUsed = false; // Nueva propiedad para tokens ya usados

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private router: Router
  ) {}

  ngOnInit() {
    // Obtener el token de la URL
    this.token = this.route.snapshot.queryParamMap.get('token') || '';

    console.log(
      '🔍 Token recibido:',
      this.token ? this.token.substring(0, 20) + '...' : 'NO TOKEN'
    );

    if (!this.token) {
      this.error = 'Token no válido o ausente. Por favor, verifica el enlace.';
    } else {
      // Verificar si el token ya expiró al cargar la página
      this.verifyTokenValidity();
    }
  }

  // Método para verificar si el token es válido antes de mostrar el formulario
  verifyTokenValidity() {
    this.loading = true;

    this.authService.verifyResetToken(this.token).subscribe({
      next: (response) => {
        this.loading = false;
        if (response.valid) {
          console.log('✅ Token válido');
        } else {
          // Manejar diferentes tipos de errores
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
      },
      error: (err) => {
        this.loading = false;
        console.error('❌ Token inválido:', err);
        this.error = 'Error al verificar el enlace de recuperación.';
      },
    });
  }

  onResetPassword(form: NgForm) {
    console.log('🚀 Iniciando reset password...');

    // Limpiar mensajes previos
    this.error = '';
    this.message = '';

    // Validaciones del formulario
    if (form.invalid) {
      this.error = 'Por favor, completa todos los campos correctamente.';
      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.error = 'Las contraseñas no coinciden.';
      return;
    }

    // Validaciones de contraseña mejoradas
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

    // Iniciar proceso de reset
    this.loading = true;

    this.authService.resetPassword(this.token, this.newPassword).subscribe({
      next: (response) => {
        console.log('✅ Reset exitoso:', response);
        this.loading = false;
        this.message =
          response.message ||
          'Contraseña actualizada con éxito. Redirigiendo al login...';

        // Redirigir después de 3 segundos
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 3000);
      },
      error: (err) => {
        console.error('❌ Error en reset:', err);
        this.loading = false;

        // Manejar específicamente tokens expirados y usados
        if (err.error?.expired || err.error?.error?.includes('expirado')) {
          this.tokenExpired = true;
          this.error =
            'El enlace de recuperación ha expirado. Por favor, solicita uno nuevo.';
        } else if (err.error?.used || err.error?.error?.includes('utilizado')) {
          this.tokenUsed = true;
          this.error =
            'Este enlace de recuperación ya fue utilizado. Por favor, solicita uno nuevo.';
        }
        // Manejar otros tipos de errores
        else if (err.error?.detail) {
          this.error = err.error.detail;
        } else if (err.error?.message) {
          this.error = err.error.message;
        } else if (err.error?.error) {
          this.error = err.error.error;
        } else if (err.message) {
          this.error = err.message;
        } else {
          this.error =
            'Error al actualizar la contraseña. Inténtalo nuevamente.';
        }
      },
    });
  }

  // Método para solicitar un nuevo enlace
  requestNewLink() {
    this.router.navigate(['/forgot-password']);
  }

  // Método para volver al login
  goToLogin() {
    this.router.navigate(['/login']);
  }

  // Validación de contraseña con reglas específicas
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

  // Verificar si la contraseña cumple con los requisitos
  isPasswordValid(): boolean {
    return this.validatePassword(this.newPassword).isValid;
  }

  // Verificar si las contraseñas coinciden
  doPasswordsMatch(): boolean {
    return (
      this.newPassword === this.confirmPassword &&
      this.confirmPassword.length > 0
    );
  }

  // Obtener requisitos de contraseña para mostrar en el UI
  getPasswordRequirements() {
    const password = this.newPassword;
    return {
      minLength: password.length >= 8,
      hasUppercase: /[A-Z]/.test(password),
      hasNumber: /[0-9]/.test(password),
    };
  }
}
