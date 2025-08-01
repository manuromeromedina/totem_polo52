import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Empresa {
  cuil: number;
  nombre: string;
  rubro: string;
  cant_empleados: number;
  observaciones?: string;
  fecha_ingreso: string;
  horario_trabajo: string;
}

export interface EmpresaCreate {
  cuil: number;
  nombre: string;
  rubro: string;
  cant_empleados: number;
  observaciones?: string;
  fecha_ingreso?: string;
  horario_trabajo: string;
}

export interface EmpresaUpdate {
  nombre?: string;
  rubro?: string;
}

export interface Usuario {
  id_usuario: string;
  email: string;
  nombre: string;
  estado: boolean;
  fecha_registro: string;
  cuil: number;
}

export interface UsuarioCreate {
  email: string;
  nombre: string;
  password: string;
  estado: boolean;
  cuil: number;
  id_rol: number;
}

export interface UsuarioUpdate {
  password?: string;
  estado?: boolean;
}

export interface Rol {
  id_rol: number;
  tipo_rol: string;
}

export interface ServicioPolo {
  id_servicio_polo: number;
  nombre: string;
  horario?: string;
  datos?: any;
  propietario?: string;
  id_tipo_servicio_polo: number;
  cuil: number;
  tipo_servicio_polo?: string;
}

export interface ServicioPoloCreate {
  nombre: string;
  horario?: string;
  datos?: any;
  propietario?: string;
  id_tipo_servicio_polo: number;
  cuil: number;
}

export interface Lote {
  id_lotes: number;
  dueno: string;
  lote: number;
  manzana: number;
  id_servicio_polo: number;
}

export interface LoteCreate {
  dueno: string;
  lote: number;
  manzana: number;
  id_servicio_polo: number;
}

@Injectable({
  providedIn: 'root'
})
export class AdminPoloService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Roles
  getRoles(): Observable<Rol[]> {
    return this.http.get<Rol[]>(`${this.apiUrl}/roles`);
  }

  // Usuarios
  getUsers(): Observable<Usuario[]> {
    return this.http.get<Usuario[]>(`${this.apiUrl}/usuarios`);
  }

  getUser(userId: string): Observable<Usuario> {
    return this.http.get<Usuario>(`${this.apiUrl}/${userId}`);
  }

  createUser(usuario: UsuarioCreate): Observable<Usuario> {
    return this.http.post<Usuario>(`${this.apiUrl}/usuarios`, usuario);
  }

  updateUser(userId: string, usuario: UsuarioUpdate): Observable<Usuario> {
    return this.http.put<Usuario>(`${this.apiUrl}/usuarios/${userId}`, usuario);
  }

  deleteUser(userId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/usuarios/${userId}`);
  }

  // Empresas
  getEmpresas(): Observable<Empresa[]> {
    return this.http.get<Empresa[]>(`${this.apiUrl}/empresas`);
  }

  createEmpresa(empresa: EmpresaCreate): Observable<Empresa> {
    return this.http.post<Empresa>(`${this.apiUrl}/empresas`, empresa);
  }

  updateEmpresa(cuil: number, empresa: EmpresaUpdate): Observable<Empresa> {
    return this.http.put<Empresa>(`${this.apiUrl}/empresas/${cuil}`, empresa);
  }

  deleteEmpresa(cuil: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/empresas/${cuil}`);
  }

  // Servicios del Polo
  getServiciosPolo(): Observable<ServicioPolo[]> {
    return this.http.get<ServicioPolo[]>(`${this.apiUrl}/serviciopolo`);
  }

  createServicioPolo(servicio: ServicioPoloCreate): Observable<ServicioPolo> {
    return this.http.post<ServicioPolo>(`${this.apiUrl}/serviciopolo`, servicio);
  }

  deleteServicioPolo(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/serviciopolo/${id}`);
  }

  // Lotes
  getLotes(): Observable<Lote[]> {
    return this.http.get<Lote[]>(`${this.apiUrl}/lotes`);
  }

  createLote(lote: LoteCreate): Observable<Lote> {
    return this.http.post<Lote>(`${this.apiUrl}/lotes`, lote);
  }

  deleteLote(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/lotes/${id}`);
  }
}