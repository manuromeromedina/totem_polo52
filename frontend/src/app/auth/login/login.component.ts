import { Component, OnInit } from '@angular/core';
import { AuthenticationService } from '../auth.service';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs/operators';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit {
  // Datos del formulario
  username = '';
  password = '';
  keepLoggedIn = false; // Checkbox para mantener sesión

  // Estados de validación
  usernameError = false;
  passwordError = false;
  usernameErrorMessage = '';
  passwordErrorMessage = '';

  // Estados de UI
  loginMessage = '';
  successMessage = '';
  loading = false;
  showPassword = false;

  // Recuperación de contraseña
  showResetPassword = false;
  resetEmail = '';
  resetMessage = '';
  resetError = '';
  resetLoading = false;

  // Estados de formulario
  loginAttempts = 0;
  maxAttempts = 5;
  isBlocked = false;
  blockTimeRemaining = 0;

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Verificar si ya está logueado
    if (this.authService.isLoggedIn()) {
      this.redirectByRole();
    }
    
    // Verificar si hay bloqueo temporal
    this.checkBlockStatus();
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  validateUsername(): void {
    this.usernameError = false;
    this.usernameErrorMessage = '';

    if (!this.username.trim()) {
      this.usernameError = true;
      this.usernameErrorMessage = 'El usuario o email es requerido';
      return;
    }

    if (this.username.includes('@')) {
      // Validar email
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(this.username)) {
        this.usernameError = true;
        this.usernameErrorMessage = 'Formato de email inválido';
      }
    } else {
      // Validar username
      if (this.username.length < 3) {
        this.usernameError = true;
        this.usernameErrorMessage = 'El usuario debe tener al menos 3 caracteres';
      }
    }
  }

  validatePassword(): void {
    this.passwordError = false;
    this.passwordErrorMessage = '';

    if (!this.password) {
      this.passwordError = true;
      this.passwordErrorMessage = 'La contraseña es requerida';
      return;
    }

    if (this.password.length < 6) {
      this.passwordError = true;
      this.passwordErrorMessage = 'La contraseña debe tener al menos 6 caracteres';
    }
  }

  onLogin(): void {
    // Verificar si está bloqueado
    if (this.isBlocked) {
      this.loginMessage = `Demasiados intentos fallidos. Intenta en ${this.blockTimeRemaining} segundos.`;
      return;
    }

    // Validar campos
    this.validateUsername();
    this.validatePassword();
    this.loginMessage = '';
    this.successMessage = '';

    if (this.usernameError || this.passwordError) {
      this.loginMessage = 'Por favor, corrige los errores antes de continuar.';
      return;
    }

    this.loading = true;
    
    this.authService
      .login(this.username.trim(), this.password, this.keepLoggedIn)
      .pipe(finalize(() => this.loading = false))
      .subscribe({
        next: (success) => {
          if (success) {
            this.successMessage = '¡Inicio de sesión exitoso! Redirigiendo...';
            this.loginAttempts = 0; // Reset attempts
            setTimeout(() => {
              this.redirectByRole();
            }, 1500);
          } else {
            this.handleLoginError();
          }
        },
        error: (error) => {
          console.error('Error de login:', error);
          this.handleLoginError();
          
          if (error.status === 429) {
            this.loginMessage = 'Demasiados intentos. Intenta más tarde.';
          } else if (error.status === 0) {
            this.loginMessage = 'Error de conexión. Verifica tu conexión a internet.';
          }
        }
      });
  }

  private handleLoginError(): void {
    this.loginAttempts++;
    this.usernameError = true;
    this.passwordError = true;
    
    const remainingAttempts = this.maxAttempts - this.loginAttempts;
    
    if (remainingAttempts <= 0) {
      this.blockUser();
    } else {
      this.loginMessage = `Usuario o contraseña incorrectos. Te quedan ${remainingAttempts} intentos.`;
    }
  }

  private blockUser(): void {
    this.isBlocked = true;
    this.blockTimeRemaining = 300; // 5 minutos
    this.loginMessage = `Demasiados intentos fallidos. Intenta en ${this.blockTimeRemaining} segundos.`;
    
    localStorage.setItem('loginBlock', (Date.now() + this.blockTimeRemaining * 1000).toString());
    
    const timer = setInterval(() => {
      this.blockTimeRemaining--;
      this.loginMessage = `Demasiados intentos fallidos. Intenta en ${this.blockTimeRemaining} segundos.`;
      
      if (this.blockTimeRemaining <= 0) {
        this.isBlocked = false;
        this.loginAttempts = 0;
        this.loginMessage = '';
        localStorage.removeItem('loginBlock');
        clearInterval(timer);
      }
    }, 1000);
  }

  private checkBlockStatus(): void {
    const blockUntil = localStorage.getItem('loginBlock');
    if (blockUntil) {
      const remaining = Math.ceil((parseInt(blockUntil) - Date.now()) / 1000);
      if (remaining > 0) {
        this.isBlocked = true;
        this.blockTimeRemaining = remaining;
        this.blockUser();
      } else {
        localStorage.removeItem('loginBlock');
      }
    }
  }

  private redirectByRole(): void {
    const rol = this.authService.getUserRole();
    
    switch (rol) {
      case 'admin_polo':
        this.router.navigate(['/empresas']);
        break;
      case 'admin_empresa':
        this.router.navigate(['/me']);
        break;
      case 'publico':
        this.router.navigate(['/chat']);
        break;
      default:
        this.loginMessage = 'Rol no reconocido. Contacta al administrador.';
        this.authService.logoutLocal();
        break;
    }
  }

  // Métodos de recuperación de contraseña
  openResetModal(): void {
    this.showResetPassword = true;
    this.resetEmail = '';
    this.resetMessage = '';
    this.resetError = '';
  }

  closeResetModal(): void {
    this.showResetPassword = false;
    this.resetEmail = '';
    this.resetMessage = '';
    this.resetError = '';
  }

  validateResetEmail(): boolean {
    if (!this.resetEmail.trim()) {
      this.resetError = 'El email es requerido';
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.resetEmail)) {
      this.resetError = 'Formato de email inválido';
      return false;
    }

    this.resetError = '';
    return true;
  }

  requestPasswordReset(): void {
    if (!this.validateResetEmail()) {
      return;
    }

    this.resetLoading = true;
    this.resetMessage = '';
    this.resetError = '';

    this.authService.passwordResetRequest(this.resetEmail)
      .pipe(finalize(() => this.resetLoading = false))
      .subscribe({
        next: (res: any) => {
          if (res?.reset_token || res?.message) {
            this.resetMessage = 'Se ha enviado un enlace para restablecer tu contraseña. Revisa tu bandeja de entrada y spam.';
          } else {
            this.resetError = 'Respuesta inesperada del servidor.';
          }
        },
        error: (err) => {
          console.error('Error en recuperación:', err);
          
          if (err.status === 404) {
            this.resetError = 'Email no encontrado en el sistema.';
          } else if (err.status === 429) {
            this.resetError = 'Demasiadas solicitudes. Intenta más tarde.';
          } else {
            this.resetError = err?.error?.detail || 'Error al solicitar recuperación.';
          }
        }
      });
  }

  // Métodos de utilidad
  clearErrors(): void {
    this.usernameError = false;
    this.passwordError = false;
    this.usernameErrorMessage = '';
    this.passwordErrorMessage = '';
    this.loginMessage = '';
  }

  onUsernameChange(): void {
    if (this.usernameError) {
      this.validateUsername();
    }
  }

  onPasswordChange(): void {
    if (this.passwordError) {
      this.validatePassword();
    }
  }

  onResetEmailChange(): void {
    if (this.resetError) {
      this.resetError = '';
    }
  }

  loginWithGoogle(): void {
    // Redireccionar directamente al endpoint de Google OAuth
    window.location.href = 'http://localhost:8000/auth/google/login';
  }
}