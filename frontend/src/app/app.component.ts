import { Component } from '@angular/core';
import { ChatbotComponent } from './chat/chat.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ChatbotComponent],
  template: `
    <app-chat></app-chat>
  `,
})
export class AppComponent {
  title = 'frontend'; 
}