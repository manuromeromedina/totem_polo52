import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ResetPasswordPublicComponent } from './password-reset.component';

describe('ResetPasswordComponent', () => {
  let component: ResetPasswordPublicComponent;
  let fixture: ComponentFixture<ResetPasswordPublicComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ResetPasswordPublicComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ResetPasswordPublicComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
