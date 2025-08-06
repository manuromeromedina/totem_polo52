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
    }
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

    if (this.newPassword.length < 6) {
      this.error = 'La contraseña debe tener al menos 6 caracteres.';
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

        // Manejar diferentes tipos de errores
        if (err.error?.detail) {
          this.error = err.error.detail;
        } else if (err.error?.message) {
          this.error = err.error.message;
        } else if (err.message) {
          this.error = err.message;
        } else {
          this.error =
            'Error al actualizar la contraseña. El token puede haber expirado.';
        }

        // Si el token ha expirado, sugerir solicitar uno nuevo
        if (
          this.error.includes('expirado') ||
          this.error.includes('inválido')
        ) {
          this.error += ' Por favor, solicita un nuevo enlace de recuperación.';
        }
      },
    });
  }

  // Método para volver al login
  goToLogin() {
    this.router.navigate(['/login']);
  }
}
