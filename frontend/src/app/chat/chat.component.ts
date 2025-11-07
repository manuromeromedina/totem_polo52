// chat.component.ts
import {
  Component,
  OnInit,
  ElementRef,
  ViewChild,
  AfterViewChecked,
} from '@angular/core';
import { ChatService, VoiceChatResponse } from './chat.service';
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
            <p class="status-text">
              {{ isTyping ? 'Escribiendo...' : 'Disponible para consultas' }}
            </p>
          </div>
        </div>
        <div class="header-actions">
          <button
            (click)="toggleTheme()"
            aria-label="Cambiar modo claro/oscuro"
            class="mode-toggle-btn"
          >
            <svg
              *ngIf="isDarkMode"
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="feather feather-sun"
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="12" r="5"></circle>
              <line x1="12" y1="1" x2="12" y2="3"></line>
              <line x1="12" y1="21" x2="12" y2="23"></line>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
              <line x1="1" y1="12" x2="3" y2="12"></line>
              <line x1="21" y1="12" x2="23" y2="12"></line>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>

            <svg
              *ngIf="!isDarkMode"
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="feather feather-moon"
              viewBox="0 0 24 24"
            >
              <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>
            </svg>
          </button>
          <app-logout-button></app-logout-button>
        </div>
      </div>

      <div class="chat-container">
        <div class="chat-panel">
          <div class="panel-card messages-card">
            <div class="panel-title">
              <div class="panel-title-icon">
                <span class="material-symbols-outlined">robot_2</span>
              </div>
              <div>
                <h3>Chat con POLO Bot</h3>
                <small>Tu asistente del Parque Industrial POLO 52</small>
              </div>
            </div>

            <div class="chat-messages" #messagesContainer>
              <div
                *ngFor="let message of messages; trackBy: trackByMessageId"
                class="message-wrapper"
                [class.user-wrapper]="message.sender === 'user'"
                [class.bot-wrapper]="message.sender === 'bot'"
              >
                <div
                  class="message-content"
                  [class]="
                    message.sender === 'user' ? 'user-message' : 'bot-message'
                  "
                >
                  <div
                    class="message-text"
                    [innerHTML]="formatMessage(message.content)"
                  ></div>
                  <div class="message-time">
                    {{ formatTime(message.timestamp) }}
                  </div>
                </div>
              </div>

              <div
                *ngIf="isTyping"
                class="message-wrapper bot-wrapper typing-indicator"
              >
                <div class="bot-message typing-message">
                  <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="panel-card input-card">
            <div class="chat-input">
              <input
                #messageInput
                [(ngModel)]="userMessage"
                placeholder="Escribe tu consulta..."
                (keyup.enter)="sendMessage()"
                [disabled]="isTyping"
                class="message-input"
              />
              <button
                type="button"
                (click)="sendMessage()"
                [disabled]="!userMessage.trim() || isTyping"
                class="send-button"
              >
                <span *ngIf="!isTyping" class="material-symbols-outlined">
                  send
                </span>
                <span *ngIf="isTyping" class="loading-text">...</span>
              </button>
            </div>
            <div class="input-footer">
              Presion&aacute; Enter o el bot&oacute;n para enviar tu consulta
            </div>
          </div>
        </div>

        <aside class="sidebar">
          <div class="sidebar-card quick-queries-card">
            <div class="card-header">
              <span class="material-symbols-outlined">bolt</span>
              <div>
                <h3>Consultas R&aacute;pidas</h3>
                <p>Las preguntas que m&aacute;s recibimos</p>
              </div>
            </div>
            <button
              type="button"
              class="quick-question"
              *ngFor="let question of quickQuestions"
              (click)="handleQuickQuestion(question)"
              [disabled]="isTyping"
            >
              <span>{{ question }}</span>
              <span class="material-symbols-outlined">arrow_forward</span>
            </button>
          </div>

          <div class="sidebar-card contact-card">
            <div class="card-header">
              <span class="material-symbols-outlined">support_agent</span>
              <div>
                <h3>Conexi&oacute;n Directa</h3>
                <p>Equipo POLO 52</p>
              </div>
            </div>
            <ul class="contact-list">
              <li>
                <span class="material-symbols-outlined">call</span>
                <div>
                  <strong>+54 351 123-4567</strong>
                  <small>Atenci&oacute;n comercial</small>
                </div>
              </li>
              <li>
                <span class="material-symbols-outlined">mail</span>
                <div>
                  <strong>info&#64;polo52.com</strong>
                  <small>Contacto general</small>
                </div>
              </li>

              <li>
                <span class="material-symbols-outlined">schedule</span>
                <div>
                  <strong>24/7 Disponible</strong>
                  <small>Siempre listos para ayudarte</small>
                </div>
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  `,

  styles: [
    `
      @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');

      :host {
        display: block;
      }

      :host {
        display: block;
        height: 100vh;
      }

      body,
      html {
        height: 100%;
        margin: 0;
        overflow: hidden;
        scrollbar-width: none;
      }

      body::-webkit-scrollbar {
        display: none;
      }

      .chat-wrapper {
        height: 100vh;
        display: flex;
        flex-direction: column;
        padding: 4px 10px 12px;
        background: linear-gradient(
          120deg,
          #e6f0ff 0%,
          #f7f9fc 60%,
          #eef2f6 100%
        );
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #495057;
        font-size: clamp(0.88rem, 0.9vw, 0.98rem);
        overflow: hidden;
        box-sizing: border-box;
      }

      .chat-wrapper.dark-mode {
        background: linear-gradient(135deg, #0f0f0f 0%, #1c1c1c 60%, #222 100%);
        color: #e0e0e0;
      }

      .chat-header {
        background: #ffffff;
        padding: 10px 14px;
        border-bottom: 1px solid #dee2e6;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
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

      .mode-toggle-btn {
        background: transparent;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 6px;
        cursor: pointer;
        transition: all 0.3s ease;
        color: #495057;
      }

      .mode-toggle-btn:hover {
        border-color: #adb5bd;
        background: rgba(73, 80, 87, 0.05);
      }

      .dark-mode .mode-toggle-btn {
        border-color: #555;
        color: #f1f1f1;
      }

      .bot-avatar {
        position: relative;
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: linear-gradient(135deg, #9a9a9a, #cfcfcf);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 12px;
      }

      .avatar-icon {
        letter-spacing: 0.5px;
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
      }

      .dark-mode .status-text {
        color: #a0a0a0;
      }

      .chat-container {
        flex: 1;
        min-height: 0;
        display: flex;
        gap: 14px;
        padding: 10px 8px 12px;
        width: 100%;
        max-width: 1180px;
        margin: 0 auto;
        box-sizing: border-box;
      }

      .chat-panel {
        flex: 2.4;
        display: flex;
        flex-direction: column;
        gap: 14px;
        min-height: 0;
      }

      .sidebar {
        flex: 0.6;
        max-width: 260px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-height: 0;
      }

      .panel-card,
      .sidebar-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 14px;
        padding: 12px;
        border: 1px solid #edf0f2;
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.05);
        backdrop-filter: blur(4px);
      }

      .dark-mode .panel-card,
      .dark-mode .sidebar-card {
        background: #272727;
        border: 1px solid #3a3a3a;
        box-shadow: 0 16px 32px rgba(0, 0, 0, 0.45);
      }

      .messages-card {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-height: 0; /* allow inner scroll */
      }

      .panel-title {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 16px;
      }

      .panel-title-icon {
        width: 34px;
        height: 34px;
        border-radius: 12px;
        background: #eef2ff;
        color: #4254ff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
      }

      .panel-title h3 {
        margin: 0;
        color: #1d1f2c;
        font-size: 17px;
      }

      .panel-title small {
        display: block;
        color: #6c757d;
        margin-top: 2px;
        font-size: 12px;
      }

      .dark-mode .panel-title-icon {
        background: #333;
        color: #8ab4ff;
      }

      .dark-mode .panel-title h3 {
        color: #f1f1f1;
      }

      .dark-mode .panel-title small {
        color: #b0b0b0;
      }

      .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding-right: 6px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        min-height: 0;
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
        max-width: 65%;
        position: relative;
      }

      .user-message {
        background: #495057;
        color: white;
        padding: 10px 14px;
        border-radius: 14px 14px 4px 14px;
        border: 1px solid #495057;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      }

      .dark-mode .user-message {
        background: #e9ecef;
        color: #212529;
        border: 1px solid #e9ecef;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
      }

      .bot-message {
        background: #f8f9fa;
        color: #212529;
        padding: 10px 14px;
        border-radius: 14px 14px 14px 4px;
        border: 1px solid #dee2e6;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
      }

      .dark-mode .bot-message {
        background: #383838;
        color: #f5f5f5;
        border: 1px solid #505050;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
      }

      .message-text {
        white-space: pre-line;
        line-height: 1.5;
      }

      .message-time {
        font-size: 11px;
        opacity: 0.6;
        margin-top: 4px;
        text-align: right;
      }

      .typing-message {
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }

      .typing-dots span {
        width: 6px;
        height: 6px;
        background: #495057;
        display: inline-block;
        border-radius: 50%;
        animation: bounce 1.4s infinite;
      }

      .typing-dots span:nth-child(2) {
        animation-delay: 0.2s;
      }

      .typing-dots span:nth-child(3) {
        animation-delay: 0.4s;
      }

      .dark-mode .typing-dots span {
        background: #f1f1f1;
      }

      .input-card {
        padding: 16px;
      }

      .chat-input {
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #e1e5ec;
        border-radius: 14px;
        padding: 8px 12px;
        background: #f8fafc;
      }

      .dark-mode .chat-input {
        background: #1f1f1f;
        border: 1px solid #3a3a3a;
      }

      .message-input {
        flex: 1;
        border: none;
        background: transparent;
        font-size: 15px;
        color: inherit;
      }

      .message-input:focus {
        outline: none;
      }

      .send-button {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        border: none;
        background: #495057;
        color: white;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: transform 0.2s ease, opacity 0.2s ease;
      }

      .send-button:not(:disabled):hover {
        transform: translateY(-2px);
      }

      .send-button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      .dark-mode .send-button {
        background: #f1f3f5;
        color: #212529;
      }

      .loading-text {
        font-size: 18px;
        letter-spacing: 2px;
      }

      .input-footer {
        margin-top: 12px;
        text-align: center;
        font-size: 14px;
        color: #6c757d;
      }

      .dark-mode .input-footer {
        color: #b4b4b4;
      }

      .card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }

      .card-header h3 {
        margin: 0;
        font-size: 15px;
        color: #1d1f2c;
      }

      .card-header p {
        margin: 0;
        font-size: 11px;
        color: #6c757d;
      }

      .card-header .material-symbols-outlined {
        font-size: 26px;
        color: #ff8a00;
      }

      .dark-mode .card-header h3 {
        color: #f1f1f1;
      }

      .dark-mode .card-header p {
        color: #b0b0b0;
      }

      .dark-mode .card-header .material-symbols-outlined {
        color: #f0b35a;
      }

      .quick-question {
        width: 100%;
        border: 1px solid #e4e7ec;
        background: #fff;
        border-radius: 12px;
        padding: 6px 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 12px;
        color: #1f1f1f;
        cursor: pointer;
        transition: border-color 0.2s ease, box-shadow 0.2s ease,
          transform 0.2s ease;
      }

      .quick-question + .quick-question {
        margin-top: 12px;
      }

      .quick-question:hover:not(:disabled) {
        border-color: #b4c2ff;
        box-shadow: 0 12px 20px rgba(56, 72, 255, 0.12);
        transform: translateY(-1px);
      }

      .quick-question:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .quick-question .material-symbols-outlined {
        font-size: 18px;
        color: #98a2ff;
      }

      .dark-mode .quick-question {
        background: #1f1f1f;
        color: #f5f5f5;
        border: 1px solid #3a3a3a;
      }

      .dark-mode .quick-question .material-symbols-outlined {
        color: #8ab4ff;
      }

      .contact-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .contact-list li {
        display: flex;
        gap: 8px;
        align-items: flex-start;
        padding-bottom: 8px;
        border-bottom: 1px solid #edf0f2;
      }

      .contact-list li:last-child {
        border-bottom: none;
      }

      .contact-list strong {
        display: block;
        color: #1d1f2c;
        font-size: 13px;
      }

      .contact-list small {
        color: #6c757d;
        font-size: 11px;
      }

      .contact-list .material-symbols-outlined {
        font-size: 22px;
        color: #4254ff;
      }

      .dark-mode .contact-list li {
        border-color: #373737;
      }

      .dark-mode .contact-list strong {
        color: #f5f5f5;
      }

      .dark-mode .contact-list small {
        color: #b0b0b0;
      }

      .dark-mode .contact-list .material-symbols-outlined {
        color: #8ab4ff;
      }

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

      @media (max-width: 1200px), (max-height: 760px) {
        .chat-container {
          padding: 14px 10px;
          gap: 14px;
          height: calc(100vh - 140px);
        }

        .panel-card,
        .sidebar-card {
          padding: 16px;
        }

        .message-content {
          max-width: 75%;
        }
      }

      @media (max-width: 992px) {
        .chat-container {
          flex-direction: column;
          padding: 14px 10px 20px;
        }

        .chat-panel,
        .sidebar {
          gap: 14px;
        }

        .sidebar {
          flex-direction: row;
          flex-wrap: wrap;
        }

        .sidebar-card {
          flex: 1 1 220px;
        }
      }

      @media (max-width: 768px) {
        .chat-container {
          padding: 12px 8px 18px;
        }

        .panel-card,
        .sidebar-card {
          padding: 14px;
        }

        .message-content {
          max-width: 85%;
        }
      }

      @media (max-width: 576px) {
        .chat-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 16px;
        }

        .header-actions {
          width: 100%;
          justify-content: space-between;
        }

        .chat-panel {
          gap: 16px;
        }

        .chat-input {
          flex-direction: column;
          align-items: stretch;
        }

        .send-button {
          width: 100%;
        }
      }

      @media (orientation: portrait) and (min-width: 577px) {
        .chat-container {
          flex-direction: column;
          max-width: 640px;
          height: auto;
        }

        .sidebar {
          flex-direction: column;
        }

        .message-content {
          max-width: 80%;
        }
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
          transform: translateY(8px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      @keyframes bounce {
        0%,
        80%,
        100% {
          transform: scale(0);
        }
        40% {
          transform: scale(1);
        }
      }
    `,
  ],
})
export class ChatbotComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('messageInput') messageInput!: ElementRef;

  messages: Message[] = [];
  userMessage = '';
  isTyping = false;
  isDarkMode = false;
  quickQuestions: string[] = [];
  private readonly defaultQuickQuestions = [
    'Disponibilidad de lotes',
    'Empresas instaladas en el parque',
    'Servicios disponibles',
    'Información de contacto',
  ];
  private readonly popularQuestionsKey = 'chatPopularQueries';
  private questionStats: Record<string, { count: number; display: string }> =
    {};

  private shouldScrollToBottom = false;

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    const savedTheme = localStorage.getItem('chatTheme');
    this.isDarkMode = savedTheme === 'dark';
    this.loadPopularQuestions();
    this.addBotMessage(
      'Bienvenido al Parque Industrial POLO 52.\n\nMi nombre es POLO y estoy aqu\u00ed para ayudarte con consultas sobre las empresas y servicios disponibles en el parque. \u00bfEn qu\u00e9 puedo asistirte?'
    );
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

  handleQuickQuestion(question: string) {
    if (this.isTyping) return;
    this.userMessage = question;
    this.sendMessage();
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
      id: this.generateMessageId(),
    });
    this.shouldScrollToBottom = true;
    this.registerQuestion(content);
  }

  private addBotMessage(content: string) {
    this.messages.push({
      sender: 'bot',
      content,
      timestamp: new Date(),
      id: this.generateMessageId(),
    });
    this.shouldScrollToBottom = true;
  }

  private scrollToBottom(): void {
    try {
      if (this.messagesContainer) {
        const element = this.messagesContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      }
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  formatMessage(content: string): string {
    return content.replace(/\n/g, '<br>');
  }

  formatTime(timestamp: Date): string {
    return timestamp.toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private getChatHistory(): Array<{ user: string; assistant: string }> {
    const history: Array<{ user: string; assistant: string }> = [];
    let lastUserMessage: string | null = null;

    for (const message of this.messages) {
      if (message.sender === 'user') lastUserMessage = message.content;
      else if (message.sender === 'bot' && lastUserMessage) {
        history.push({ user: lastUserMessage, assistant: message.content });
        lastUserMessage = null;
      }
    }
    return history;
  }

  private loadPopularQuestions() {
    try {
      const stored = localStorage.getItem(this.popularQuestionsKey);
      if (stored) this.questionStats = JSON.parse(stored);
    } catch (error) {
      console.warn('No se pudieron cargar las consultas populares:', error);
      this.questionStats = {};
    }
    this.updateQuickQuestions();
  }

  private savePopularQuestions() {
    try {
      localStorage.setItem(
        this.popularQuestionsKey,
        JSON.stringify(this.questionStats)
      );
    } catch (error) {
      console.warn('No se pudieron guardar las consultas populares:', error);
    }
  }

  private updateQuickQuestions() {
    const stats = Object.values(this.questionStats)
      .filter((item) => item.count >= 2)
      .sort((a, b) => b.count - a.count);

    const top = stats.slice(0, 4).map((item) => item.display);

    if (top.length < 4) {
      const remainingDefaults = this.defaultQuickQuestions.filter(
        (question) => !top.includes(question)
      );
      this.quickQuestions = [...top, ...remainingDefaults].slice(0, 4);
    } else {
      this.quickQuestions = top;
    }
  }

  private registerQuestion(content: string) {
    const normalized = content.trim().toLowerCase();
    if (!normalized) return;

    if (this.questionStats[normalized]) {
      this.questionStats[normalized].count++;
      this.questionStats[normalized].display = content.trim();
    } else {
      this.questionStats[normalized] = { count: 1, display: content.trim() };
    }

    this.savePopularQuestions();
    this.updateQuickQuestions();
  }

  async sendMessage() {
    if (!this.userMessage.trim() || this.isTyping) return;

    const messageToSend = this.userMessage.trim();
    this.addUserMessage(messageToSend);
    this.userMessage = '';
    this.isTyping = true;

    const initialDelay = Math.min(300 + messageToSend.length * 10, 800);

    setTimeout(() => {
      const history = this.getChatHistory();

      this.chatService.sendMessage(messageToSend, history).subscribe({
        next: (resp: VoiceChatResponse) => {
          const text = resp?.data?.text || 'Respuesta invÃ¡lida.';
          this.simulateTyping(text);

          const b64 = resp?.data?.audio_base64;
          if (b64) {
            const audio = new Audio(`data:audio/mpeg;base64,${b64}`);
            audio.play().catch(console.error);
          }
        },
        error: (error) => {
          console.error('Error en la solicitud:', error);
          const msg =
            error.status === 0
              ? 'No se pudo conectar con el servidor. Verifique la conexiÃ³n.'
              : error.status >= 500
              ? 'El servidor estÃ¡ experimentando problemas. Intente mÃ¡s tarde.'
              : 'Lo siento, hubo un problema tÃ©cnico. Por favor, intente nuevamente.';
          this.simulateTyping(msg);
        },
      });
    }, initialDelay);

    setTimeout(() => {
      if (this.messageInput) this.messageInput.nativeElement.focus();
    }, 100);
  }

  private simulateTyping(message: string) {
    const botMessage: Message = {
      sender: 'bot',
      content: '',
      timestamp: new Date(),
      id: this.generateMessageId(),
    };

    this.messages.push(botMessage);
    this.shouldScrollToBottom = true;

    let currentIndex = 0;
    const characters = message.split('');

    const typeCharacter = () => {
      if (currentIndex < characters.length) {
        botMessage.content += characters[currentIndex];
        this.shouldScrollToBottom = true;
        currentIndex++;

        let delay = 25;
        if (['.', '!'].includes(characters[currentIndex - 1])) delay = 100;
        else if ([',', ':'].includes(characters[currentIndex - 1])) delay = 50;
        else if (characters[currentIndex - 1] === ' ') delay = 15;
        else delay = Math.random() * 20 + 15;

        setTimeout(typeCharacter, delay);
      } else {
        this.isTyping = false;
      }
    };

    setTimeout(typeCharacter, 100);
  }
}
