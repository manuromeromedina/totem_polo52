// chat.component.ts
import { Component, OnInit, ElementRef, ViewChild, AfterViewChecked } from '@angular/core';
import { ChatService } from './chat.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { LogoutButtonComponent } from '../shared/logout-button/logout-button.component';

interface Message {
  sender: 'user' | 'bot';
  content: string;
  timestamp: Date;
  id: string;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [FormsModule, CommonModule, LogoutButtonComponent],
  template: `
    <div class="chat-wrapper" [class.dark-mode]="isDarkMode">
      <div class="chat-header">
        <div class="header-content">
          <div class="bot-avatar">
            <div class="avatar-icon">P52</div>
            <div class="status-indicator" [class.active]="!isTyping"></div>
          </div>
          <div class="header-info">
            <h2>Asistente Virtual - Parque Industrial Polo 52</h2>
            <p class="status-text">{{ isTyping ? 'Escribiendo...' : 'Disponible para consultas' }}</p>
          </div>
        </div>
        <div class="header-actions">
          <app-logout-button></app-logout-button>
        </div>
      </div>

      <div class="chat-container">
        <div class="chat-controls">
          <button class="theme-toggle" (click)="toggleTheme()" [attr.aria-label]="isDarkMode ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'">
            <span *ngIf="!isDarkMode">Modo Oscuro</span>
            <span *ngIf="isDarkMode">Modo Claro</span>
          </button>
        </div>
        <div class="chat-messages" #messagesContainer>
          <div 
            *ngFor="let message of messages; trackBy: trackByMessageId" 
            class="message-wrapper"
            [class.user-wrapper]="message.sender === 'user'"
            [class.bot-wrapper]="message.sender === 'bot'"
          >
            <div class="message-content" [class]="message.sender === 'user' ? 'user-message' : 'bot-message'">
              <div class="message-text" [innerHTML]="formatMessage(message.content)"></div>
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>
          </div>
          
          <!-- Indicador de escritura -->
          <div *ngIf="isTyping" class="message-wrapper bot-wrapper typing-indicator">
            <div class="bot-message typing-message">
              <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="chat-input-container">
          <div class="chat-input">
            <button 
              class="mic-button" 
              (click)="toggleSpeechRecognition()"
              [disabled]="isTyping"
              [class.listening]="isListening"
              [attr.aria-label]="isListening ? 'Detener grabación' : 'Iniciar grabación de voz'"
            >
              <span *ngIf="!isListening">MIC</span>
              <span *ngIf="isListening" class="mic-recording">REC</span>
            </button>
            <input 
              #messageInput
              [(ngModel)]="userMessage" 
              placeholder="Escriba su consulta sobre las empresas del parque..." 
              (keyup.enter)="sendMessage()"
              [disabled]="isTyping"
              class="message-input"
            >
            <button 
              (click)="sendMessage()" 
              [disabled]="!userMessage.trim() || isTyping"
              class="send-button"
            >
              <span *ngIf="!isTyping">Enviar</span>
              <span *ngIf="isTyping" class="loading-text">...</span>
            </button>
          </div>
          <div class="input-footer">
            <small>
              <span *ngIf="!isListening">Presione Enter para enviar su consulta o use el micrófono para hablar</span>
              <span *ngIf="isListening" class="listening-text">Grabando... Hable ahora</span>
            </small>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .chat-wrapper {
        height: 100vh;
        display: flex;
        flex-direction: column;
        background: #f8f9fa;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #495057;
        transition: background-color 0.3s ease, color 0.3s ease;
      }

      /* === MODO OSCURO === */
      .chat-wrapper.dark-mode {
        background: #1a1a1a;
        color: #e0e0e0;
      }

      .chat-header {
        background: #ffffff;
        padding: 18px;
        border-bottom: 1px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: background-color 0.3s ease, border-color 0.3s ease;
      }

      .dark-mode .chat-header {
        background: #2d2d2d;
        border-bottom: 1px solid #404040;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
      }

      .header-content {
        display: flex;
        align-items: center;
        gap: 14px;
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .theme-toggle {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        padding: 8px 16px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 500;
        color: #495057;
      }

      .theme-toggle:hover {
        background: #e9ecef;
        transform: translateY(-1px);
      }

      .dark-mode .theme-toggle {
        background: #404040;
        border: 1px solid #555;
        color: #e0e0e0;
      }

      .dark-mode .theme-toggle:hover {
        background: #505050;
      }

      .bot-avatar {
        position: relative;
        width: 48px;
        height: 48px;
        background: #6c757d;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 10px;
        transition: background-color 0.3s ease;
      }

      .dark-mode .bot-avatar {
        background: #505050;
      }

      .avatar-icon {
        font-size: 12px;
        font-weight: 600;
      }

      .status-indicator {
        position: absolute;
        bottom: -2px;
        right: -2px;
        width: 12px;
        height: 12px;
        background: #dc3545;
        border-radius: 50%;
        border: 2px solid white;
        transition: background-color 0.3s ease;
      }

      .dark-mode .status-indicator {
        border: 2px solid #2d2d2d;
      }

      .status-indicator.active {
        background: #28a745;
        box-shadow: 0 0 8px rgba(40, 167, 69, 0.4);
      }

      .header-info h2 {
        margin: 0;
        color: #212529;
        font-size: 16px;
        font-weight: 600;
        line-height: 1.2;
        transition: color 0.3s ease;
      }

      .dark-mode .header-info h2 {
        color: #e0e0e0;
      }

      .status-text {
        margin: 0;
        color: #6c757d;
        font-size: 14px;
        font-weight: 400;
        margin-top: 2px;
        transition: color 0.3s ease;
      }

      .dark-mode .status-text {
        color: #a0a0a0;
      }

      .chat-container {
        flex: 1;
        display: flex;
        flex-direction: column;
        max-width: 1000px;
        margin: 0 auto;
        padding: 20px;
        width: 100%;
        box-sizing: border-box;
        background: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        overflow: hidden;
        transition: background-color 0.3s ease, border-color 0.3s ease;
      }

      .dark-mode .chat-container {
        background: #2d2d2d;
        border: 1px solid #404040;
      }

      .chat-controls {
        display: flex;
        justify-content: flex-end;
        padding: 12px 0;
        border-bottom: 1px solid #dee2e6;
        margin-bottom: 12px;
      }

      .dark-mode .chat-controls {
        border-bottom: 1px solid #404040;
      }

      .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        background: #ffffff;
        scroll-behavior: smooth;
        transition: background-color 0.3s ease;
      }

      .dark-mode .chat-messages {
        background: #2d2d2d;
      }

      .message-wrapper {
        display: flex;
        animation: fadeIn 0.2s ease-out;
      }

      .user-wrapper {
        justify-content: flex-end;
      }

      .bot-wrapper {
        justify-content: flex-start;
      }

      .message-content {
        max-width: 70%;
        position: relative;
      }

      .user-message {
        background: #495057;  /* Gris oscuro en modo claro */
        color: white;
        padding: 12px 16px;
        border-radius: 16px 16px 4px 16px;
        border: 1px solid #495057;
        transition: background-color 0.3s ease, border-color 0.3s ease;
      }

      .dark-mode .user-message {
        background: #e9ecef;  /* Gris claro en modo oscuro */
        color: #212529;       /* Texto oscuro en modo oscuro */
        border: 1px solid #e9ecef;
      }

      .bot-message {
        background: #f8f9fa;
        color: #212529;
        padding: 12px 16px;
        border-radius: 16px 16px 16px 4px;
        border: 1px solid #dee2e6;
        transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
      }

      .dark-mode .bot-message {
        background: #404040;
        color: #e0e0e0;
        border: 1px solid #555;
      }

      .message-text {
        word-wrap: break-word;
        line-height: 1.5;
        margin-bottom: 4px;
        font-size: 15px;
      }

      .message-time {
        font-size: 12px;
        opacity: 0.7;
        text-align: right;
        margin-top: 4px;
      }

      .user-message .message-time {
        color: rgba(255, 255, 255, 0.8);
      }

      .bot-message .message-time {
        color: #6c757d;
        transition: color 0.3s ease;
      }

      .dark-mode .bot-message .message-time {
        color: #a0a0a0;
      }

      .typing-indicator {
        animation: fadeIn 0.3s ease-in;
      }

      .typing-message {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 12px 16px;
        transition: background-color 0.3s ease, border-color 0.3s ease;
      }

      .dark-mode .typing-message {
        background: #404040;
        border: 1px solid #555;
      }

      .typing-dots {
        display: flex;
        gap: 4px;
        align-items: center;
      }

      .typing-dots span {
        width: 6px;
        height: 6px;
        background: #6c757d;
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
        transition: background-color 0.3s ease;
      }

      .dark-mode .typing-dots span {
        background: #a0a0a0;
      }

      .typing-dots span:nth-child(2) {
        animation-delay: 0.2s;
      }

      .typing-dots span:nth-child(3) {
        animation-delay: 0.4s;
      }

      .chat-input-container {
        background: #f8f9fa;
        border-top: 1px solid #dee2e6;
        padding: 20px;
        margin-top: auto;
        transition: background-color 0.3s ease, border-color 0.3s ease;
      }

      .dark-mode .chat-input-container {
        background: #383838;
        border-top: 1px solid #555;
      }

      .chat-input {
        display: flex;
        gap: 8px;
        align-items: stretch;
      }

      .mic-button {
        padding: 12px 16px;
        background: #6c757d;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s ease-in-out;
        font-size: 12px;
        font-weight: 600;
        font-family: inherit;
        min-width: 56px;
        min-height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        letter-spacing: 0.5px;
      }

      .mic-button:hover:not(:disabled) {
        background: #5a6268;
        transform: translateY(-1px);
      }

      .mic-button:disabled {
        background: #adb5bd;
        cursor: not-allowed;
        transform: none;
      }

      .mic-button.listening {
        background: #dc3545;
        animation: pulse-red 1.5s infinite;
      }

      .mic-button.listening:hover {
        background: #c82333;
      }

      .dark-mode .mic-button {
        background: #505050;
      }

      .dark-mode .mic-button:hover:not(:disabled) {
        background: #606060;
      }

      .dark-mode .mic-button.listening {
        background: #dc3545;
      }

      .mic-recording {
        animation: blink 1s infinite;
      }

      .message-input {
        flex: 1;
        padding: 12px 16px;
        font-size: 15px;
        border: 1px solid #ced4da;
        border-radius: 6px;
        outline: none;
        transition: all 0.15s ease-in-out;
        background: #ffffff;
        font-family: inherit;
        color: #495057;
      }

      .message-input:focus {
        border-color: #495057;  /* Cambiado de azul a gris oscuro */
        box-shadow: 0 0 0 2px rgba(73, 80, 87, 0.1);
      }

      .dark-mode .message-input {
        background: #505050;
        border: 1px solid #666;
        color: #e0e0e0;
      }

      .dark-mode .message-input:focus {
        border-color: #007bff;
        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
      }

      .dark-mode .message-input::placeholder {
        color: #a0a0a0;
      }

      .message-input:disabled {
        background: #f8f9fa;
        cursor: not-allowed;
        color: #6c757d;
      }

      .dark-mode .message-input:disabled {
        background: #404040;
        color: #808080;
      }

      .send-button {
        padding: 12px 24px;
        background: #495057;  /* Gris oscuro en modo claro */
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.15s ease-in-out;
        font-size: 15px;
        font-weight: 500;
        font-family: inherit;
        min-width: 80px;
      }

      .send-button:hover:not(:disabled) {
        background: #343a40;  /* Versión más oscura del gris */
      }

      .dark-mode .send-button {
        background: #e9ecef;  /* Gris claro en modo oscuro */
        color: #212529;       /* Texto oscuro en modo oscuro */
      }

      .dark-mode .send-button:hover:not(:disabled) {
        background: #dee2e6;  /* Versión más oscura del gris claro */
      }

      .send-button:disabled {
        background: #6c757d;
        cursor: not-allowed;
      }

      .loading-text {
        display: inline-block;
        animation: pulse-loading 1s infinite;
      }

      @keyframes pulse-loading {
        0%, 100% {
          opacity: 1;
        }
        50% {
          opacity: 0.5;
        }
      }

      .input-footer {
        text-align: center;
        margin-top: 12px;
      }

      .input-footer small {
        color: #6c757d;
        font-size: 13px;
        transition: color 0.3s ease;
      }

      .dark-mode .input-footer small {
        color: #a0a0a0;
      }

      .listening-text {
        color: #dc3545 !important;
        font-weight: 500;
        animation: pulse-text 1s infinite;
      }

      @keyframes pulse-text {
        0%, 100% {
          opacity: 1;
        }
        50% {
          opacity: 0.7;
        }
      }

      /* Animaciones sutiles */
      @keyframes fadeIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      @keyframes typing {
        0%, 60%, 100% {
          transform: translateY(0);
          opacity: 0.4;
        }
        30% {
          transform: translateY(-6px);
          opacity: 1;
        }
      }

      @keyframes pulse-red {
        0%, 100% {
          box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
        }
        50% {
          box-shadow: 0 0 0 8px rgba(220, 53, 69, 0);
        }
      }

      @keyframes blink {
        0%, 50% {
          opacity: 1;
        }
        51%, 100% {
          opacity: 0.3;
        }
      }

      /* Responsive para tótem */
      @media (max-width: 1024px) {
        .chat-container {
          padding: 20px;
        }
        
        .message-content {
          max-width: 80%;
        }
        
        .header-info h2 {
          font-size: 14px;
        }
        
        .chat-header {
          padding: 16px;
        }

        .message-input {
          font-size: 16px;
        }
      }

      @media (max-width: 768px) {
        .chat-container {
          padding: 16px;
        }
        
        .message-content {
          max-width: 85%;
        }
        
        .header-content {
          gap: 12px;
        }
        
        .bot-avatar {
          width: 40px;
          height: 40px;
          font-size: 10px;
        }
        
        .header-info h2 {
          font-size: 14px;
        }
        
        .status-text {
          font-size: 12px;
        }

        .theme-toggle {
          padding: 6px 12px;
          font-size: 12px;
        }

        .mic-button {
          min-width: 48px;
          min-height: 40px;
          font-size: 10px;
          padding: 8px 12px;
        }
      }

      /* Scrollbar personalizado */
      .chat-messages::-webkit-scrollbar {
        width: 8px;
      }

      .chat-messages::-webkit-scrollbar-track {
        background: #f1f3f4;
        border-radius: 4px;
        margin: 10px 0;
      }

      .dark-mode .chat-messages::-webkit-scrollbar-track {
        background: #404040;
      }

      .chat-messages::-webkit-scrollbar-thumb {
        background: #ced4da;
        border-radius: 4px;
      }

      .dark-mode .chat-messages::-webkit-scrollbar-thumb {
        background: #666;
      }

      .chat-messages::-webkit-scrollbar-thumb:hover {
        background: #adb5bd;
      }

      .dark-mode .chat-messages::-webkit-scrollbar-thumb:hover {
        background: #777;
      }

      /* Mejoras para accesibilidad táctil */
      .send-button {
        min-height: 44px;
      }

      .message-input {
        min-height: 44px;
      }

      .mic-button {
        min-height: 44px;
      }

      /* Contraste mejorado */
      .user-message {
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      }

      .bot-message {
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
      }

      .dark-mode .user-message {
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
      }

      .dark-mode .bot-message {
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
      }
    `,
  ],
})
export class ChatbotComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('messageInput') messageInput!: ElementRef;

  messages: Message[] = [];
  userMessage: string = '';
  isTyping: boolean = false;
  isDarkMode: boolean = false;
  isListening: boolean = false;
  private shouldScrollToBottom = false;
  private recognition: any = null;

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    // Cargar preferencia de tema desde localStorage
    const savedTheme = localStorage.getItem('chatTheme');
    this.isDarkMode = savedTheme === 'dark';

    // Inicializar reconocimiento de voz
    this.initializeSpeechRecognition();

    this.addBotMessage('Bienvenido al Parque Industrial Polo 52.\n\nMi nombre es POLO y estoy aquí para ayudarle con consultas sobre las empresas y servicios disponibles en el parque. ¿En qué puedo asistirle?');
  }

  ngAfterViewChecked() {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  toggleTheme() {
    this.isDarkMode = !this.isDarkMode;
    localStorage.setItem('chatTheme', this.isDarkMode ? 'dark' : 'light');
  }

  initializeSpeechRecognition() {
    // Verificar si el navegador soporta reconocimiento de voz
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      this.recognition = new SpeechRecognition();
      
      // Configuración del reconocimiento
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'es-ES'; // Español de España
      this.recognition.maxAlternatives = 1;

      // Eventos del reconocimiento
      this.recognition.onstart = () => {
        this.isListening = true;
        console.log('Reconocimiento de voz iniciado');
      };

      this.recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        this.userMessage = transcript;
        console.log('Texto reconocido:', transcript);
        
        // Enviar automáticamente después de reconocer
        setTimeout(() => {
          if (this.userMessage.trim()) {
            this.sendMessage();
          }
        }, 500);
      };

      this.recognition.onerror = (event: any) => {
        console.error('Error en reconocimiento de voz:', event.error);
        this.isListening = false;
        
        let errorMessage = '';
        switch (event.error) {
          case 'no-speech':
            errorMessage = 'No se detectó voz. Intente nuevamente.';
            break;
          case 'audio-capture':
            errorMessage = 'No se pudo acceder al micrófono.';
            break;
          case 'not-allowed':
            errorMessage = 'Permisos de micrófono denegados.';
            break;
          default:
            errorMessage = 'Error de reconocimiento de voz.';
        }
        
        this.showVoiceError(errorMessage);
      };

      this.recognition.onend = () => {
        this.isListening = false;
        console.log('Reconocimiento de voz finalizado');
      };
    } else {
      console.warn('Reconocimiento de voz no soportado en este navegador');
    }
  }

  toggleSpeechRecognition() {
    if (!this.recognition) {
      this.showVoiceError('Reconocimiento de voz no disponible en este navegador.');
      return;
    }

    if (this.isListening) {
      // Detener reconocimiento
      this.recognition.stop();
    } else {
      // Iniciar reconocimiento
      try {
        this.recognition.start();
      } catch (error) {
        console.error('Error al iniciar reconocimiento:', error);
        this.showVoiceError('Error al iniciar el reconocimiento de voz.');
      }
    }
  }

  private showVoiceError(message: string) {
    // Mostrar error temporalmente en el placeholder
    const originalPlaceholder = this.messageInput.nativeElement.placeholder;
    this.messageInput.nativeElement.placeholder = message;
    
    setTimeout(() => {
      this.messageInput.nativeElement.placeholder = originalPlaceholder;
    }, 3000);
  }

  trackByMessageId(index: number, message: Message): string {
    return message.id;
  }

  private generateMessageId(): string {
    return Date.now().toString() + Math.random().toString(36).substr(2, 9);
  }

  private addUserMessage(content: string) {
    this.messages.push({
      sender: 'user',
      content,
      timestamp: new Date(),
      id: this.generateMessageId()
    });
    this.shouldScrollToBottom = true;
  }

  private addBotMessage(content: string) {
    this.messages.push({
      sender: 'bot',
      content,
      timestamp: new Date(),  
      id: this.generateMessageId()
    });
    this.shouldScrollToBottom = true;
  }

  private scrollToBottom(): void {
    try {
      if (this.messagesContainer) {
        const element = this.messagesContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      }
    } catch(err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  formatMessage(content: string): string {
    return content.replace(/\n/g, '<br>');
  }

  formatTime(timestamp: Date): string {
    return timestamp.toLocaleTimeString('es-ES', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  private getChatHistory(): Array<{ user: string; assistant: string }> {
    const history: Array<{ user: string; assistant: string }> = [];
    let lastUserMessage: string | null = null;

    for (const message of this.messages) {
      if (message.sender === 'user') {
        lastUserMessage = message.content;
      } else if (message.sender === 'bot' && lastUserMessage) {
        history.push({ user: lastUserMessage, assistant: message.content });
        lastUserMessage = null;
      }
    }
    return history;
  }

  async sendMessage() {
    if (!this.userMessage.trim() || this.isTyping) {
      return;
    }

    const messageToSend = this.userMessage.trim();
    this.addUserMessage(messageToSend);
    this.userMessage = '';
    this.isTyping = true;

    // Delay antes de comenzar a "escribir" - más rápido
    const initialDelay = Math.min(300 + (messageToSend.length * 10), 800);
    
    setTimeout(() => {
      const history = this.getChatHistory();

      this.chatService.sendMessage(messageToSend, history).subscribe({
        next: (response) => {
          if (response && 'reply' in response) {
            this.simulateTyping(response.reply);
          } else {
            this.simulateTyping('Lo siento, recibí una respuesta inválida del servidor. Por favor, intente reformular su consulta.');
          }
        },
        error: (error) => {
          console.error('Error en la solicitud:', error);
          let errorMessage = 'Lo siento, hubo un problema técnico. Por favor, intente nuevamente.';
          
          if (error.status === 0) {
            errorMessage = 'No se pudo conectar con el servidor. Verifique la conexión.';
          } else if (error.status >= 500) {
            errorMessage = 'El servidor está experimentando problemas. Intente más tarde.';
          }
          
          this.simulateTyping(errorMessage);
        },
      });
    }, initialDelay);

    // Auto-focus para facilitar uso en tótem
    setTimeout(() => {
      if (this.messageInput) {
        this.messageInput.nativeElement.focus();
      }
    }, 100);
  }

  private simulateTyping(message: string) {
    // Crear un mensaje vacío del bot
    const botMessage: Message = {
      sender: 'bot',
      content: '',
      timestamp: new Date(),
      id: this.generateMessageId()
    };
    
    this.messages.push(botMessage);
    this.shouldScrollToBottom = true;
    
    // Variables para la simulación de escritura
    let currentIndex = 0;
    const characters = message.split('');
    
    const typeCharacter = () => {
      if (currentIndex < characters.length) {
        // Actualizar el contenido del mensaje
        botMessage.content += characters[currentIndex];
        
        // Scroll automático mientras escribe
        this.shouldScrollToBottom = true;
        
        currentIndex++;
        
        // Velocidad más rápida
        let delay = 25; // Velocidad base más rápida
        
        // Pausas más cortas en puntos y comas
        if (characters[currentIndex - 1] === '.' || characters[currentIndex - 1] === '!') {
          delay = 100;
        } else if (characters[currentIndex - 1] === ',' || characters[currentIndex - 1] === ':') {
          delay = 50;
        } else if (characters[currentIndex - 1] === ' ') {
          delay = 15;
        } else {
          // Variación aleatoria más rápida
          delay = Math.random() * 20 + 15;
        }
        
        setTimeout(typeCharacter, delay);
      } else {
        // Terminó de escribir
        this.isTyping = false;
      }
    };
    
    // Comenzar a "escribir" más rápido
    setTimeout(typeCharacter, 100);
  }
}