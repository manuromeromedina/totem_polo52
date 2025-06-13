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
  if (token) {
    const clone = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
    return next.handle(clone);
  }
  return next.handle(req);
}

}
