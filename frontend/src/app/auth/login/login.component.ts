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

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {}

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onLogin() {
    // reset errores
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
          this.router.navigate(['/dashboard']);
        } else {
          this.usernameError = true;
          this.passwordError = true;
          this.loginMessage = 'Usuario o contraseña inválidos.';
        }
      }, () => {
        this.loginMessage = 'Error de conexión. Intenta de nuevo más tarde.';
      });
  }
}
