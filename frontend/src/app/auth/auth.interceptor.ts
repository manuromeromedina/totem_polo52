// src/app/auth.interceptor.ts
import { Injectable } from '@angular/core';
import { HttpEvent, HttpInterceptor, HttpRequest, HttpHandler  } from '@angular/common/http';
import { AuthenticationService } from './auth.service';
import { Observable } from 'rxjs';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private auth: AuthenticationService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = this.auth.getToken();
    
    // 🔍 Debug logs
    console.log('🌐 INTERCEPTOR - URL:', req.url);
    console.log('🔑 INTERCEPTOR - Token:', token ? 'EXISTS' : 'NOT FOUND');
    
    if (token) {
      const clone = req.clone({
        setHeaders: { Authorization: `Bearer ${token}` }
      });
      console.log('✅ INTERCEPTOR - Token añadido a la request');
      return next.handle(clone);
    }
    
    console.log('❌ INTERCEPTOR - No token, request sin autorización');
    return next.handle(req);
  }
}