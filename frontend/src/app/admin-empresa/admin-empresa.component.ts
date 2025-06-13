import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LogoutButtonComponent } from '../shared/logout-button/logout-button.component';

interface EmpresaSelf {
  cuil: number;
  nombre: string;
  rubro: string;
  cant_empleados: number;
  observaciones?: string;
  fecha_ingreso: string;
  horario_trabajo: string;
}

@Component({
  selector: 'app-empresa-me',
  standalone: true,
  imports: [CommonModule, FormsModule, LogoutButtonComponent],
  templateUrl: './admin-empresa.component.html',
  styleUrls: ['./admin-empresa.component.css']
})
export class EmpresaMeComponent implements OnInit {
  empresa!: EmpresaSelf;
  loading = false;
  loadingData = false;
  successMessage = '';
  errorMessage = '';
  
  // Datos originales para comparar cambios
  originalEmpresa!: EmpresaSelf;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.cargarDatosEmpresa();
  }

  cargarDatosEmpresa(): void {
    this.loadingData = true;
    this.errorMessage = '';
    
    this.http.get<EmpresaSelf>('http://localhost:8000/me').subscribe({
      next: (data) => {
        this.empresa = { ...data };
        this.originalEmpresa = { ...data }; // Guardar copia original
        this.loadingData = false;
        console.log('Datos de empresa cargados:', data);
      },
      error: (err: HttpErrorResponse) => {
        this.loadingData = false;
        this.errorMessage = 'Error al cargar los datos de la empresa';
        console.error('Error al obtener datos de la empresa:', err);
        
        // Manejar diferentes tipos de error
        if (err.status === 401) {
          this.errorMessage = 'Sesión expirada. Por favor, inicie sesión nuevamente.';
        } else if (err.status === 403) {
          this.errorMessage = 'No tiene permisos para acceder a esta información.';
        } else if (err.status === 0) {
          this.errorMessage = 'Error de conexión. Verifique su conexión a internet.';
        }
        
        this.limpiarMensajes();
      }
    });
  }

  actualizar(): void {
    if (!this.validarFormulario()) {
      return;
    }

    this.loading = true;
    this.successMessage = '';
    this.errorMessage = '';

    // Preparar datos para enviar (solo campos editables)
    const datosActualizar = {
      cant_empleados: this.empresa.cant_empleados,
      observaciones: this.empresa.observaciones || '',
      horario_trabajo: this.empresa.horario_trabajo.trim()
    };

    console.log('Actualizando empresa con datos:', datosActualizar);

    this.http.put('http://localhost:8000/me', datosActualizar).subscribe({
      next: (response) => {
        this.loading = false;
        this.successMessage = 'Datos de empresa actualizados correctamente';
        
        // Actualizar datos originales para futuras comparaciones
        this.originalEmpresa = { ...this.empresa };
        
        console.log('Empresa actualizada exitosamente:', response);
        this.limpiarMensajes();
      },
      error: (err: HttpErrorResponse) => {
        this.loading = false;
        console.error('Error al actualizar la empresa:', err);
        
        // Manejar diferentes tipos de error
        if (err.status === 400) {
          this.errorMessage = 'Datos inválidos. Verifique la información ingresada.';
        } else if (err.status === 401) {
          this.errorMessage = 'Sesión expirada. Por favor, inicie sesión nuevamente.';
        } else if (err.status === 403) {
          this.errorMessage = 'No tiene permisos para realizar esta acción.';
        } else if (err.status === 422) {
          this.errorMessage = 'Error de validación en los datos enviados.';
        } else if (err.status === 0) {
          this.errorMessage = 'Error de conexión. Verifique su conexión a internet.';
        } else {
          this.errorMessage = 'Error al actualizar los datos. Intente nuevamente.';
        }
        
        this.limpiarMensajes();
      }
    });
  }

  validarFormulario(): boolean {
    // Limpiar mensajes previos
    this.errorMessage = '';

    // Validar cantidad de empleados
    if (!this.empresa.cant_empleados || this.empresa.cant_empleados < 1) {
      this.errorMessage = 'La cantidad de empleados debe ser mayor a 0';
      this.limpiarMensajes();
      return false;
    }

    if (this.empresa.cant_empleados > 50000) {
      this.errorMessage = 'La cantidad de empleados no puede exceder 50,000';
      this.limpiarMensajes();
      return false;
    }

    // Validar horario de trabajo
    if (!this.empresa.horario_trabajo || this.empresa.horario_trabajo.trim().length === 0) {
      this.errorMessage = 'El horario de trabajo es requerido';
      this.limpiarMensajes();
      return false;
    }

    if (this.empresa.horario_trabajo.length > 200) {
      this.errorMessage = 'El horario de trabajo no puede exceder 200 caracteres';
      this.limpiarMensajes();
      return false;
    }

    // Validar observaciones (opcional)
    if (this.empresa.observaciones && this.empresa.observaciones.length > 1000) {
      this.errorMessage = 'Las observaciones no pueden exceder 1000 caracteres';
      this.limpiarMensajes();
      return false;
    }

    return true;
  }

  private limpiarMensajes(): void {
    setTimeout(() => {
      this.successMessage = '';
      this.errorMessage = '';
    }, 5000);
  }

  // Métodos auxiliares para mejorar UX
  onEmpleadosChange(): void {
    if (this.empresa.cant_empleados) {
      // Asegurar que esté en rango válido
      if (this.empresa.cant_empleados < 1) {
        this.empresa.cant_empleados = 1;
      }
      if (this.empresa.cant_empleados > 50000) {
        this.empresa.cant_empleados = 50000;
      }
    }
    this.limpiarMensajesError();
  }

  onHorarioChange(): void {
    if (this.empresa.horario_trabajo) {
      // Limpiar espacios extra al inicio y final
      this.empresa.horario_trabajo = this.empresa.horario_trabajo.trim();
    }
    this.limpiarMensajesError();
  }

  onObservacionesChange(): void {
    this.limpiarMensajesError();
  }

  private limpiarMensajesError(): void {
    if (this.errorMessage) {
      this.errorMessage = '';
    }
  }

  // Utilidades para la UI
  contarCaracteresObservaciones(): string {
    const longitud = this.empresa?.observaciones ? this.empresa.observaciones.length : 0;
    return `${longitud}/1000`;
  }

  contarCaracteresHorario(): string {
    const longitud = this.empresa?.horario_trabajo ? this.empresa.horario_trabajo.length : 0;
    return `${longitud}/200`;
  }

  hayCaracteresExcesivos(campo: 'observaciones' | 'horario'): boolean {
    if (campo === 'observaciones') {
      return this.empresa?.observaciones ? this.empresa.observaciones.length > 1000 : false;
    } else {
      return this.empresa?.horario_trabajo ? this.empresa.horario_trabajo.length > 200 : false;
    }
  }

  // Verificar si hay cambios pendientes
  haycambiosPendientes(): boolean {
    if (!this.empresa || !this.originalEmpresa) return false;
    
    return this.empresa.cant_empleados !== this.originalEmpresa.cant_empleados ||
           this.empresa.horario_trabajo !== this.originalEmpresa.horario_trabajo ||
           this.empresa.observaciones !== this.originalEmpresa.observaciones;
  }

  // Descartar cambios
  descartarCambios(): void {
    if (this.originalEmpresa) {
      this.empresa = { ...this.originalEmpresa };
      this.successMessage = '';
      this.errorMessage = '';
    }
  }

  // Recargar datos
  recargarDatos(): void {
    this.cargarDatosEmpresa();
  }

  // Formatear fecha para mostrar
  formatearFecha(fecha: string): string {
    try {
      return new Date(fecha).toLocaleDateString('es-AR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (error) {
      return fecha;
    }
  }
}