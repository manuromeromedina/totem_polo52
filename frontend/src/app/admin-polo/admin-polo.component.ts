import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AdminPoloService, Empresa, EmpresaCreate, EmpresaUpdate, Usuario, UsuarioCreate, UsuarioUpdate, Rol, ServicioPolo, ServicioPoloCreate, Lote, LoteCreate } from './admin-polo.service';
import { LogoutButtonComponent } from '../shared/logout-button/logout-button.component';

@Component({
  selector: 'app-empresas',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LogoutButtonComponent],
  templateUrl: './admin-polo.component.html',
  styleUrls: ['./admin-polo.component.css']
})
export class EmpresasComponent implements OnInit {
  activeTab = 'empresas';
  
  // Empresas
  empresas: Empresa[] = [];
  showEmpresaForm = false;
  editingEmpresa: Empresa | null = null;
  empresaForm: EmpresaCreate = {
    cuil: 0,
    nombre: '',
    rubro: '',
    cant_empleados: 0,
    observaciones: '',
    horario_trabajo: ''
  };

  // Usuarios
  usuarios: Usuario[] = [];
  roles: Rol[] = [];
  showUsuarioForm = false;
  editingUsuario: Usuario | null = null;
  usuarioForm: UsuarioCreate = {
    email: '',
    nombre: '',
    password: '',
    estado: true,
    cuil: 0,
    id_rol: 0
  };

  // Servicios del Polo
  serviciosPolo: ServicioPolo[] = [];
  showServicioPoloForm = false;
  servicioPoloForm: ServicioPoloCreate = {
    nombre: '',
    horario: '',
    datos: {},
    propietario: '',
    id_tipo_servicio_polo: 1,
    cuil: 0
  };

  // Lotes
  lotes: Lote[] = [];
  showLoteForm = false;
  loteForm: LoteCreate = {
    dueno: '',
    lote: 0,
    manzana: 0,
    id_servicio_polo: 0
  };

  // Estados
  loading = false;
  message = '';
  messageType: 'success' | 'error' = 'success';

  constructor(private adminPoloService: AdminPoloService) {}

  ngOnInit(): void {
    this.loadRoles();
    this.loadData();
  }

  setActiveTab(tab: string): void {
    this.activeTab = tab;
    this.resetForms();
    this.loadData();
  }

  loadRoles(): void {
    this.adminPoloService.getRoles().subscribe({
      next: (roles) => {
        this.roles = roles;
      },
      error: (error) => {
        console.error('Error loading roles:', error);
      }
    });
  }

  loadData(): void {
    // En un caso real, tendrías endpoints para listar
    // Por ahora solo limpiamos las listas
    this.empresas = [];
    this.usuarios = [];
    this.serviciosPolo = [];
    this.lotes = [];
  }

  resetForms(): void {
    this.showEmpresaForm = false;
    this.showUsuarioForm = false;
    this.showServicioPoloForm = false;
    this.showLoteForm = false;
    this.editingEmpresa = null;
    this.editingUsuario = null;
    this.message = '';
    
    this.empresaForm = {
      cuil: 0,
      nombre: '',
      rubro: '',
      cant_empleados: 0,
      observaciones: '',
      horario_trabajo: ''
    };
    
    this.usuarioForm = {
      email: '',
      nombre: '',
      password: '',
      estado: true,
      cuil: 0,
      id_rol: 0
    };
    
    this.servicioPoloForm = {
      nombre: '',
      horario: '',
      datos: {},
      propietario: '',
      id_tipo_servicio_polo: 1,
      cuil: 0
    };
    
    this.loteForm = {
      dueno: '',
      lote: 0,
      manzana: 0,
      id_servicio_polo: 0
    };
  }

  showMessage(message: string, type: 'success' | 'error'): void {
    this.message = message;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
    }, 5000);
  }

  // EMPRESAS
  openEmpresaForm(empresa?: Empresa): void {
    if (empresa) {
      this.editingEmpresa = empresa;
      this.empresaForm = { ...empresa };
    } else {
      this.editingEmpresa = null;
      this.resetForms();
    }
    this.showEmpresaForm = true;
  }

  onSubmitEmpresa(): void {
    this.loading = true;
    
    if (this.editingEmpresa) {
      // Actualizar
      const updateData: EmpresaUpdate = {
        nombre: this.empresaForm.nombre,
        rubro: this.empresaForm.rubro
      };
      
      this.adminPoloService.updateEmpresa(this.editingEmpresa.cuil, updateData).subscribe({
        next: (empresa) => {
          this.showMessage('Empresa actualizada exitosamente', 'success');
          this.resetForms();
          this.loadData();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage('Error al actualizar empresa: ' + (error.error?.detail || error.message), 'error');
          this.loading = false;
        }
      });
    } else {
      // Crear
      this.adminPoloService.createEmpresa(this.empresaForm).subscribe({
        next: (empresa) => {
          this.showMessage('Empresa creada exitosamente', 'success');
          this.empresas.push(empresa);
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage('Error al crear empresa: ' + (error.error?.detail || error.message), 'error');
          this.loading = false;
        }
      });
    }
  }

  deleteEmpresa(cuil: number): void {
    if (confirm('¿Está seguro de que desea eliminar esta empresa?')) {
      this.adminPoloService.deleteEmpresa(cuil).subscribe({
        next: () => {
          this.showMessage('Empresa eliminada exitosamente', 'success');
          this.empresas = this.empresas.filter(e => e.cuil !== cuil);
        },
        error: (error) => {
          this.showMessage('Error al eliminar empresa: ' + (error.error?.detail || error.message), 'error');
        }
      });
    }
  }

  // USUARIOS
  openUsuarioForm(usuario?: Usuario): void {
    if (usuario) {
      this.editingUsuario = usuario;
      this.usuarioForm = {
        email: usuario.email,
        nombre: usuario.nombre,
        password: '', // Siempre vacío para edición
        estado: usuario.estado,
        cuil: usuario.cuil,
        id_rol: 0 // Se mantendrá el rol existente
      };
    } else {
      this.editingUsuario = null;
      this.usuarioForm = {
        email: '',
        nombre: '',
        password: '',
        estado: true,
        cuil: 0,
        id_rol: 0
      };
    }
    this.showUsuarioForm = true;
  }

  onSubmitUsuario(): void {
    this.loading = true;
    
    if (this.editingUsuario) {
      // Actualizar
      const updateData: UsuarioUpdate = {
        password: this.usuarioForm.password || undefined,
        estado: this.usuarioForm.estado
      };
      
      this.adminPoloService.updateUser(this.editingUsuario.id_usuario, updateData).subscribe({
        next: (usuario) => {
          this.showMessage('Usuario actualizado exitosamente', 'success');
          this.resetForms();
          this.loadData();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage('Error al actualizar usuario: ' + (error.error?.detail || error.message), 'error');
          this.loading = false;
        }
      });
    } else {
      // Crear - validar que todos los campos requeridos estén presentes
      if (!this.usuarioForm.password) {
        this.showMessage('La contraseña es requerida para crear un nuevo usuario', 'error');
        this.loading = false;
        return;
      }
      
      this.adminPoloService.createUser(this.usuarioForm).subscribe({
        next: (usuario) => {
          this.showMessage('Usuario creado exitosamente', 'success');
          this.usuarios.push(usuario);
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage('Error al crear usuario: ' + (error.error?.detail || error.message), 'error');
          this.loading = false;
        }
      });
    }
  }

  deleteUsuario(userId: string): void {
    if (confirm('¿Está seguro de que desea inhabilitar este usuario?')) {
      this.adminPoloService.deleteUser(userId).subscribe({
        next: () => {
          this.showMessage('Usuario inhabilitado exitosamente', 'success');
          this.usuarios = this.usuarios.filter(u => u.id_usuario !== userId);
        },
        error: (error) => {
          this.showMessage('Error al inhabilitar usuario: ' + (error.error?.detail || error.message), 'error');
        }
      });
    }
  }

  // SERVICIOS DEL POLO
  openServicioPoloForm(): void {
    this.showServicioPoloForm = true;
  }

  onSubmitServicioPolo(): void {
    this.loading = true;
    
    this.adminPoloService.createServicioPolo(this.servicioPoloForm).subscribe({
      next: (servicio) => {
        this.showMessage('Servicio del polo creado exitosamente', 'success');
        this.serviciosPolo.push(servicio);
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.showMessage('Error al crear servicio del polo: ' + (error.error?.detail || error.message), 'error');
        this.loading = false;
      }
    });
  }

  deleteServicioPolo(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este servicio del polo?')) {
      this.adminPoloService.deleteServicioPolo(id).subscribe({
        next: () => {
          this.showMessage('Servicio del polo eliminado exitosamente', 'success');
          this.serviciosPolo = this.serviciosPolo.filter(s => s.id_servicio_polo !== id);
        },
        error: (error) => {
          this.showMessage('Error al eliminar servicio del polo: ' + (error.error?.detail || error.message), 'error');
        }
      });
    }
  }

  // LOTES
  openLoteForm(): void {
    this.showLoteForm = true;
  }

  onSubmitLote(): void {
    this.loading = true;
    
    this.adminPoloService.createLote(this.loteForm).subscribe({
      next: (lote) => {
        this.showMessage('Lote creado exitosamente', 'success');
        this.lotes.push(lote);
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.showMessage('Error al crear lote: ' + (error.error?.detail || error.message), 'error');
        this.loading = false;
      }
    });
  }

  deleteLote(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este lote?')) {
      this.adminPoloService.deleteLote(id).subscribe({
        next: () => {
          this.showMessage('Lote eliminado exitosamente', 'success');
          this.lotes = this.lotes.filter(l => l.id_lotes !== id);
        },
        error: (error) => {
          this.showMessage('Error al eliminar lote: ' + (error.error?.detail || error.message), 'error');
        }
      });
    }
  }

  getRoleName(id: number): string {
    const rol = this.roles.find(r => r.id_rol === id);
    return rol ? rol.tipo_rol : 'Desconocido';
  }
}