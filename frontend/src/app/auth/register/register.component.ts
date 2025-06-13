import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthenticationService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css'],
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
})
export class RegisterComponent {
  // Datos del formulario
  nombre: string = '';
  email: string = '';
  password: string = '';
  cuil: string = '';

  // Estados de validación
  nombreError = false;
  emailError = false;
  passwordError = false;
  cuilError = false;

  // Mensajes de error específicos
  nombreErrorMessage = '';
  emailErrorMessage = '';
  passwordErrorMessage = '';
  cuilErrorMessage = '';

  // Estados de UI
  loading = false;
  errorMessage = '';
  successMessage = '';
  showPassword = false;

  constructor(
    private authService: AuthenticationService, 
    private router: Router
  ) {}

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  validateNombre(): void {
    this.nombreError = false;
    this.nombreErrorMessage = '';

    if (!this.nombre.trim()) {
      this.nombreError = true;
      this.nombreErrorMessage = 'El nombre es requerido';
      return;
    }

    if (this.nombre.trim().length < 2) {
      this.nombreError = true;
      this.nombreErrorMessage = 'El nombre debe tener al menos 2 caracteres';
      return;
    }

    if (this.nombre.trim().length > 100) {
      this.nombreError = true;
      this.nombreErrorMessage = 'El nombre no puede exceder 100 caracteres';
    }
  }

  validateEmail(): void {
    this.emailError = false;
    this.emailErrorMessage = '';

    if (!this.email.trim()) {
      this.emailError = true;
      this.emailErrorMessage = 'El email es requerido';
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.email)) {
      this.emailError = true;
      this.emailErrorMessage = 'Formato de email inválido';
    }
  }

  validateCuil(): void {
    this.cuilError = false;
    this.cuilErrorMessage = '';

    if (!this.cuil.trim()) {
      this.cuilError = true;
      this.cuilErrorMessage = 'El CUIL es requerido';
      return;
    }

    // Remover guiones y espacios
    const cuilClean = this.cuil.replace(/[-\s]/g, '');
    
    if (!/^\d{11}$/.test(cuilClean)) {
      this.cuilError = true;
      this.cuilErrorMessage = 'El CUIL debe tener 11 dígitos';
      return;
    }

    // Actualizar el campo con formato limpio
    this.cuil = cuilClean;
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

  onRegister(): void {
    // Validar todos los campos
    this.validateNombre();
    this.validateEmail();
    this.validateCuil();
    this.validatePassword();

    // Limpiar mensajes generales
    this.errorMessage = '';
    this.successMessage = '';

    // Verificar si hay errores
    if (this.nombreError || this.emailError || this.cuilError || this.passwordError) {
      this.errorMessage = 'Por favor, corrige los errores antes de continuar.';
      return;
    }

    // 🔍 DEBUG: Mostrar datos antes de enviar
    console.log('📝 Datos del formulario:');
    console.log('Nombre:', this.nombre.trim());
    console.log('Email:', this.email.trim());
    console.log('Password:', this.password);
    console.log('CUIL:', this.cuil);

    this.loading = true;

    this.authService.register(this.nombre.trim(), this.email.trim(), this.password, this.cuil)
      .pipe(finalize(() => this.loading = false))
      .subscribe({
        next: (success) => {
          console.log('✅ Registro completado exitosamente');
          this.successMessage = '¡Registro exitoso! Redirigiendo al login...';
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 2000);
        },
        error: (error) => {
          console.error('❌ Error detallado de registro:', error);
          console.log('📊 Status Code:', error.status);
          console.log('📄 Error Response:', error.error);
          console.log('📋 Error Message:', error.message);
          
          // Manejo específico por tipo de error
          if (error.status === 422) {
            // Error de validación - datos inválidos
            let errorDetail = '';
            
            if (error.error && error.error.detail) {
              if (Array.isArray(error.error.detail)) {
                // FastAPI validation errors
                errorDetail = error.error.detail.map((err: any) => 
                  `${err.loc ? err.loc.join('.') : 'Campo'}: ${err.msg}`
                ).join(', ');
              } else {
                errorDetail = error.error.detail;
              }
            }
            
            this.errorMessage = errorDetail || 'Datos inválidos. Verifica la información ingresada.';
            console.log('🔍 Detalles del error 422:', errorDetail);
            
          } else if (error.status === 409) {
            this.errorMessage = 'El email o CUIL ya está registrado.';
          } else if (error.status === 400) {
            this.errorMessage = 'Solicitud incorrecta. Verifica los datos.';
          } else if (error.status === 0) {
            this.errorMessage = 'Error de conexión. Verifica tu conexión a internet.';
          } else if (error.status >= 500) {
            this.errorMessage = 'Error del servidor. Intenta más tarde.';
          } else {
            this.errorMessage = error?.error?.detail || error?.error?.message || 'Error al registrar usuario.';
          }
        }
      });
  }

  // Métodos de utilidad
  onNombreChange(): void {
    if (this.nombreError) {
      this.validateNombre();
    }
  }

  onEmailChange(): void {
    if (this.emailError) {
      this.validateEmail();
    }
  }

  onCuilChange(): void {
    if (this.cuilError) {
      this.validateCuil();
    }
  }

  onPasswordChange(): void {
    if (this.passwordError) {
      this.validatePassword();
    }
  }

  formatCuil(): void {
    // Formatear CUIL mientras se escribe (opcional)
    let value = this.cuil.replace(/\D/g, '');
    if (value.length >= 11) {
      value = value.substring(0, 11);
    }
    this.cuil = value;
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}