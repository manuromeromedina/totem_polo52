import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthenticationService } from '../auth.service';  // <-- importar tu servicio
import { CommonModule } from '@angular/common'; // para *ngIf
import { FormsModule } from '@angular/forms';   // para [(ngModel)]

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css'],
  standalone: true,
  imports: [CommonModule, FormsModule],

})
export class RegisterComponent {
  nombre: string = '';
  email: string = '';
  password: string = '';
  cuil: string = '';
  loading: boolean = false;
  errorMessage: string = '';

  constructor(private authService: AuthenticationService, private router: Router) {}

  onRegister() {
    

    this.loading = true;
    this.authService.register(this.nombre, this.email, this.password, this.cuil)
      .subscribe(success => {
        this.loading = false;
        if (success) {
          this.router.navigate(['/login']);
        } else {
          this.errorMessage = 'Error al registrar usuario';
        }
      });
  }
}
