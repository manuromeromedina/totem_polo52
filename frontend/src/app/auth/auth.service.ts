// src/app/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { tap, map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

interface LoginResponse {
  access_token: string;
  token_type: string;
  tipo_rol: string;
}

interface RegisterResponse {
  message: string;
}

interface LogoutResponse {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AuthenticationService {
  private loginUrl = `${environment.apiUrl}/login`;
  private registerUrl = `${environment.apiUrl}/register`;
  private logoutUrl = `${environment.apiUrl}/logout`;
  private sessionKey = 'sessionToken';

  constructor(private http: HttpClient, private router: Router) {}

  passwordResetRequest(email: string) {
    return this.http.post(`${environment.apiUrl}/password-reset/request`, { email });
  }

  resetPassword(token: string, newPassword: string): Observable<boolean> {
    const body = { token, new_password: newPassword };
    return this.http.post(`${environment.apiUrl}/password-reset/confirm`, body)
      .pipe(
        map(() => true),
        catchError(err => {
          console.error('Reset failed', err);
          return of(false);
        })
      );
  }

  // 🔧 MÉTODO REGISTER CORREGIDO
  register(username: string, email: string, password: string, cuil: string): Observable<boolean> {
    const body = {
      nombre: username,
      email: email,
      password: password,
      cuil: cuil
    };

    // 🔍 DEBUG: Log de los datos enviados
    console.log('🚀 Datos enviados al backend:', body);

    const headers = new HttpHeaders({
      'Content-Type': 'application/json'
    });

    return this.http.post<RegisterResponse>(this.registerUrl, body, { headers })
      .pipe(
        tap(response => {
          console.log('✅ Registro exitoso:', response);
        }),
        map(() => true),
        catchError(err => {
          console.error('❌ Error de registro completo:', err);
          console.error('Status:', err.status);
          console.error('Error body:', err.error);
          console.error('Headers:', err.headers);
          
          // 🚨 IMPORTANTE: Re-lanzar el error para que llegue al componente
          return throwError(() => err);
        })
      );
  }

  login(username: string, password: string, keepLoggedIn: boolean): Observable<boolean> {
    const body = new HttpParams()
      .set('grant_type', 'password')
      .set('username', username)
      .set('password', password);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded'
    });

    return this.http
      .post<LoginResponse>(this.loginUrl, body.toString(), { headers })
      .pipe(
        tap(res => {
          const storage = keepLoggedIn ? localStorage : sessionStorage;
          storage.setItem(this.sessionKey, res.access_token);
          storage.setItem('rol', res.tipo_rol);
        }),
        map(() => true),
        catchError(err => {
          console.error('Login fallido', err);
          return throwError(() => err); // También corregido para propagar errores
        })
      );
  }

  // Nuevo método logout mejorado
  logout(): Observable<boolean> {
    const token = this.getToken();
    
    if (!token) {
      // Si no hay token, solo limpiar y redirigir
      this.clearSession();
      this.router.navigate(['/login']);
      return of(true);
    }

    // Hacer petición al backend para cerrar sesión
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });

    return this.http.post<LogoutResponse>(this.logoutUrl, {}, { headers })
      .pipe(
        tap(response => {
          console.log('Logout response:', response);
          this.clearSession();
          this.router.navigate(['/login']);
        }),
        map(() => true),
        catchError(err => {
          console.error('Error en logout:', err);
          // Aunque falle el backend, limpiar la sesión local
          this.clearSession();
          this.router.navigate(['/login']);
          return of(false);
        })
      );
  }

  // Método para limpiar la sesión local
  private clearSession(): void {
    localStorage.removeItem(this.sessionKey);
    localStorage.removeItem('rol');
    sessionStorage.removeItem(this.sessionKey);
    sessionStorage.removeItem('rol');
  }

  // Método para logout sin llamada al backend (emergencia)
  logoutLocal(): void {
    this.clearSession();
    this.router.navigate(['/login']);
  }

  getUserRole(): string | null {
    return localStorage.getItem('rol') || sessionStorage.getItem('rol');
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  getToken(): string | null {
    return localStorage.getItem(this.sessionKey) || sessionStorage.getItem(this.sessionKey);
  }
}