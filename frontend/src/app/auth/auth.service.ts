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
  success?: boolean;
  error?: string;
  expired?: boolean;
}

interface TokenVerificationResponse {
  valid: boolean;
  message?: string;
  email_hint?: string;
  error?: string;
  expired?: boolean;
  used?: boolean;
  email?: string; // ← Agregar este campo
  user_name?: string; // ← Agregar este campo
}

@Injectable({ providedIn: 'root' })
export class AuthenticationService {
  private loginUrl = `${environment.apiUrl}/login`;
  private registerUrl = `${environment.apiUrl}/register`;
  private logoutUrl = `${environment.apiUrl}/logout`;
  private sessionKey = 'sessionToken';

  constructor(private http: HttpClient, private router: Router) {}

  passwordResetRequest(email: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/forgot-password`, {
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

  // 🆕 NUEVO MÉTODO - Verificar token de reset sin hacer cambios
  verifyResetToken(token: string): Observable<TokenVerificationResponse> {
    const params = new HttpParams().set('token', token);

    console.log('🔍 Verificando token:', token.substring(0, 20) + '...');

    return this.http
      .post<TokenVerificationResponse>(
        `${environment.apiUrl}/password-reset/verify-token`,
        null,
        { params }
      )
      .pipe(
        tap((response) => {
          console.log('✅ Verificación de token:', response);
        }),
        catchError((err) => {
          console.error('❌ Error verificando token:', err);

          // Transformar el error en una respuesta consistente
          const errorResponse: TokenVerificationResponse = {
            valid: false,
            error: err.error?.detail || err.message || 'Token inválido',
            expired:
              err.status === 400 ||
              (err.error?.detail && err.error.detail.includes('expirado')),
            used:
              err.status === 400 ||
              (err.error?.detail && err.error.detail.includes('utilizado')), // ✅ Detectar tokens usados
          };

          // Retornar como observable en lugar de error para manejar en el componente
          return of(errorResponse);
        })
      );
  }

  // - Ahora retorna el response completo para manejar errores
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
    // Limpiar tokens tradicionales
    localStorage.removeItem(this.sessionKey);
    localStorage.removeItem('rol');
    sessionStorage.removeItem(this.sessionKey);
    sessionStorage.removeItem('rol');

    // Limpiar tokens de Google OAuth
    localStorage.removeItem('access_token');
    localStorage.removeItem('tipo_rol');

    console.log('🧹 Sesión completamente limpiada');
  }

  logoutLocal(): void {
    this.clearSession();
    this.router.navigate(['/login']);
  }

  getUserRole(): string | null {
    // Primero buscar rol de Google OAuth
    const googleRole = localStorage.getItem('tipo_rol');
    if (googleRole) {
      console.log('👤 Rol encontrado (Google OAuth):', googleRole);
      return googleRole;
    }

    // Luego buscar rol tradicional
    const traditionalRole =
      localStorage.getItem('rol') || sessionStorage.getItem('rol');
    if (traditionalRole) {
      console.log('👤 Rol encontrado (Login tradicional):', traditionalRole);
      return traditionalRole;
    }

    console.log('❌ No se encontró ningún rol');
    return null;
  }

  isLoggedIn(): boolean {
    const token = this.getToken();
    if (!token) {
      console.log('🔍 isLoggedIn: No hay token');
      return false;
    }

    try {
      // Verificar si el token no está expirado
      const payload = JSON.parse(atob(token.split('.')[1]));
      const isExpired = Date.now() >= payload.exp * 1000;

      if (isExpired) {
        console.log('⏰ isLoggedIn: Token expirado');
        this.logoutLocal();
        return false;
      }

      console.log('✅ isLoggedIn: Usuario autenticado');
      return true;
    } catch (error) {
      console.error('❌ isLoggedIn: Error al verificar token:', error);
      this.logoutLocal();
      return false;
    }
  }

  getToken(): string | null {
    // Primero buscar el token de Google OAuth
    const googleToken = localStorage.getItem('access_token');
    if (googleToken) {
      console.log(
        '🔍 Token encontrado (Google OAuth):',
        googleToken.substring(0, 20) + '...'
      );
      return googleToken;
    }

    // Luego buscar el token tradicional
    const traditionalToken =
      localStorage.getItem(this.sessionKey) ||
      sessionStorage.getItem(this.sessionKey);
    if (traditionalToken) {
      console.log(
        '🔍 Token encontrado (Login tradicional):',
        traditionalToken.substring(0, 20) + '...'
      );
      return traditionalToken;
    }

    console.log('❌ No se encontró ningún token');
    return null;
  }

  setToken(token: string): void {
    localStorage.setItem('access_token', token);
    console.log(
      '💾 Token de Google OAuth guardado:',
      token.substring(0, 20) + '...'
    );
  }

  // ✅ MÉTODO MEJORADO - Guardar rol para Google OAuth
  setUserRole(role: string): void {
    localStorage.setItem('tipo_rol', role);
    console.log('👤 Rol de Google OAuth guardado:', role);
  }

  debugAuthState(): void {
    console.log('🔍 === DEBUG AUTH STATE ===');
    console.log(
      'Google OAuth Token:',
      localStorage.getItem('access_token') ? 'EXISTS' : 'NOT_FOUND'
    );
    console.log('Google OAuth Role:', localStorage.getItem('tipo_rol'));
    console.log(
      'Traditional Token (localStorage):',
      localStorage.getItem(this.sessionKey) ? 'EXISTS' : 'NOT_FOUND'
    );
    console.log(
      'Traditional Token (sessionStorage):',
      sessionStorage.getItem(this.sessionKey) ? 'EXISTS' : 'NOT_FOUND'
    );
    console.log(
      'Traditional Role:',
      localStorage.getItem('rol') || sessionStorage.getItem('rol')
    );
    console.log('Current getToken():', this.getToken() ? 'FOUND' : 'NOT_FOUND');
    console.log('Current getUserRole():', this.getUserRole());
    console.log('Current isLoggedIn():', this.isLoggedIn());
    console.log('=========================');
  }

  /**
   * Validar si una contraseña fue utilizada anteriormente (validación en tiempo real)
   */
  validatePasswordReset(data: {
    token: string;
    current_password: string;
    new_password: string;
    confirm_password: string;
    validate_only?: boolean;
  }): Observable<any> {
    return this.http
      .post(`${environment.apiUrl}/password-reset/validate`, data)
      .pipe(
        tap((response) => {
          console.log('🔍 Validación de contraseña:', response);
        }),
        catchError((err) => {
          console.error('❌ Error validando contraseña:', err);
          return throwError(() => err);
        })
      );
  }

  /**
   * Reset de contraseña con validación completa (método seguro)
   */
  /**
   * Cambio directo de contraseña para usuarios YA logueados
   * Requiere contraseña actual para validación
   */
  changePasswordDirect(data: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }): Observable<any> {
    const token = this.getToken();
    const headers = new HttpHeaders({
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    });

    console.log('🔐 Enviando cambio de contraseña directo:', {
      current_password: '***',
      new_password: '***',
      confirm_password: '***',
    });

    return this.http
      .post(`${environment.apiUrl}/change-password-direct`, data, { headers })
      .pipe(
        tap((response) => {
          console.log('✅ Cambio de contraseña directo exitoso:', response);
        }),
        catchError((err) => {
          console.error('❌ Error en cambio de contraseña directo:', err);
          return throwError(() => err);
        })
      );
  }

  /**
   * ACTUALIZAR TU MÉTODO EXISTENTE resetPasswordSecure para que sea flexible:
   * - Con current_password: Para usuarios logueados
   * - Sin current_password: Para usuarios NO logueados (via email token)
   */
  // Reemplazar tu resetPasswordSecure existente con esta versión mejorada:
  resetPasswordSecure(data: {
    token: string;
    current_password?: string; // <- Opcional para usuarios NO logueados
    new_password: string;
    confirm_password: string;
  }): Observable<any> {
    const isLoggedUser = !!data.current_password;

    console.log(
      `🔒 Enviando reset password ${
        isLoggedUser ? '(usuario logueado)' : '(usuario público)'
      }:`,
      {
        token: data.token.substring(0, 20) + '...',
        current_password: data.current_password ? '***' : 'N/A',
        new_password: '***',
        confirm_password: '***',
      }
    );

    return this.http
      .post(`${environment.apiUrl}/password-reset/confirm-secure`, data)
      .pipe(
        tap((response) => {
          console.log(
            `✅ Reset password ${
              isLoggedUser ? 'logueado' : 'público'
            } exitoso:`,
            response
          );
        }),
        catchError((err) => {
          console.error(
            `❌ Error en reset password ${
              isLoggedUser ? 'logueado' : 'público'
            }:`,
            err
          );
          return throwError(() => err);
        })
      );
  }

  /**
   * Solicitar reset de contraseña via email (usuarios NO logueados)
   */
  forgotPassword(email: string): Observable<any> {
    return this.http
      .post(`${environment.apiUrl}/forgot-password`, { email })
      .pipe(
        tap((response) => {
          console.log('📧 Solicitud de reset enviada:', response);
        }),
        catchError((err) => {
          console.error('❌ Error enviando solicitud de reset:', err);
          return throwError(() => err);
        })
      );
  }
}
