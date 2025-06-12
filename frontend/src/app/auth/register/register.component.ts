// src/app/auth/register.component.ts
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule }  from '@angular/forms';
import { Router }       from '@angular/router';
import { AuthenticationService } from '../auth.service';
import { finalize } from 'rxjs/operators';
import { RouterModule } from '@angular/router';


@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule , RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent {
  nombre = '';
  email  = '';
  cuil   = '';
  password        = '';
  confirmPassword = '';

  errorMessage = '';
  loading = false;

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {}

  onRegister() {
    this.errorMessage = '';
    if (!this.nombre || !this.email || !this.cuil || !this.password) {
      this.errorMessage = 'Completa todos los campos.';
      return;
    }
    if (this.password !== this.confirmPassword) {
      this.errorMessage = 'Las contraseñas no coinciden.';
      return;
    }

    this.loading = true;
    this.authService
      .register(this.nombre, this.email, this.password)
      .pipe(finalize(() => this.loading = false))
      .subscribe(success => {
        if (success) {
          this.router.navigate(['/login']);
        } else {
          this.errorMessage = 'Error al registrarse.';
        }
      }, () => {
        this.errorMessage = 'Error de red. Intenta más tarde.';
      });
  }
}
