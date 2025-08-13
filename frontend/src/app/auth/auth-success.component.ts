// =============================================================================
// ARCHIVO CORREGIDO: src/app/auth/auth-success/auth-success.component.ts
// =============================================================================

import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthenticationService } from './auth.service'; // ← CORREGIR IMPORT

@Component({
  selector: 'app-auth-success',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div style="padding: 20px; background: lightgreen; color: black; min-height: 100vh;">
      <h1>🎉 AUTH SUCCESS COMPONENT CARGADO</h1>
      
      <h2>Parámetros recibidos:</h2>
      <p><strong>Token:</strong> {{ receivedToken }}</p>
      <p><strong>Rol:</strong> {{ receivedRole }}</p>
      
      <h2>Estado después de guardar:</h2>
      <p><strong>Token en localStorage:</strong> {{ tokenInStorage }}</p>
      <p><strong>Rol en localStorage:</strong> {{ roleInStorage }}</p>
      <p><strong>isLoggedIn():</strong> {{ isLoggedIn }}</p>
      <p><strong>authService.getToken():</strong> {{ serviceToken }}</p>
      <p><strong>authService.getUserRole():</strong> {{ serviceRole }}</p>
      
      <button (click)="manualRedirect()" 
              style="padding: 10px; background: blue; color: white; margin: 10px;">
        Redireccionar Manualmente
      </button>
      
      <button (click)="debugInfo()" 
              style="padding: 10px; background: orange; color: white; margin: 10px;">
        Mostrar Debug Info
      </button>
      
      <div style="margin-top: 20px; background: #f0f0f0; padding: 10px; color: black;">
        <h3>Logs en tiempo real:</h3>
        <div>{{ statusMessage }}</div>
      </div>
    </div>
  `
})
export class AuthSuccessComponent implements OnInit {
  receivedToken = 'NO_RECIBIDO';
  receivedRole = 'NO_RECIBIDO';
  tokenInStorage = 'NO_GUARDADO';
  roleInStorage = 'NO_GUARDADO';
  isLoggedIn = false;
  serviceToken = 'NO_ENCONTRADO';
  serviceRole = 'NO_ENCONTRADO';
  statusMessage = 'Iniciando...';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthenticationService
  ) {}

  ngOnInit(): void {
    console.log('🎉 AUTH SUCCESS COMPONENT INICIADO');
    this.statusMessage = 'Componente iniciado, esperando parámetros...';
    
    this.route.queryParams.subscribe(params => {
      console.log('📨 Parámetros recibidos:', params);
      
      const token = params['token'];
      const tipoRol = params['tipo_rol'];
      
      this.receivedToken = token || 'NO_RECIBIDO';
      this.receivedRole = tipoRol || 'NO_RECIBIDO';
      
      if (token && tipoRol) {
        this.statusMessage = 'Parámetros recibidos, guardando...';
        this.processAuth(token, tipoRol);
      } else {
        this.statusMessage = 'ERROR: Parámetros faltantes';
        console.error('❌ Parámetros faltantes:', { token: !!token, tipoRol: !!tipoRol });
      }
      
      this.updateStatus();
    });
  }

  processAuth(token: string, role: string): void {
    console.log('💾 Guardando credenciales...');
    
    // Método 1: Usar AuthenticationService
    this.authService.setToken(token);
    this.authService.setUserRole(role);
    
    // Método 2: Guardar directamente (backup)
    localStorage.setItem('access_token', token);
    localStorage.setItem('tipo_rol', role);
    
    console.log('✅ Credenciales guardadas');
    
    // Verificar que se guardó
    this.updateStatus();
    
    // Verificar isLoggedIn
    const loggedIn = this.authService.isLoggedIn();
    console.log('🔍 isLoggedIn resultado:', loggedIn);
    
    if (loggedIn) {
      this.statusMessage = 'Autenticación exitosa, redirigiendo en 3 segundos...';
      setTimeout(() => {
        this.redirectByRole(role);
      }, 3000);
    } else {
      this.statusMessage = 'ERROR: isLoggedIn() retorna false';
      console.error('❌ isLoggedIn() retorna false después de guardar');
    }
  }

  updateStatus(): void {
    this.tokenInStorage = localStorage.getItem('access_token') || 'NO_GUARDADO';
    this.roleInStorage = localStorage.getItem('tipo_rol') || 'NO_GUARDADO';
    this.serviceToken = this.authService.getToken() || 'NO_ENCONTRADO';
    this.serviceRole = this.authService.getUserRole() || 'NO_ENCONTRADO';
    this.isLoggedIn = this.authService.isLoggedIn();
    
    console.log('📊 Estado actualizado:');
    console.log('- Token en localStorage:', this.tokenInStorage !== 'NO_GUARDADO');
    console.log('- Rol en localStorage:', this.roleInStorage);
    console.log('- Service getToken():', this.serviceToken !== 'NO_ENCONTRADO');
    console.log('- Service getUserRole():', this.serviceRole);
    console.log('- Service isLoggedIn():', this.isLoggedIn);
  }

  manualRedirect(): void {
    const role = localStorage.getItem('tipo_rol') || this.receivedRole;
    if (role && role !== 'NO_RECIBIDO') {
      this.redirectByRole(role);
    } else {
      alert('No hay rol para redireccionar');
    }
  }

  redirectByRole(role: string): void {
    console.log('🔄 Redirigiendo según rol:', role);
    
    let destination = '/login'; // fallback
    
    switch (role) {
      case 'admin_polo':
        destination = '/empresas';
        break;
      case 'admin_empresa':
        destination = '/me';
        break;
      case 'publico':
        destination = '/chat';
        break;
      default:
        console.warn('⚠️ Rol no reconocido:', role);
        destination = '/dashboard';
        break;
    }
    
    console.log('🎯 Navegando a:', destination);
    this.statusMessage = `Redirigiendo a ${destination}...`;
    
    this.router.navigate([destination]);
  }

  debugInfo(): void {
    console.log('=== DEBUG COMPLETO ===');
    console.log('URL actual:', window.location.href);
    console.log('Parámetros de ruta:', this.route.snapshot.queryParams);
    console.log('localStorage access_token:', localStorage.getItem('access_token'));
    console.log('localStorage tipo_rol:', localStorage.getItem('tipo_rol'));
    console.log('localStorage sessionToken:', localStorage.getItem('sessionToken'));
    console.log('localStorage rol:', localStorage.getItem('rol'));
    console.log('authService.getToken():', this.authService.getToken());
    console.log('authService.getUserRole():', this.authService.getUserRole());
    console.log('authService.isLoggedIn():', this.authService.isLoggedIn());
    
    // Llamar al debug del servicio si existe
    if (this.authService.debugAuthState) {
      this.authService.debugAuthState();
    }
    
    alert('Debug info mostrado en consola');
  }
}