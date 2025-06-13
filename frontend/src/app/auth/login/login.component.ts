import { Component } from '@angular/core';
import { AuthenticationService } from '../auth.service';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common'; 
import { FormsModule } from '@angular/forms';   
import { finalize } from 'rxjs/operators';
import { RouterModule } from '@angular/router';


@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule,    RouterModule,   ], 
  templateUrl: './login.component.html', 
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  // Sólo username y password
  username = '';
  password = '';

  // flags de control
  usernameError = false;
  passwordError = false;
  loginMessage = '';
  loading = false;

  // visibilidad de contraseña
  showPassword = false;

  showResetPassword = false;
  resetEmail = '';
  resetMessage = '';
  resetError = '';
  resetToken = '';  // Agregado para mostrar el token



  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {}

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onLogin() {
  // Reset de errores
  this.usernameError = !this.username;
  this.passwordError = !this.password;
  this.loginMessage = '';

  if (this.usernameError || this.passwordError) {
    this.loginMessage = 'Por favor, completa todos los campos.';
    return;
  }

  this.loading = true;
  this.authService
    .login(this.username, this.password, /* keepLoggedIn */ false)
    .pipe(finalize(() => this.loading = false))
    .subscribe(success => {
      if (success) {
        const rol = this.authService.getUserRole();

        switch (rol) {
          case 'admin_polo':
            this.router.navigate(['/admin_polo']);
            break;
          case 'admin_empresa':
            this.router.navigate(['/admin_empresa']);
            break;
          case 'usuario':
            this.router.navigate(['/publico']);
            break;
          default:
            this.loginMessage = 'Rol no reconocido.';
            break;
        }
      } else {
        this.usernameError = true;
        this.passwordError = true;
        this.loginMessage = 'Usuario o contraseña inválidos.';
      }
    }, () => {
      this.loginMessage = 'Error de conexión. Intenta de nuevo más tarde.';
    });
}

requestPasswordReset() {
  this.resetMessage = '';
  this.resetError = '';

  this.authService.passwordResetRequest(this.resetEmail).subscribe({
    next: (res: any) => {
      if (res?.reset_token) {
        this.resetMessage = 'Se ha enviado un enlace para restablecer tu contraseña a tu correo. Por favor, revisa tu bandeja de entrada.';
        // Keep modal open to show message
      } else {
        this.resetError = 'Respuesta inesperada del servidor.';
      }
    },
    error: (err) => {
      console.error('Error en recuperación:', err);
      this.resetError = err?.error?.detail || 'Error al solicitar recuperación.';
    }
  });
}


}
