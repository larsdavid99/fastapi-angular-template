import { ChangeDetectionStrategy, Component, Signal, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { HelloResponse } from '../../models/hello-response.model';
import { HelloLogicService } from '../../services/logic-services/hello-logic.service';

@Component({
  selector: 'app-hello',
  imports: [FormsModule],
  templateUrl: './hello.html',
  styleUrl: './hello.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HelloPageComponent {
  private readonly logic: HelloLogicService = inject(HelloLogicService);

  readonly name = signal<string>('');
  readonly result: Signal<HelloResponse | null> = this.logic.result;
  readonly isLoading: Signal<boolean> = this.logic.isLoading;
  readonly error: Signal<string | null> = this.logic.error;

  submit(): void {
    this.logic.greet(this.name());
  }
}
