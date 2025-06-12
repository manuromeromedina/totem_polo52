import { Component } from '@angular/core';
import { AuthenticationService } from '../auth.service';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common'; 
import { FormsModule } from '@angular/forms';   

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule], 
  templateUrl: './login.component.html', 
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  username: string = '';
  password: string = '';
  keepLoggedIn: boolean = false;
  usernameError: boolean = false;
  passwordError: boolean = false;
  loginMessage: string = '';

  constructor(private authService: AuthenticationService, private router: Router) {}

  onLogin() {
    // Reiniciar errores y mensaje
    this.usernameError = false;
    this.passwordError = false;
    this.loginMessage = '';

    // Validación básica
    if (!this.username || !this.password) {
      this.usernameError = !this.username;
      this.passwordError = !this.password;
      this.loginMessage = 'Por favor, completa todos los campos.';
      return;
    }

    // Intentar login
    const success = this.authService.login(this.username, this.password, this.keepLoggedIn);
    if (success) {
      this.router.navigate(['/dashboard']); // Ajusta la ruta según tu app
    } else {
      this.usernameError = true; // Simula error en usuario para el borde rojo
      this.loginMessage = 'Credenciales incorrectas.';
    }
  }
}