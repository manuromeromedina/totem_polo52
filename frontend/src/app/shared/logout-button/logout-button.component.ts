import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthenticationService } from '../../auth/auth.service';

@Component({
  selector: 'app-logout-button',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './logout-button.component.html',
  styleUrls: ['./logout-button.component.css']
})
export class LogoutButtonComponent {
  loading = false;
  showModal = false;
  successMessage = '';
  errorMessage = '';

  constructor(private authService: AuthenticationService) {}

  // Mostrar modal de confirmación
  showLogoutModal() {
    this.showModal = true;
  }

  // Cancelar logout
  cancelLogout() {
    this.showModal = false;
  }

  // Confirmar y ejecutar logout
  confirmLogout() {
    this.loading = true;
    this.showModal = false;
    this.successMessage = '';
    this.errorMessage = '';

    this.authService.logout().subscribe({
      next: (success) => {
        this.loading = false;
        if (success) {
          this.successMessage = '✅ Sesión cerrada correctamente';
          // Mostrar mensaje por 2 segundos antes de redirigir
          setTimeout(() => {
            this.successMessage = '';
          }, 2000);
        } else {
          this.errorMessage = '⚠️ Error al cerrar sesión en el servidor, pero se cerró localmente';
          setTimeout(() => {
            this.errorMessage = '';
          }, 3000);
        }
      },
      error: (error) => {
        this.loading = false;
        console.error('Error en logout:', error);
        this.errorMessage = '❌ Error al cerrar sesión, pero se cerró localmente';
        setTimeout(() => {
          this.errorMessage = '';
        }, 3000);
      }
    });
  }

  // Logout directo (sin confirmación) - para usar si prefieres
  logout() {
    this.loading = true;
    this.successMessage = '';
    this.errorMessage = '';

    this.authService.logout().subscribe({
      next: (success) => {
        this.loading = false;
        if (success) {
          this.successMessage = '✅ Sesión cerrada correctamente';
          setTimeout(() => {
            this.successMessage = '';
          }, 2000);
        }
      },
      error: (error) => {
        this.loading = false;
        console.error('Error en logout:', error);
        this.errorMessage = '⚠️ Sesión cerrada localmente';
        setTimeout(() => {
          this.errorMessage = '';
        }, 3000);
      }
    });
  }
}