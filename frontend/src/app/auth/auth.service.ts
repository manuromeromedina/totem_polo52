// src/app/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { tap, map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

interface LoginResponse {
  access_token: string;
  token_type: string;
  tipo_rol: string; // ⬅️ agregá esta línea

}
interface RegisterResponse {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AuthenticationService {
  private loginUrl    = `${environment.apiUrl}/login`;
  private registerUrl = `${environment.apiUrl}/register`;
  private sessionKey  = 'sessionToken';

  constructor(private http: HttpClient, private router: Router) {}
  
  
  
  passwordResetRequest(email: string) {
  return this.http.post(`${environment.apiUrl}/password-reset/request`, { email });
}


resetPassword(token: string, newPassword: string): Observable<boolean> {
    const body = { token, new_password: newPassword }; // Matches backend expectation
    return this.http.post(`${environment.apiUrl}/password-reset/confirm`, body)
      .pipe(
        map(() => true),
        catchError(err => {
          console.error('Reset failed', err);
          return of(false);
        })
      );
  }


 register(username: string, email: string, password: string, cuil: string): Observable<boolean> {
  return this.http.post<RegisterResponse>(this.registerUrl, {
    nombre: username,
    email,
    password,
    cuil  
  }).pipe(
    map(() => true),
    catchError(err => {
      console.error('Registro fallido', err);
      return of(false);
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
        storage.setItem('rol', res.tipo_rol); // <--- aquí guardamos el rol
      }),
      map(() => true),
      catchError(err => {
        console.error('Login fallido', err);
        return of(false);
      })
    );
}
  getUserRole(): string | null {
    return localStorage.getItem('rol') || sessionStorage.getItem('rol');
  }


  logout(): void {
    localStorage.removeItem(this.sessionKey);
    sessionStorage.removeItem(this.sessionKey);
    this.router.navigate(['/login']);
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  getToken(): string | null {
    return localStorage.getItem(this.sessionKey)
        || sessionStorage.getItem(this.sessionKey);
  }
}
