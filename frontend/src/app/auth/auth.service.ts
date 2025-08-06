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

interface PasswordResetResponse {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AuthenticationService {
  private loginUrl = `${environment.apiUrl}/login`;
  private registerUrl = `${environment.apiUrl}/register`;
  private logoutUrl = `${environment.apiUrl}/logout`;
  private sessionKey = 'sessionToken';

  constructor(private http: HttpClient, private router: Router) {}

  passwordResetRequest(email: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/password-reset/request`, {
      email,
    });
  }

  // Cambiar contraseña del usuario logueado (envía email)
  changePasswordRequest(): Observable<any> {
    return this.http.post(
      `${environment.apiUrl}/password-reset/request-logged-user`,
      {}
    );
  }

  // ✅ MÉTODO CORREGIDO - Ahora retorna el response completo para manejar errores
  resetPassword(
    token: string,
    newPassword: string
  ): Observable<PasswordResetResponse> {
    const body = { token, new_password: newPassword };

    console.log('🔄 Enviando reset password:', {
      token: token.substring(0, 20) + '...',
      newPassword: '***',
    });

    return this.http
      .post<PasswordResetResponse>(
        `${environment.apiUrl}/password-reset/confirm`,
        body
      )
      .pipe(
        tap((response) => {
          console.log('✅ Reset password exitoso:', response);
        }),
        catchError((err) => {
          console.error('❌ Error en reset password:', err);
          // Re-lanzar el error para que el componente pueda manejarlo
          return throwError(() => err);
        })
      );
  }

  register(
    username: string,
    email: string,
    password: string,
    cuil: string
  ): Observable<boolean> {
    return this.http
      .post<RegisterResponse>(this.registerUrl, {
        nombre: username,
        email,
        password,
        cuil,
      })
      .pipe(
        map(() => true),
        catchError((err) => {
          console.error('Registro fallido', err);
          return of(false);
        })
      );
  }

  login(
    username: string,
    password: string,
    keepLoggedIn: boolean
  ): Observable<boolean> {
    const body = new HttpParams()
      .set('grant_type', 'password')
      .set('username', username)
      .set('password', password);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded',
    });

    return this.http
      .post<LoginResponse>(this.loginUrl, body.toString(), { headers })
      .pipe(
        tap((res) => {
          const storage = keepLoggedIn ? localStorage : sessionStorage;
          storage.setItem(this.sessionKey, res.access_token);
          storage.setItem('rol', res.tipo_rol);
          // 🔍 Log para verificar
          console.log('✅ TOKEN GUARDADO:', res.access_token);
          console.log('📦 STORAGE ACTUAL:', storage.getItem(this.sessionKey));
        }),
        map(() => true),
        catchError((err) => {
          console.error('Login fallido', err);
          return of(false);
        })
      );
  }

  logout(): Observable<boolean> {
    const token = this.getToken();

    if (!token) {
      this.clearSession();
      this.router.navigate(['/login']);
      return of(true);
    }

    const headers = new HttpHeaders({
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    });

    return this.http.post<LogoutResponse>(this.logoutUrl, {}, { headers }).pipe(
      tap(() => {
        this.clearSession();
        this.router.navigate(['/login']);
      }),
      map(() => true),
      catchError((err) => {
        console.error('Error en logout:', err);
        this.clearSession();
        this.router.navigate(['/login']);
        return of(false);
      })
    );
  }

  private clearSession(): void {
    localStorage.removeItem(this.sessionKey);
    localStorage.removeItem('rol');
    sessionStorage.removeItem(this.sessionKey);
    sessionStorage.removeItem('rol');
  }

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
    return (
      localStorage.getItem(this.sessionKey) ||
      sessionStorage.getItem(this.sessionKey)
    );
  }
}
