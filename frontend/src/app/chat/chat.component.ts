
import { Component, OnInit } from '@angular/core';
import { ChatService } from './chat.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

interface Message {
  sender: 'user' | 'bot';
  content: string;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [FormsModule, CommonModule], 
  template: `
    <div class="chat-container">
      <h2>Chatbot del Parque Industrial Polo 52</h2>
      <div class="chat-messages">
        <div *ngFor="let message of messages" [class]="message.sender === 'user' ? 'user-message' : 'bot-message'">
          {{ message.content }}
        </div>
      </div>
      <div class="chat-input">
        <input [(ngModel)]="userMessage" placeholder="Haz una pregunta sobre las empresas..." (keyup.enter)="sendMessage()">
        <button (click)="sendMessage()">Enviar</button>
      </div>
    </div>
  `,
  styles: [
    `
      .chat-container {
        text-align: center;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        font-family: Arial, sans-serif;
      }
      .chat-messages {
        height: 500px;
        overflow-y: auto;
        border: 1px solid #ccc;
        padding: 10px;
        margin-bottom: 10px;
        display: flex; 
        flex-direction: column; 
        border-radius:15px;
      }
      .user-message {
        text-align: right;
        background-color:rgb(221, 241, 250);
        padding: 15px;
        margin: 10px 0;
        border-radius: 15px;
        display: block; 
        max-width: 70%; 
        word-wrap: break-word; 
        margin-left: auto;
      }
      .bot-message {
        text-align: left;
        background-color:rgb(242, 235, 235);
        padding: 10px;
        margin: 5px 0;
        border-radius: 15px;
        display: inline-block; 
        max-width: 70%; 
        word-wrap: break-word;
      }
      .chat-input {
        display: flex;
        gap: 10px;
      }
      input {
        flex: 1;
        padding: 10px;
        font-size: 16px;
        border-radius: 10px;
      }
      button {
        padding: 10px 20px;
        background-color:rgb(145, 15, 15);
        color: white;
        border: none;
        cursor: pointer;
        border-radius: 10px;
      }
      button:hover {
        background-color:rgb(179, 36, 0);
      }
    `
  ]
})
export class ChatbotComponent implements OnInit {
  messages: Message[] = [];
  userMessage: string = '';

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    this.messages.push({
      sender: 'bot',
      content: '¡Bienvenido al Parque Industrial Polo 52! Pregúntame sobre las empresas del parque.'
    });
  }

  sendMessage() {
    if (this.userMessage.trim()) {
      this.messages.push({ sender: 'user', content: this.userMessage });
      this.chatService.sendMessage(this.userMessage).subscribe({
        next: (response: any) => {
          this.messages.push({ sender: 'bot', content: response.reply });
        },
        error: (error) => {
          this.messages.push({ sender: 'bot', content: 'Lo siento, hubo un error. Intenta de nuevo.' });
          console.error(error);
        }
      });
      this.userMessage = '';
    }
  }
}
  