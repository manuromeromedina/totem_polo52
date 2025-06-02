import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// Definir interfaces para la solicitud y la respuesta
interface ChatMessageRequest {
  message: string;
  history: Array<{ user: string; assistant: string }>;
}

interface ChatMessageResponse {
  reply: string;
}

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private apiUrl = 'http://localhost:8000/chat/';  // Añadir la barra final

  constructor(private http: HttpClient) {}

  sendMessage(message: string, history: Array<{ user: string; assistant: string }> = []): Observable<ChatMessageResponse> {
    const payload: ChatMessageRequest = { message, history };
    return this.http.post<ChatMessageResponse>(this.apiUrl, payload);
  }
}