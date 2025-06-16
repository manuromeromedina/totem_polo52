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
    <div class="chat-wrapper">
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
        <app-logout-button></app-logout-button>
      </div>

      <div class="chat-container">
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
            <small>Presione Enter para enviar su consulta</small>
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
      }

      .chat-header {
        background: #ffffff;
        padding: 18px;
        border-bottom: 1px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .header-content {
        display: flex;
        align-items: center;
        gap: 14px;
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

      .status-indicator.active {
        background: #28a745;
      }

      .header-info h2 {
        margin: 0;
        color: #212529;
        font-size: 16px;
        font-weight: 600;
        line-height: 1.2;
      }

      .status-text {
        margin: 0;
        color: #6c757d;
        font-size: 14px;
        font-weight: 400;
        margin-top: 2px;
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
        background: #007bff;
        color: white;
        padding: 12px 16px;
        border-radius: 16px 16px 4px 16px;
        border: 1px solid #007bff;
      }

      .bot-message {
        background: #f8f9fa;
        color: #212529;
        padding: 12px 16px;
        border-radius: 16px 16px 16px 4px;
        border: 1px solid #dee2e6;
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
      }

      .typing-indicator {
        animation: fadeIn 0.3s ease-in;
      }

      .typing-message {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 12px 16px;
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
      }

      .chat-input {
        display: flex;
        gap: 12px;
        align-items: stretch;
      }

      .message-input {
        flex: 1;
        padding: 12px 16px;
        font-size: 15px;
        border: 1px solid #ced4da;
        border-radius: 6px;
        outline: none;
        transition: border-color 0.15s ease-in-out;
        background: #ffffff;
        font-family: inherit;
      }

      .message-input:focus {
        border-color: #007bff;
        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
      }

      .message-input:disabled {
        background: #f8f9fa;
        cursor: not-allowed;
        color: #6c757d;
      }

      .send-button {
        padding: 12px 24px;
        background: #007bff;
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
        background: #0056b3;
      }

      .send-button:disabled {
        background: #6c757d;
        cursor: not-allowed;
      }

      .loading-text {
        display: inline-block;
        animation: pulse 1s infinite;
      }

      .input-footer {
        text-align: center;
        margin-top: 12px;
      }

      .input-footer small {
        color: #6c757d;
        font-size: 13px;
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

      @keyframes pulse {
        0%, 100% {
          opacity: 1;
        }
        50% {
          opacity: 0.5;
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
          font-size: 18px;
        }
        
        .chat-header {
          padding: 20px;
        }

        .message-input {
          font-size: 16px; /* Evita zoom en móviles */
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
          font-size: 12px;
        }
        
        .header-info h2 {
          font-size: 16px;
        }
        
        .status-text {
          font-size: 13px;
        }
      }

      /* Scrollbar para el chat interno */
      .chat-messages::-webkit-scrollbar {
        width: 8px;
      }

      .chat-messages::-webkit-scrollbar-track {
        background: #f1f3f4;
        border-radius: 4px;
        margin: 10px 0;
      }

      .chat-messages::-webkit-scrollbar-thumb {
        background: #ced4da;
        border-radius: 4px;
      }

      .chat-messages::-webkit-scrollbar-thumb:hover {
        background: #adb5bd;
      }

      /* Mejoras para accesibilidad táctil */
      .send-button {
        min-height: 44px;
      }

      .message-input {
        min-height: 44px;
      }

      /* Contraste mejorado */
      .user-message {
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      }

      .bot-message {
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
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
  private shouldScrollToBottom = false;

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    this.addBotMessage('Bienvenido al Parque Industrial Polo 52.\n\nMi nombre es POLO y estoy aquí para ayudarle con consultas sobre las empresas y servicios disponibles en el parque. ¿En qué puedo asistirle?');
  }

  ngAfterViewChecked() {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
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