import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SidebarPoloComponent } from './sidebar-polo.component';

describe('SidebarPoloComponent', () => {
  let component: SidebarPoloComponent;
  let fixture: ComponentFixture<SidebarPoloComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarPoloComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SidebarPoloComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
