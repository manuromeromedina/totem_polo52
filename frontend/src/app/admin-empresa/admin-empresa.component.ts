import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxJsonViewerModule } from 'ngx-json-viewer';

import { AuthenticationService } from '../auth/auth.service';

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
import { PasswordChangeModalComponent } from '../shared/password-change-modal/password-change-modal.component';

// Interfaces para manejo de errores
interface FormError {
  field: string;
  message: string;
  type: 'required' | 'invalid' | 'duplicate' | 'server' | 'validation';
}

interface ErrorResponse {
  detail?: string;
  message?: string;
  errors?: { [key: string]: string[] };
  status?: number;
}

@Component({
  selector: 'app-empresa-me',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    LogoutButtonComponent,
    NgxJsonViewerModule,
    PasswordChangeModalComponent,
  ],
  templateUrl: './admin-empresa.component.html',
  styleUrls: ['./admin-empresa.component.css'],
})
export class EmpresaMeComponent implements OnInit {
  // pestañas
  activeTab:
    | 'resumen'
    | 'perfil'
    | 'vehiculos'
    | 'servicios'
    | 'contactos'
    | 'serviciosPolo'
    | 'config' = 'resumen';

  // límite de ítems en “Actividad Reciente”
  private readonly MAX_ACTIVIDADES = 6;

  // Datos de la empresa
  empresaData: EmpresaDetail | null = null;

  // Formularios / modales
  showPasswordForm = false;
  showVehiculoForm = false;
  showServicioForm = false;
  showContactoForm = false;
  showEmpresaEditForm = false;
  showPasswordModal = false; // ← requerido por la plantilla

  // Estados de edición
  editingVehiculo: Vehiculo | null = null;
  editingServicio: Servicio | null = null;
  editingContacto: Contacto | null = null;

  // PROPIEDADES PARA CONTROL DE CAMBIOS
  private initialForms: { [key: string]: any } = {};
  private hasUnsavedChanges: { [key: string]: boolean } = {};

  // Formularios
  passwordForm = {
    password: '',
    confirmPassword: '',
  };

  vehiculoForm: VehiculoCreate = {
    id_tipo_vehiculo: 1,
    horarios: '',
    frecuencia: '',
    datos: {},
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

  // Sistema de errores mejorado
  formErrors: { [key: string]: FormError[] } = {};
  showErrorDetails = false;

  // Tipos desde la BD
  tiposVehiculo: TipoVehiculo[] = [];
  tiposServicio: TipoServicio[] = [];
  tiposContacto: TipoContacto[] = [];
  tiposServicioPolo: TipoServicioPolo[] = [];

  // PROPIEDADES PARA BÚSQUEDA
  vehiculoSearchTerm: string = '';
  servicioSearchTerm: string = '';
  contactoSearchTerm: string = '';
  servicioPoloSearchTerm: string = '';

  // Arrays filtrados
  filteredVehiculos: Vehiculo[] = [];
  filteredServicios: Servicio[] = [];
  filteredContactos: Contacto[] = [];
  filteredServiciosPolo: any[] = [];

  // Expanded rows
  expandedRows = new Set<string>();

  constructor(
    private adminEmpresaService: AdminEmpresaService,
    private authService: AuthenticationService
  ) {}
  public isDarkMode: boolean = false;

  ngOnInit(): void {
    this.loadTipos();
    this.loadEmpresaData();

    const savedTheme = localStorage.getItem('theme');
    this.isDarkMode = savedTheme === 'dark';

    if (this.isDarkMode) {
      document.body.style.background = '#1a1a1a';
      document.documentElement.style.background = '#1a1a1a';
    }
  }

  toggleDarkMode(): void {
    this.isDarkMode = !this.isDarkMode;
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');

    const body = document.body;
    const html = document.documentElement;

    if (this.isDarkMode) {
      body.style.background = '#1a1a1a';
      body.style.margin = '0';
      body.style.padding = '0';
      html.style.background = '#1a1a1a';
    } else {
      body.style.background = '#f8f9fa';
      html.style.background = '#ffffff';
    }
  }

  // TIPADO CORRECTO: la unión de literales
  setActiveTab(tab: EmpresaMeComponent['activeTab']): void {
    this.activeTab = tab;
    this.closeAllFormsWithoutConfirmation();
    this.applyFilters();
  }

  // MÉTODO PARA CERRAR TODOS LOS FORMULARIOS SIN CONFIRMACIÓN
  private closeAllFormsWithoutConfirmation(): void {
    this.showPasswordForm = false;
    this.showVehiculoForm = false;
    this.showServicioForm = false;
    this.showContactoForm = false;
    this.showEmpresaEditForm = false;
    this.editingVehiculo = null;
    this.editingServicio = null;
    this.editingContacto = null;

    this.formErrors = {};
    this.initialForms = {};
    this.hasUnsavedChanges = {};
  }

  // ===== Control de cambios =====
  private saveInitialFormState(formName: string, formData: any): void {
    this.initialForms[formName] = JSON.parse(JSON.stringify(formData));
    this.hasUnsavedChanges[formName] = false;
  }

  private hasFormChanged(formName: string, currentFormData: any): boolean {
    if (!this.initialForms[formName]) return false;
    const initial = JSON.stringify(this.initialForms[formName]);
    const current = JSON.stringify(currentFormData);
    return initial !== current;
  }

  private checkUnsavedChanges(formName: string, currentFormData: any): boolean {
    return this.hasFormChanged(formName, currentFormData);
  }

  private restoreOriginalFormData(formName: string): void {
    if (!this.initialForms[formName]) return;
    const originalData = JSON.parse(
      JSON.stringify(this.initialForms[formName])
    );
    switch (formName) {
      case 'vehiculo':
        this.vehiculoForm = {
          id_tipo_vehiculo: originalData.id_tipo_vehiculo,
          horarios: originalData.horarios,
          frecuencia: originalData.frecuencia,
          datos: { ...originalData.datos },
        };
        break;
      case 'servicio':
        this.servicioForm = {
          id_tipo_servicio: originalData.id_tipo_servicio,
          datos: { ...originalData.datos },
        };
        break;
      case 'contacto':
        this.contactoForm = {
          id_tipo_contacto: originalData.id_tipo_contacto,
          nombre: originalData.nombre,
          telefono: originalData.telefono,
          direccion: originalData.direccion,
          id_servicio_polo: originalData.id_servicio_polo,
          datos: { ...originalData.datos },
        };
        break;
      case 'empresa':
        this.empresaEditForm = {
          cant_empleados: originalData.cant_empleados,
          observaciones: originalData.observaciones,
          horario_trabajo: originalData.horario_trabajo,
        };
        break;
      case 'password':
        this.passwordForm = {
          password: originalData.password,
          confirmPassword: originalData.confirmPassword,
        };
        break;
    }
  }

  // ===== Métricas y actividad =====
  get vehiculosActivos(): number {
    return this.empresaData?.vehiculos?.length ?? 0;
  }
  get totalServicios(): number {
    return this.empresaData?.servicios?.length ?? 0;
  }
  get totalContactos(): number {
    return this.empresaData?.contactos?.length ?? 0;
  }
  get estaActiva(): boolean {
    return !!this.empresaData;
  }
  get desdeIngreso(): string {
    return this.formatMonthYear(this.empresaData?.fecha_ingreso);
  }

  actividadReciente: Array<{
    tipo: 'ok' | 'warn' | 'info';
    titulo: string;
    cuando: string; // HH:mm o "—" si no hay timestamp
  }> = [];

  // ——— Helper para “actividad reciente”
  private addActividad(
    tipo: 'ok' | 'warn' | 'info',
    titulo: string,
    cuando = this.formatTime(new Date())
  ) {
    this.actividadReciente.unshift({ tipo, titulo, cuando });
    this.actividadReciente = this.actividadReciente.slice(
      0,
      this.MAX_ACTIVIDADES
    );
  }

  // ====== ACTIVIDAD EN TIEMPO REAL ======
  private pushActivity(
    tipo: 'ok' | 'warn' | 'info',
    titulo: string,
    cuando: string = this.formatTime(new Date())
  ): void {
    this.actividadReciente.unshift({ tipo, titulo, cuando });
    this.actividadReciente = this.actividadReciente.slice(
      0,
      this.MAX_ACTIVIDADES
    );
  }

  /** reconstruye actividad desde los datos existentes */
  private buildActividadRecienteFromData(): void {
    this.actividadReciente = [];

    // Si el backend expone created_at/updated_at, lo mostramos; si no, “—”
    const getCuando = (anyItem: any): string => {
      if (anyItem?.updated_at || anyItem?.created_at) {
        const raw = anyItem.updated_at ?? anyItem.created_at;
        try {
          const d = new Date(raw);
          return this.formatTime(d);
        } catch {
          return '—';
        }
      }
      return '—';
    };

    const vs = [...(this.empresaData?.vehiculos ?? [])]
      .sort((a, b) => (b.id_vehiculo ?? 0) - (a.id_vehiculo ?? 0))
      .slice(0, 3);
    vs.forEach((v) =>
      this.actividadReciente.push({
        tipo: 'ok',
        titulo: `Vehículo ${this.getTipoVehiculoName(
          v.id_tipo_vehiculo
        )} registrado/actualizado`,
        cuando: getCuando(v),
      })
    );

    const ss = [...(this.empresaData?.servicios ?? [])]
      .sort((a, b) => (b.id_servicio ?? 0) - (a.id_servicio ?? 0))
      .slice(0, 3);
    ss.forEach((s) =>
      this.actividadReciente.push({
        tipo: 'info',
        titulo: `Servicio ${this.getTipoServicioName(
          s.id_tipo_servicio
        )} actualizado`,
        cuando: getCuando(s),
      })
    );

    const cs = [...(this.empresaData?.contactos ?? [])]
      .sort((a, b) => (b.id_contacto ?? 0) - (a.id_contacto ?? 0))
      .slice(0, 3);
    cs.forEach((c) =>
      this.actividadReciente.push({
        tipo: 'ok',
        titulo: `Contacto ${c.nombre} agregado/actualizado`,
        cuando: getCuando(c),
      })
    );

    // dejamos solo los últimos 6 (por si viene mucho histórico)
    this.actividadReciente = this.actividadReciente.slice(
      0,
      this.MAX_ACTIVIDADES
    );
  }

  // ===== Cancelación de formularios =====
  cancelForm(formName: string): void {
    let currentFormData: any;
    switch (formName) {
      case 'vehiculo':
        currentFormData = this.vehiculoForm;
        break;
      case 'servicio':
        currentFormData = this.servicioForm;
        break;
      case 'contacto':
        currentFormData = this.contactoForm;
        break;
      case 'empresa':
        currentFormData = this.empresaEditForm;
        break;
      case 'password':
        currentFormData = this.passwordForm;
        break;
      default:
        return;
    }
    const hasChanges = this.checkUnsavedChanges(formName, currentFormData);
    if (hasChanges) {
      const shouldDiscard = confirm(
        '¿Deseas descartar los cambios?\n\nSe perderán todos los cambios no guardados.'
      );
      if (!shouldDiscard) return;
      this.restoreOriginalFormData(formName);
    }
    this.closeFormWithoutConfirmation(formName);
  }

  private closeFormWithoutConfirmation(formName: string): void {
    switch (formName) {
      case 'vehiculo':
        this.showVehiculoForm = false;
        this.editingVehiculo = null;
        break;
      case 'servicio':
        this.showServicioForm = false;
        this.editingServicio = null;
        break;
      case 'contacto':
        this.showContactoForm = false;
        this.editingContacto = null;
        break;
      case 'empresa':
        this.showEmpresaEditForm = false;
        break;
      case 'password':
        this.showPasswordForm = false;
        break;
    }
    this.clearFormErrors(formName);
    delete this.initialForms[formName];
    delete this.hasUnsavedChanges[formName];
  }

  closeFormDirectly(formName: string): void {
    this.cancelForm(formName);
  }

  // ===== Filtros =====
  applyFilters(): void {
    switch (this.activeTab) {
      case 'vehiculos':
        this.filterVehiculos();
        break;
      case 'servicios':
        this.filterServicios();
        break;
      case 'contactos':
        this.filterContactos();
        break;
      case 'serviciosPolo':
        this.filterServiciosPolo();
        break;
    }
  }

  filterVehiculos(): void {
    if (!this.empresaData?.vehiculos) {
      this.filteredVehiculos = [];
      return;
    }
    if (!this.vehiculoSearchTerm.trim()) {
      this.filteredVehiculos = [...this.empresaData.vehiculos];
      return;
    }
    const term = this.vehiculoSearchTerm.toLowerCase().trim();
    this.filteredVehiculos = this.empresaData.vehiculos.filter(
      (vehiculo) =>
        this.getTipoVehiculoName(vehiculo.id_tipo_vehiculo)
          .toLowerCase()
          .includes(term) ||
        vehiculo.horarios.toLowerCase().includes(term) ||
        vehiculo.frecuencia.toLowerCase().includes(term) ||
        (vehiculo.datos.patente &&
          vehiculo.datos.patente.toLowerCase().includes(term)) ||
        (vehiculo.datos.carga &&
          vehiculo.datos.carga.toLowerCase().includes(term))
    );
  }

  clearVehiculoSearch(): void {
    this.vehiculoSearchTerm = '';
    this.filteredVehiculos = this.empresaData?.vehiculos
      ? [...this.empresaData.vehiculos]
      : [];
  }

  filterServicios(): void {
    if (!this.empresaData?.servicios) {
      this.filteredServicios = [];
      return;
    }
    if (!this.servicioSearchTerm.trim()) {
      this.filteredServicios = [...this.empresaData.servicios];
      return;
    }
    const term = this.servicioSearchTerm.toLowerCase().trim();
    this.filteredServicios = this.empresaData.servicios.filter(
      (servicio) =>
        this.getTipoServicioName(servicio.id_tipo_servicio)
          .toLowerCase()
          .includes(term) ||
        JSON.stringify(servicio.datos).toLowerCase().includes(term)
    );
  }

  clearServicioSearch(): void {
    this.servicioSearchTerm = '';
    this.filteredServicios = this.empresaData?.servicios
      ? [...this.empresaData.servicios]
      : [];
  }

  filterContactos(): void {
    if (!this.empresaData?.contactos) {
      this.filteredContactos = [];
      return;
    }
    if (!this.contactoSearchTerm.trim()) {
      this.filteredContactos = [...this.empresaData.contactos];
      return;
    }
    const term = this.contactoSearchTerm.toLowerCase().trim();
    this.filteredContactos = this.empresaData.contactos.filter(
      (contacto) =>
        contacto.nombre.toLowerCase().includes(term) ||
        this.getTipoContactoName(contacto.id_tipo_contacto)
          .toLowerCase()
          .includes(term) ||
        (contacto.telefono && contacto.telefono.toLowerCase().includes(term)) ||
        (contacto.direccion &&
          contacto.direccion.toLowerCase().includes(term)) ||
        (contacto.datos?.correo &&
          contacto.datos.correo.toLowerCase().includes(term)) ||
        (contacto.datos?.pagina_web &&
          contacto.datos.pagina_web.toLowerCase().includes(term))
    );
  }

  clearContactoSearch(): void {
    this.contactoSearchTerm = '';
    this.filteredContactos = this.empresaData?.contactos
      ? [...this.empresaData.contactos]
      : [];
  }

  filterServiciosPolo(): void {
    if (!this.empresaData?.servicios_polo) {
      this.filteredServiciosPolo = [];
      return;
    }
    if (!this.servicioPoloSearchTerm.trim()) {
      this.filteredServiciosPolo = [...this.empresaData.servicios_polo];
      return;
    }
    const term = this.servicioPoloSearchTerm.toLowerCase().trim();
    this.filteredServiciosPolo = this.empresaData.servicios_polo.filter(
      (servicio) =>
        (servicio.nombre && servicio.nombre.toLowerCase().includes(term)) ||
        this.getTipoServicioPoloName(servicio.id_tipo_servicio_polo)
          .toLowerCase()
          .includes(term) ||
        (servicio.horario && servicio.horario.toLowerCase().includes(term)) ||
        (servicio.propietario &&
          servicio.propietario.toLowerCase().includes(term))
    );
  }

  clearServicioPoloSearch(): void {
    this.servicioPoloSearchTerm = '';
    this.filteredServiciosPolo = this.empresaData?.servicios_polo
      ? [...this.empresaData.servicios_polo]
      : [];
  }

  // ===== Errores =====
  clearFormErrors(formName: string): void {
    this.formErrors[formName] = [];
  }
  getFieldErrors(formName: string, fieldName: string): FormError[] {
    const errors = this.formErrors[formName] || [];
    return errors.filter((error) => error.field === fieldName);
  }
  hasFieldError(formName: string, fieldName: string): boolean {
    return this.getFieldErrors(formName, fieldName).length > 0;
  }

  private handleError(error: any, formName: string, operation: string): void {
    console.error(`Error en ${operation}:`, error);
    this.clearFormErrors(formName);
    let errorMessages: FormError[] = [];

    if (error.status === 0) {
      errorMessages.push({
        field: 'general',
        message: 'Error de conexión. Verifique su conexión a internet.',
        type: 'server',
      });
    } else if (error.status === 401) {
      errorMessages.push({
        field: 'general',
        message: 'Sesión expirada. Por favor, inicie sesión nuevamente.',
        type: 'server',
      });
    } else if (error.status === 403) {
      errorMessages.push({
        field: 'general',
        message: 'No tiene permisos para realizar esta acción.',
        type: 'server',
      });
    } else if (error.status === 404) {
      errorMessages.push({
        field: 'general',
        message: 'El recurso solicitado no fue encontrado.',
        type: 'server',
      });
    } else if (error.status === 422) {
      const errorResponse: ErrorResponse = error.error;
      if (errorResponse.errors) {
        Object.keys(errorResponse.errors).forEach((field) => {
          const fieldErrors = errorResponse.errors![field];
          fieldErrors.forEach((message) => {
            errorMessages.push({
              field: field,
              message: this.translateFieldError(field, message, formName),
              type: 'validation',
            });
          });
        });
      } else if (errorResponse.detail) {
        errorMessages.push({
          field: 'general',
          message: this.translateGenericError(errorResponse.detail, formName),
          type: 'validation',
        });
      }
    } else if (error.status === 400) {
      const errorDetail = error.error?.detail || 'Datos inválidos';
      errorMessages.push({
        field: 'general',
        message: this.translateGenericError(errorDetail, formName),
        type: 'validation',
      });
    } else if (error.status === 500) {
      errorMessages.push({
        field: 'general',
        message: 'Error interno del servidor. Intente más tarde.',
        type: 'server',
      });
    } else {
      const detail =
        error.error?.detail || error.message || 'Error desconocido';
      errorMessages.push({
        field: 'general',
        message: this.translateGenericError(detail, formName),
        type: 'server',
      });
    }

    this.formErrors[formName] = errorMessages;

    const generalError = errorMessages.find((e) => e.field === 'general');
    if (generalError) {
      this.showMessage(generalError.message, 'error');
    } else {
      this.showMessage(
        `Error en ${operation}. Revise los campos marcados.`,
        'error'
      );
    }
  }

  private translateFieldError(
    field: string,
    message: string,
    formName: string
  ): string {
    const translations: { [key: string]: { [key: string]: string } } = {
      vehiculo: {
        id_tipo_vehiculo: 'El tipo de vehículo es requerido',
        horarios: 'Los horarios son requeridos (formato: HH:MM - HH:MM)',
        frecuencia: 'La frecuencia es requerida',
        'datos.cantidad': 'La cantidad debe ser mayor a 0',
        'datos.patente':
          'La patente debe tener formato válido (ABC123 o AB123CD)',
        'datos.carga': 'Seleccione un tipo de carga válido',
        'datos.m2': 'Los metros cuadrados deben ser mayor a 0',
      },
      servicio: {
        id_tipo_servicio: 'El tipo de servicio es requerido',
        'datos.biofiltro': 'Debe especificar si tiene biofiltro',
        'datos.tratamiento_aguas_grises':
          'Debe especificar el tratamiento de aguas grises',
        'datos.abierto': 'Debe especificar si está abierto al público',
        'datos.m2': 'Los metros cuadrados son requeridos y deben ser mayor a 0',
        'datos.tipo': 'El tipo es requerido',
        'datos.proveedor': 'El proveedor es requerido',
        'datos.cantidad': 'La cantidad es requerida y debe ser mayor a 0',
      },
      contacto: {
        nombre: 'El nombre es requerido (mínimo 2 caracteres)',
        id_tipo_contacto: 'El tipo de contacto es requerido',
        telefono: 'El teléfono debe tener formato válido',
        direccion: 'La dirección es requerida para contactos comerciales',
        id_servicio_polo: 'El ID del servicio polo es requerido',
        'datos.pagina_web':
          'La página web debe tener formato válido (https://)',
        'datos.correo': 'El correo debe tener formato válido',
        'datos.redes_sociales':
          'Las redes sociales son requeridas para contactos comerciales',
      },
      empresa: {
        cant_empleados: 'La cantidad de empleados debe ser mayor a 0',
        horario_trabajo: 'El horario de trabajo es requerido',
        observaciones: 'Las observaciones no pueden exceder 500 caracteres',
      },
      password: {
        password: 'La contraseña debe tener al menos 6 caracteres',
        email: 'El email no fue encontrado en el sistema',
      },
    };

    const formTranslations = translations[formName];
    if (formTranslations && formTranslations[field]) {
      return formTranslations[field];
    }

    const genericTranslations: { [key: string]: string } = {
      required: 'Este campo es requerido',
      invalid: 'El formato de este campo es inválido',
      min_length: 'Este campo es muy corto',
      max_length: 'Este campo es muy largo',
      email: 'El formato del email es inválido',
      url: 'El formato de la URL es inválido',
      number: 'Debe ser un número válido',
    };

    return genericTranslations[message] || message;
  }

  private translateGenericError(detail: string, formName: string): string {
    const translations: { [key: string]: string } = {
      'Ya existe un vehículo con esa patente':
        'Ya existe un vehículo registrado con esa patente',
      'Ya existe un contacto con ese nombre':
        'Ya existe un contacto registrado con ese nombre',
      'Usuario no encontrado': 'Usuario no encontrado en el sistema',
      'Email no registrado': 'El email no está registrado en el sistema',
      'Credenciales inválidas': 'Usuario o contraseña incorrectos',
      'Token inválido':
        'La sesión ha expirado, por favor inicie sesión nuevamente',
      'Servicio no encontrado': 'El servicio solicitado no existe',
      'Vehículo no encontrado': 'El vehículo solicitado no existe',
      'Contacto no encontrado': 'El contacto solicitado no existe',
      'Empresa no encontrada': 'La empresa no fue encontrada',
      'Rol inválido': 'El rol especificado no es válido',
      'Acceso denegado': 'No tiene permisos para realizar esta acción',
      'Datos inválidos': 'Los datos enviados contienen errores',
    };
    return translations[detail] || detail;
  }

  // ===== Carga de datos =====
  loadEmpresaData(): void {
    this.loading = true;
    this.clearFormErrors('general');

    this.adminEmpresaService.getMyCompanyDetails().subscribe({
      next: (data) => {
        this.empresaData = data;
        this.empresaEditForm = {
          cant_empleados: data.cant_empleados,
          observaciones: data.observaciones || '',
          horario_trabajo: data.horario_trabajo,
        };

        this.filteredVehiculos = [...(data.vehiculos || [])];
        this.filteredServicios = [...(data.servicios || [])];
        this.filteredContactos = [...(data.contactos || [])];
        this.filteredServiciosPolo = [...(data.servicios_polo || [])];

        this.buildActividadRecienteFromData();
        this.loading = false;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar datos de la empresa');
        this.loading = false;
      },
    });
  }

  // accesos rápidos
  goTo(tab: EmpresaMeComponent['activeTab']) {
    this.setActiveTab(tab);
  }
  quickAddVehiculo() {
    this.setActiveTab('vehiculos');
    this.openVehiculoForm();
  }
  quickAddServicio() {
    this.setActiveTab('servicios');
    this.openServicioForm();
  }
  quickAddContacto() {
    this.setActiveTab('contactos');
    this.openContactoForm();
  }

  // ===== Reset de formularios =====
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

    this.formErrors = {};

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

    this.initialForms = {};
    this.hasUnsavedChanges = {};
  }

  showMessage(message: string, type: 'success' | 'error'): void {
    this.message = message;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
    }, 5000);
  }

  // ===== Password modal (coincide con la plantilla) =====
  openPasswordModal() {
    this.showPasswordModal = true;
  }
  onPasswordModalClosed() {
    this.showPasswordModal = false;
  }
  onPasswordChanged(success: boolean) {
    if (success) {
      this.addActividad('info', 'Contraseña cambiada');
    }
  }

  // EMPRESA EDIT
  openEmpresaEditForm(): void {
    this.clearFormErrors('empresa');
    this.showEmpresaEditForm = true;
    setTimeout(() => {
      this.saveInitialFormState('empresa', this.empresaEditForm);
    }, 0);
  }

  onSubmitEmpresaEdit(): void {
    this.loading = true;
    this.clearFormErrors('empresa');

    this.adminEmpresaService.updateMyCompany(this.empresaEditForm).subscribe({
      next: () => {
        this.showMessage(
          'Datos de empresa actualizados exitosamente',
          'success'
        );
        this.pushActivity('info', 'Datos de empresa actualizados');
        this.loadEmpresaData();
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.handleError(error, 'empresa', 'actualizar datos de empresa');
        this.loading = false;
      },
    });
  }

  // ===== Vehículos =====
  openVehiculoForm(vehiculo?: Vehiculo): void {
    this.clearFormErrors('vehiculo');

    if (vehiculo) {
      this.editingVehiculo = vehiculo;
      this.vehiculoForm = {
        id_tipo_vehiculo: vehiculo.id_tipo_vehiculo,
        horarios: vehiculo.horarios,
        frecuencia: vehiculo.frecuencia,
        datos: { ...vehiculo.datos },
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

    this.onVehiculoTipoChange();
    this.showVehiculoForm = true;
    setTimeout(() => {
      this.saveInitialFormState('vehiculo', this.vehiculoForm);
    }, 0);
  }

  onSubmitVehiculo(): void {
    this.loading = true;
    this.clearFormErrors('vehiculo');

    if (this.editingVehiculo) {
      this.adminEmpresaService
        .updateVehiculo(this.editingVehiculo.id_vehiculo, this.vehiculoForm)
        .subscribe({
          next: () => {
            this.showMessage('Vehículo actualizado exitosamente', 'success');
            this.pushActivity(
              'ok',
              `Vehículo actualizado (${
                this.vehiculoForm.datos?.patente || 'sin patente'
              })`
            );

            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.handleError(error, 'vehiculo', 'actualizar vehículo');
            this.loading = false;
          },
        });
    } else {
      this.adminEmpresaService.createVehiculo(this.vehiculoForm).subscribe({
        next: () => {
          this.showMessage('Vehículo creado exitosamente', 'success');
          this.pushActivity(
            'ok',
            `Vehículo agregado (${
              this.vehiculoForm.datos?.patente || 'sin patente'
            })`
          );

          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.handleError(error, 'vehiculo', 'crear vehículo');
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
          this.pushActivity('warn', `Vehículo eliminado (#${id})`);
          this.loadEmpresaData();
        },
        error: (error) => {
          this.handleError(error, 'general', 'eliminar vehículo');
        },
      });
    }
  }

  // ===== Servicios =====
  openServicioForm(servicio?: Servicio): void {
    this.clearFormErrors('servicio');

    if (servicio) {
      this.editingServicio = servicio;
      this.servicioForm = {
        id_tipo_servicio: servicio.id_tipo_servicio,
        datos: { ...servicio.datos },
      };
    } else {
      this.editingServicio = null;
      this.servicioForm = {
        id_tipo_servicio: 1,
        datos: {},
      };
    }

    this.onTipoServicioChange();

    if (this.editingServicio) {
      this.servicioForm.datos = { ...servicio!.datos };
    }

    this.showServicioForm = true;
    setTimeout(() => {
      this.saveInitialFormState('servicio', this.servicioForm);
    }, 0);
  }

  onSubmitServicio(): void {
    this.loading = true;
    this.clearFormErrors('servicio');

    if (this.editingServicio) {
      const sid = this.editingServicio.id_servicio;

      const updateData: ServicioUpdate = {
        datos: this.servicioForm.datos,
        id_tipo_servicio: this.servicioForm.id_tipo_servicio,
      };

      this.adminEmpresaService.updateServicio(sid, updateData).subscribe({
        next: () => {
          this.showMessage('Servicio actualizado exitosamente', 'success');
          this.pushActivity('ok', `Servicio actualizado (#${sid})`);
          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.handleError(error, 'servicio', 'actualizar servicio');
          this.loading = false;
        },
      });
    } else {
      this.adminEmpresaService.createServicio(this.servicioForm).subscribe({
        next: () => {
          this.showMessage('Servicio creado exitosamente', 'success');
          this.pushActivity(
            'ok',
            `Servicio agregado (${this.getTipoServicioName(
              this.servicioForm.id_tipo_servicio
            )})`
          );

          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.handleError(error, 'servicio', 'crear servicio');
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
          this.pushActivity('warn', `Servicio eliminado (#${id})`);
          this.loadEmpresaData();
        },
        error: (error) => {
          this.handleError(error, 'general', 'eliminar servicio');
        },
      });
    }
  }

  onTipoServicioChange(): void {
    this.servicioForm.datos = {};

    switch (this.servicioForm.id_tipo_servicio) {
      case 1:
        this.servicioForm.datos = {
          biofiltro: '',
          tratamiento_aguas_grises: '',
        };
        break;
      case 2:
        this.servicioForm.datos = {
          abierto: '',
          m2: null,
        };
        break;
      case 3:
        this.servicioForm.datos = {
          tipo: '',
          proveedor: '',
        };
        break;
      case 4:
        this.servicioForm.datos = {
          tipo: '',
          cantidad: null,
        };
        break;
      default:
        this.servicioForm.datos = {};
    }
  }

  // ===== Contactos =====
  openContactoForm(contacto?: Contacto): void {
    this.clearFormErrors('contacto');

    if (contacto) {
      this.editingContacto = contacto;
      this.contactoForm = {
        id_tipo_contacto: contacto.id_tipo_contacto,
        nombre: contacto.nombre,
        telefono: contacto.telefono || '',
        datos: contacto.datos
          ? { ...contacto.datos }
          : {
              pagina_web: '',
              correo: '',
              redes_sociales: '',
              direccion: '',
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
          direccion: '',
        },
        direccion: '',
        id_servicio_polo: 1,
      };
    }

    this.showContactoForm = true;
    this.onTipoContactoChange();
    setTimeout(() => {
      this.saveInitialFormState('contacto', this.contactoForm);
    }, 0);
  }

  onTipoContactoChange(): void {
    const tipo = Number(this.contactoForm.id_tipo_contacto);

    if (tipo === 1) {
      this.contactoForm.datos = {
        pagina_web: this.contactoForm.datos.pagina_web || '',
        correo: this.contactoForm.datos.correo || '',
        redes_sociales: this.contactoForm.datos.redes_sociales || '',
        direccion:
          this.contactoForm.direccion ||
          this.contactoForm.datos.direccion ||
          '',
      };
    } else {
      this.contactoForm.datos = {};
    }
  }

  onSubmitContacto(): void {
    this.loading = true;
    this.clearFormErrors('contacto');

    if (this.esTipoComercial()) {
      if (this.contactoForm.direccion) {
        this.contactoForm.datos.direccion = this.contactoForm.direccion;
      } else if (this.contactoForm.datos.direccion) {
        this.contactoForm.direccion = this.contactoForm.datos.direccion;
      }

      if (
        !this.contactoForm.datos.direccion ||
        this.contactoForm.datos.direccion.trim() === ''
      ) {
        this.formErrors['contacto'] = [
          {
            field: 'direccion',
            message: 'La dirección es requerida para contactos comerciales',
            type: 'required',
          },
        ];
        this.showMessage(
          'La dirección es requerida para contactos comerciales',
          'error'
        );
        this.loading = false;
        return;
      }
    }

    if (this.editingContacto) {
      this.adminEmpresaService
        .updateContacto(this.editingContacto.id_contacto, this.contactoForm)
        .subscribe({
          next: () => {
            this.showMessage('Contacto actualizado exitosamente', 'success');
            this.pushActivity(
              'ok',
              `Contacto actualizado (${this.contactoForm.nombre})`
            );

            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.handleError(error, 'contacto', 'actualizar contacto');
            this.loading = false;
          },
        });
    } else {
      this.adminEmpresaService.createContacto(this.contactoForm).subscribe({
        next: () => {
          this.showMessage('Contacto creado exitosamente', 'success');
          this.pushActivity(
            'ok',
            `Contacto agregado (${this.contactoForm.nombre})`
          );

          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.handleError(error, 'contacto', 'crear contacto');
          this.loading = false;
        },
      });
    }
  }

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
          this.pushActivity('warn', `Contacto eliminado (#${id})`);
          this.loadEmpresaData();
        },
        error: (error) => {
          this.handleError(error, 'general', 'eliminar contacto');
        },
      });
    }
  }

  esTipoComercial(): boolean {
    return this.contactoForm.id_tipo_contacto === 1;
  }

  // ===== Helpers de tipos/estado/fechas =====
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

  // HH:mm para actividad en vivo
  private formatTime(d: Date): string {
    try {
      return d.toLocaleTimeString('es-AR', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '—';
    }
  }

  // usado por el HTML y por el getter desdeIngreso
  formatMonthYear(dateStr?: string): string {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return new Intl.DateTimeFormat('es-AR', {
        month: 'long',
        year: 'numeric',
      }).format(d);
    } catch {
      return '—';
    }
  }

  formatDatos(datos: any, isExpanded: boolean = false): string {
    if (!datos || Object.keys(datos).length === 0) {
      return 'Sin datos adicionales';
    }
    try {
      const dataString = JSON.stringify(datos, null, 2);
      if (isExpanded) return dataString;
      return dataString.length > 50
        ? dataString.substring(0, 50) + '...'
        : dataString;
    } catch {
      return 'Error al procesar datos';
    }
  }

  getTotalLotes(): number {
    if (!this.empresaData?.servicios_polo) return 0;
    return this.empresaData.servicios_polo.reduce((total, servicio) => {
      return total + (servicio.lotes ? servicio.lotes.length : 0);
    }, 0);
  }

  getTipoVehiculoName(id: any): string {
    const nid = Number(id);
    const t = this.tiposVehiculo?.find(
      (v) => Number(v.id_tipo_vehiculo) === nid
    );
    return t?.tipo ?? '-';
  }

  getTipoServicioName(id: any): string {
    const nid = Number(id);
    const t = this.tiposServicio?.find(
      (s) => Number(s.id_tipo_servicio) === nid
    );
    return t?.tipo ?? '-';
  }

  getTipoContactoName(id: any): string {
    const nid = Number(id);
    const t = this.tiposContacto?.find(
      (c) => Number(c.id_tipo_contacto) === nid
    );
    return t?.tipo ?? '-';
  }

  loadTipos(): void {
    this.loadingTipos = true;

    this.adminEmpresaService.getTiposServicioPolo().subscribe({
      next: (tipos) => {
        this.tiposServicioPolo = tipos;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de servicio polo');
      },
    });

    this.adminEmpresaService.getTiposVehiculo().subscribe({
      next: (tipos) => {
        this.tiposVehiculo = tipos;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de vehículo');
      },
    });

    this.adminEmpresaService.getTiposServicio().subscribe({
      next: (tipos) => {
        this.tiposServicio = tipos;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de servicio');
      },
    });

    this.adminEmpresaService.getTiposContacto().subscribe({
      next: (tipos) => {
        this.tiposContacto = tipos;
        this.loadingTipos = false;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de contacto');
        this.loadingTipos = false;
      },
    });
  }

  toggleExpandRow(key: string): void {
    if (this.expandedRows.has(key)) {
      this.expandedRows.delete(key);
    } else {
      this.expandedRows.add(key);
    }
  }

  hasKeys(obj: any): boolean {
    return obj && Object.keys(obj).length > 0;
  }

  toggleErrorDetails(): void {
    this.showErrorDetails = !this.showErrorDetails;
  }

  getTotalErrors(): number {
    return Object.values(this.formErrors).reduce(
      (total, errors) => total + errors.length,
      0
    );
  }

  getErrorsByType(type: FormError['type']): FormError[] {
    const allErrors: FormError[] = [];
    Object.values(this.formErrors).forEach((errors) => {
      allErrors.push(...errors.filter((error) => error.type === type));
    });
    return allErrors;
  }

  private handlePasswordError(errorResponse: any): void {
    this.clearFormErrors('password');
    let passwordErrors: FormError[] = [];

    if (
      errorResponse.wrong_current ||
      errorResponse.error?.includes('contraseña actual') ||
      errorResponse.detail?.includes('incorrecta')
    ) {
      passwordErrors.push({
        field: 'currentPassword',
        message: 'La contraseña actual es incorrecta',
        type: 'validation',
      });
      this.showMessage('La contraseña actual es incorrecta', 'error');
    } else if (
      errorResponse.password_reused ||
      errorResponse.error?.includes('utilizado anteriormente')
    ) {
      passwordErrors.push({
        field: 'newPassword',
        message:
          'No puedes usar una contraseña que ya hayas utilizado anteriormente',
        type: 'validation',
      });
      this.showMessage(
        'No puedes usar una contraseña que ya hayas utilizado anteriormente',
        'error'
      );
    } else if (
      errorResponse.passwords_mismatch ||
      errorResponse.error?.includes('no coinciden')
    ) {
      passwordErrors.push({
        field: 'confirmPassword',
        message: 'Las contraseñas no coinciden',
        type: 'validation',
      });
      this.showMessage('Las contraseñas no coinciden', 'error');
    } else if (errorResponse.detail) {
      passwordErrors.push({
        field: 'general',
        message: errorResponse.detail,
        type: 'server',
      });
      this.showMessage(errorResponse.detail, 'error');
    } else if (errorResponse.error) {
      passwordErrors.push({
        field: 'general',
        message: errorResponse.error,
        type: 'server',
      });
      this.showMessage(errorResponse.error, 'error');
    } else {
      passwordErrors.push({
        field: 'general',
        message: 'Error al cambiar la contraseña. Inténtalo nuevamente.',
        type: 'server',
      });
      this.showMessage('Error al cambiar la contraseña', 'error');
    }

    this.formErrors['password'] = passwordErrors;
  }

  onVehiculoTipoChange(): void {
    const tipo = Number(this.vehiculoForm.id_tipo_vehiculo);
    const currentDatos = this.vehiculoForm.datos || {};

    switch (tipo) {
      case 1: // Corporativo
        this.vehiculoForm.datos = {
          cantidad: currentDatos.cantidad ?? null,
          patente: currentDatos.patente ?? '',
          carga: currentDatos.carga ?? null,
        };
        break;
      case 2: // Personal
        this.vehiculoForm.datos = {
          cantidad: currentDatos.cantidad ?? null,
          patente: currentDatos.patente ?? '',
        };
        break;
      case 3: // Terceros
        this.vehiculoForm.datos = {
          cantidad: currentDatos.cantidad ?? null,
          carga: currentDatos.carga ?? null,
        };
        break;
      default:
        this.vehiculoForm.datos = {
          descripcion: currentDatos.descripcion ?? '',
        };
    }
  }

  /** Devuelve un texto de URL sin protocolo para mostrar */
  displayUrl(u?: string): string {
    if (!u) return '';
    try {
      return u.trim().replace(/^\s*https?:\/\//i, '');
    } catch {
      return u;
    }
  }

  /** Devuelve una URL segura para usar en href (agrega https:// si falta) */
  externalHref(u?: string): string {
    if (!u) return '#';
    return /^https?:\/\//i.test(u) ? u : `https://${u.trim()}`;
  }
}
