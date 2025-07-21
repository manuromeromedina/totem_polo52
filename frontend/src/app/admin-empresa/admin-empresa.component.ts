import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import {
  AdminEmpresaService,
  Vehiculo,
  VehiculoCreate,
  Servicio,
  ServicioCreate,
  ServicioUpdate,
  Contacto,
  ContactoCreate,
  EmpresaDetail,
  EmpresaSelfUpdate,
  UserUpdateCompany,
  TipoVehiculo,
  TipoServicio,
  TipoContacto,
  TipoServicioPolo,
} from './admin-empresa.service';
import { LogoutButtonComponent } from '../shared/logout-button/logout-button.component';

@Component({
  selector: 'app-empresa-me',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LogoutButtonComponent],
  templateUrl: './admin-empresa.component.html',
  styleUrls: ['./admin-empresa.component.css'],
})
export class EmpresaMeComponent implements OnInit {
  activeTab = 'perfil';

  // Datos de la empresa
  empresaData: EmpresaDetail | null = null;

  // Formularios
  showPasswordForm = false;
  showVehiculoForm = false;
  showServicioForm = false;
  showContactoForm = false;
  showEmpresaEditForm = false;

  // Estados de edición
  editingVehiculo: Vehiculo | null = null;
  editingServicio: Servicio | null = null;
  editingContacto: Contacto | null = null;

  // Formularios
  passwordForm = {
    password: '',
    confirmPassword: '',
  };

  vehiculoForm: VehiculoCreate = {
    id_tipo_vehiculo: 1,
    horarios: '',
    frecuencia: '',
    datos: {}, // Asegúrate de que sea un objeto vacío válido
  };

  servicioForm: ServicioCreate = {
    datos: {},
    id_tipo_servicio: 1,
  };

  contactoForm: ContactoCreate = {
    id_tipo_contacto: 1,
    nombre: '',
    telefono: '',
    datos: {},
    direccion: '',
    id_servicio_polo: 1,
  };

  empresaEditForm: EmpresaSelfUpdate = {
    cant_empleados: 0,
    observaciones: '',
    horario_trabajo: '',
  };

  // Estados
  loading = false;
  loadingTipos = false;
  message = '';
  messageType: 'success' | 'error' = 'success';

  // Tipos desde la BD
  tiposVehiculo: TipoVehiculo[] = [];
  tiposServicio: TipoServicio[] = [];
  tiposContacto: TipoContacto[] = [];
  tiposServicioPolo: TipoServicioPolo[] = [];

  constructor(private adminEmpresaService: AdminEmpresaService) {}

  ngOnInit(): void {
    this.loadTipos();
    this.loadEmpresaData();
  }

  setActiveTab(tab: string): void {
    this.activeTab = tab;
    this.resetForms();
  }

  loadEmpresaData(): void {
    this.loading = true;
    this.adminEmpresaService.getMyCompanyDetails().subscribe({
      next: (data) => {
        this.empresaData = data;
        this.empresaEditForm = {
          cant_empleados: data.cant_empleados,
          observaciones: data.observaciones || '',
          horario_trabajo: data.horario_trabajo,
        };
        this.loading = false;
      },
      error: (error) => {
        this.showMessage(
          'Error al cargar datos de la empresa: ' +
            (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  resetForms(): void {
    this.showPasswordForm = false;
    this.showVehiculoForm = false;
    this.showServicioForm = false;
    this.showContactoForm = false;
    this.showEmpresaEditForm = false;
    this.editingVehiculo = null;
    this.editingServicio = null;
    this.editingContacto = null;
    this.message = '';

    this.passwordForm = { password: '', confirmPassword: '' };
    this.vehiculoForm = {
      id_tipo_vehiculo: 1,
      horarios: '',
      frecuencia: '',
      datos: {},
    };
    this.servicioForm = { datos: {}, id_tipo_servicio: 1 };
    this.contactoForm = {
      id_tipo_contacto: 1,
      nombre: '',
      telefono: '',
      datos: {
        pagina_web: '',
        correo: '',
        redes_sociales: '',
      },
      direccion: '',
      id_servicio_polo: 1,
    };
  }

  showMessage(message: string, type: 'success' | 'error'): void {
    this.message = message;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
    }, 5000);
  }

  // PASSWORD
  openPasswordForm(): void {
    this.showPasswordForm = true;
  }
  onSubmitPassword(): void {
    this.loading = true;
    this.adminEmpresaService.changePasswordRequest().subscribe({
      next: () => {
        this.showMessage(
          'Se ha enviado un enlace de cambio de contraseña a tu email',
          'success'
        );
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.showMessage(
          'Error al solicitar cambio de contraseña: ' +
            (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  // EMPRESA EDIT
  openEmpresaEditForm(): void {
    this.showEmpresaEditForm = true;
  }

  onSubmitEmpresaEdit(): void {
    this.loading = true;
    this.adminEmpresaService.updateMyCompany(this.empresaEditForm).subscribe({
      next: () => {
        this.showMessage(
          'Datos de empresa actualizados exitosamente',
          'success'
        );
        this.loadEmpresaData();
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.showMessage(
          'Error al actualizar empresa: ' +
            (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  // VEHÍCULOS
  openVehiculoForm(vehiculo?: Vehiculo): void {
    if (vehiculo) {
      this.editingVehiculo = vehiculo;
      this.vehiculoForm = {
        id_tipo_vehiculo: vehiculo.id_tipo_vehiculo,
        horarios: vehiculo.horarios,
        frecuencia: vehiculo.frecuencia,
        datos: vehiculo.datos,
      };
    } else {
      this.editingVehiculo = null;
      this.vehiculoForm = {
        id_tipo_vehiculo: 1,
        horarios: '',
        frecuencia: '',
        datos: {},
      };
    }
    this.showVehiculoForm = true;
  }

  onSubmitVehiculo(): void {
    this.loading = true;

    if (this.editingVehiculo) {
      // Actualizar
      this.adminEmpresaService
        .updateVehiculo(this.editingVehiculo.id_vehiculo, this.vehiculoForm)
        .subscribe({
          next: () => {
            this.showMessage('Vehículo actualizado exitosamente', 'success');
            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.showMessage(
              'Error al actualizar vehículo: ' +
                (error.error?.detail || error.message),
              'error'
            );
            this.loading = false;
          },
        });
    } else {
      // Crear
      this.adminEmpresaService.createVehiculo(this.vehiculoForm).subscribe({
        next: () => {
          this.showMessage('Vehículo creado exitosamente', 'success');
          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage(
            'Error al crear vehículo: ' +
              (error.error?.detail || error.message),
            'error'
          );
          this.loading = false;
        },
      });
    }
  }

  deleteVehiculo(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este vehículo?')) {
      this.adminEmpresaService.deleteVehiculo(id).subscribe({
        next: () => {
          this.showMessage('Vehículo eliminado exitosamente', 'success');
          this.loadEmpresaData();
        },
        error: (error) => {
          this.showMessage(
            'Error al eliminar vehículo: ' +
              (error.error?.detail || error.message),
            'error'
          );
        },
      });
    }
  }

  // SERVICIOS
  openServicioForm(servicio?: Servicio): void {
    if (servicio) {
      this.editingServicio = servicio;
      this.servicioForm = {
        id_tipo_servicio: servicio.id_tipo_servicio,
        datos: { ...servicio.datos }, // Clonamos para no mutar directamente
      };
    } else {
      this.editingServicio = null;
      this.servicioForm = {
        id_tipo_servicio: 1,
        datos: {},
      };
    }

    // Llamamos para inicializar datos según tipo
    this.onTipoServicioChange();

    // Si estamos editando, sobreescribimos con los datos reales para no perderlos
    if (this.editingServicio) {
      this.servicioForm.datos = { ...servicio?.datos };
    }

    this.showServicioForm = true;
  }

  onSubmitServicio(): void {
    this.loading = true;

    if (this.editingServicio) {
      // Actualizar
      const updateData: ServicioUpdate = {
        datos: this.servicioForm.datos,
        id_tipo_servicio: this.servicioForm.id_tipo_servicio,
      };

      this.adminEmpresaService
        .updateServicio(this.editingServicio.id_servicio, updateData)
        .subscribe({
          next: () => {
            this.showMessage('Servicio actualizado exitosamente', 'success');
            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.showMessage(
              'Error al actualizar servicio: ' +
                (error.error?.detail || error.message),
              'error'
            );
            this.loading = false;
          },
        });
    } else {
      // Crear
      this.adminEmpresaService.createServicio(this.servicioForm).subscribe({
        next: () => {
          this.showMessage('Servicio creado exitosamente', 'success');
          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage(
            'Error al crear servicio: ' +
              (error.error?.detail || error.message),
            'error'
          );
          this.loading = false;
        },
      });
    }
  }

  deleteServicio(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este servicio?')) {
      this.adminEmpresaService.deleteServicio(id).subscribe({
        next: () => {
          this.showMessage('Servicio eliminado exitosamente', 'success');
          this.loadEmpresaData();
        },
        error: (error) => {
          this.showMessage(
            'Error al eliminar servicio: ' +
              (error.error?.detail || error.message),
            'error'
          );
        },
      });
    }
  }

  // Método que se llama al cambiar el tipo de servicio en el select
  onTipoServicioChange(): void {
    // Reseteamos los datos para evitar datos residuales al cambiar tipo
    this.servicioForm.datos = {};

    // Inicializar con valores vacíos o por defecto según el tipo seleccionado
    switch (this.servicioForm.id_tipo_servicio) {
      case 1: // Agua
        this.servicioForm.datos = {
          biofiltro: '',
          tratamiento_aguas_grises: '',
        };
        break;
      case 2: // Espacios verdes
        this.servicioForm.datos = {
          abierto: '',
          m2: null,
        };
        break;
      case 3: // Internet
        this.servicioForm.datos = {
          tipo: '',
          proveedor: '',
        };
        break;
      case 4: // Residuos
        this.servicioForm.datos = {
          tipo: '',
          cantidad: null,
        };
        break;
      default:
        this.servicioForm.datos = {};
    }
  }

  // CONTACTOS
  // CONTACTOS - VERSIÓN CORREGIDA
  openContactoForm(contacto?: Contacto): void {
    if (contacto) {
      this.editingContacto = contacto;
      this.contactoForm = {
        id_tipo_contacto: contacto.id_tipo_contacto,
        nombre: contacto.nombre,
        telefono: contacto.telefono || '',
        datos: contacto.datos || {
          pagina_web: '',
          correo: '',
          redes_sociales: '',
          direccion: '', // 👈 Agregamos dirección al JSON datos
        },
        direccion: contacto.direccion || '',
        id_servicio_polo: contacto.id_servicio_polo,
      };
    } else {
      this.editingContacto = null;
      this.contactoForm = {
        id_tipo_contacto: 1,
        nombre: '',
        telefono: '',
        datos: {
          pagina_web: '',
          correo: '',
          redes_sociales: '',
          direccion: '', // 👈 Inicializamos dirección en datos
        },
        direccion: '',
        id_servicio_polo: 1,
      };
    }
    this.showContactoForm = true;
    this.onTipoContactoChange(); // 👈 fuerza la recarga dinámica de campos
  }

  onTipoContactoChange(): void {
    console.log(
      'Tipo contacto:',
      this.contactoForm.id_tipo_contacto,
      typeof this.contactoForm.id_tipo_contacto
    );
    const tipo = Number(this.contactoForm.id_tipo_contacto);

    if (tipo === 1) {
      // Para tipo comercial, asegurar que todos los campos estén en datos
      this.contactoForm.datos = {
        pagina_web: this.contactoForm.datos.pagina_web || '',
        correo: this.contactoForm.datos.correo || '',
        redes_sociales: this.contactoForm.datos.redes_sociales || '',
        direccion:
          this.contactoForm.direccion ||
          this.contactoForm.datos.direccion ||
          '', // 👈 Sincronizar dirección
      };
    } else {
      this.contactoForm.datos = {};
    }
  }

  onSubmitContacto(): void {
    this.loading = true;

    // 👈 VALIDACIÓN ADICIONAL ANTES DE ENVIAR
    if (this.esTipoComercial()) {
      // Asegurar que la dirección esté en ambos lugares
      if (this.contactoForm.direccion) {
        this.contactoForm.datos.direccion = this.contactoForm.direccion;
      } else if (this.contactoForm.datos.direccion) {
        this.contactoForm.direccion = this.contactoForm.datos.direccion;
      }

      // Validar que los campos requeridos para comercial estén presentes
      if (
        !this.contactoForm.datos.direccion ||
        this.contactoForm.datos.direccion.trim() === ''
      ) {
        this.showMessage(
          'La dirección es requerida para contactos comerciales',
          'error'
        );
        this.loading = false;
        return;
      }
    }

    if (this.editingContacto) {
      // Actualizar
      this.adminEmpresaService
        .updateContacto(this.editingContacto.id_contacto, this.contactoForm)
        .subscribe({
          next: () => {
            this.showMessage('Contacto actualizado exitosamente', 'success');
            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.showMessage(
              'Error al actualizar contacto: ' +
                (error.error?.detail || error.message),
              'error'
            );
            this.loading = false;
          },
        });
    } else {
      // Crear
      this.adminEmpresaService.createContacto(this.contactoForm).subscribe({
        next: () => {
          this.showMessage('Contacto creado exitosamente', 'success');
          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage(
            'Error al crear contacto: ' +
              (error.error?.detail || error.message),
            'error'
          );
          this.loading = false;
        },
      });
    }
  }

  // 👈 MÉTODO ADICIONAL PARA SINCRONIZAR DIRECCIÓN
  onDireccionChange(): void {
    if (this.esTipoComercial()) {
      this.contactoForm.datos.direccion = this.contactoForm.direccion;
    }
  }

  deleteContacto(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este contacto?')) {
      this.adminEmpresaService.deleteContacto(id).subscribe({
        next: () => {
          this.showMessage('Contacto eliminado exitosamente', 'success');
          this.loadEmpresaData();
        },
        error: (error) => {
          this.showMessage(
            'Error al eliminar contacto: ' +
              (error.error?.detail || error.message),
            'error'
          );
        },
      });
    }
  }

  esTipoComercial(): boolean {
    return this.contactoForm.id_tipo_contacto === 1;
  }

  // Métodos helper para servicios polo
  getTipoServicioPoloName(id: number): string {
    const tipo = this.tiposServicioPolo.find(
      (t) => t.id_tipo_servicio_polo === id
    );
    return tipo ? tipo.tipo : 'Sin tipo definido';
  }

  get tieneServiciosPolo(): boolean {
    return (
      Array.isArray(this.empresaData?.servicios_polo) &&
      this.empresaData.servicios_polo.length > 0
    );
  }

  getStatusClass(activo: boolean): string {
    return activo ? 'status-active' : 'status-inactive';
  }

  formatDate(dateString: string): string {
    if (!dateString) return 'Sin fecha';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
    } catch (error) {
      return 'Fecha inválida';
    }
  }

  formatDatos(datos: any): string {
    if (!datos || Object.keys(datos).length === 0) {
      return 'Sin datos adicionales';
    }

    try {
      const dataString = JSON.stringify(datos);
      return dataString.length > 50
        ? dataString.substring(0, 50) + '...'
        : dataString;
    } catch (error) {
      return 'Error al procesar datos';
    }
  }

  getTotalLotes(): number {
    if (!this.empresaData?.servicios_polo) return 0;

    return this.empresaData.servicios_polo.reduce((total, servicio) => {
      return total + (servicio.lotes ? servicio.lotes.length : 0);
    }, 0);
  }

  getTipoVehiculoName(id: number): string {
    const tipo = this.tiposVehiculo.find((t) => t.id_tipo_vehiculo === id);
    return tipo ? tipo.tipo : 'Desconocido';
  }

  getTipoServicioName(id: number): string {
    const tipo = this.tiposServicio.find((t) => t.id_tipo_servicio === id);
    return tipo ? tipo.tipo : 'Desconocido';
  }

  getTipoContactoName(id: number): string {
    const tipo = this.tiposContacto.find((t) => t.id_tipo_contacto === id);
    return tipo ? tipo.tipo : 'Desconocido';
  }

  // Agregar este método
  loadTipos(): void {
    // Cargar tipos de servicio del polo
    this.adminEmpresaService.getTiposServicioPolo().subscribe({
      next: (tipos) => {
        this.tiposServicioPolo = tipos;
      },
      error: (error) => {
        console.error('Error loading tipos servicio polo:', error);
      },
    });

    // Cargar tipos de vehículo
    this.adminEmpresaService.getTiposVehiculo().subscribe({
      next: (tipos) => {
        this.tiposVehiculo = tipos;
      },
      error: (error) => {
        console.error('Error loading tipos vehículo:', error);
      },
    });

    // Cargar tipos de servicio
    this.adminEmpresaService.getTiposServicio().subscribe({
      next: (tipos) => {
        this.tiposServicio = tipos;
      },
      error: (error) => {
        console.error('Error loading tipos servicio:', error);
      },
    });

    // Cargar tipos de contacto
    this.adminEmpresaService.getTiposContacto().subscribe({
      next: (tipos) => {
        this.tiposContacto = tipos;
      },
      error: (error) => {
        console.error('Error loading tipos contacto:', error);
      },
    });
  }
}
