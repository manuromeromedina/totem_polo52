 // src/app/app.module.ts
 import { NgModule } from '@angular/core';
 import { BrowserModule } from '@angular/platform-browser';
 import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
 import { RouterModule } from '@angular/router';

import { AppComponent }    from './app.component';  // es standalone

 import { AuthInterceptor } from './auth/auth.interceptor';

 @NgModule({
  imports: [
    BrowserModule,
   AppComponent,        // ← aquí lo importas
    HttpClientModule,
    RouterModule.forRoot([
      {
        path: 'login',
        loadComponent: () =>
          import('./auth/login/login.component').then(m => m.LoginComponent)
      },
      {
        path: 'register',
        loadComponent: () =>
          import('./auth/register/register.component').then(m => m.RegisterComponent)
      },
      {
        path: 'dashboard',
        loadChildren: () =>
          import('./dashboard/dashboard.module').then(m => m.DashboardModule)
      },
      { path: '', redirectTo: 'login', pathMatch: 'full' },
      { path: '**', redirectTo: 'login' }
    ])
  ],
  providers: [
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
  ],
  bootstrap: [AppComponent]
 })
 export class AppModule {}
