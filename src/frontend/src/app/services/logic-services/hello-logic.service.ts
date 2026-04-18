import { Injectable, Signal, WritableSignal, inject, signal } from '@angular/core';

import { ApiError } from '../../models/api-error.model';
import { HelloResponse } from '../../models/hello-response.model';
import { HelloDataService } from '../data-services/hello-data.service';

@Injectable({ providedIn: 'root' })
export class HelloLogicService {
  private readonly dataService: HelloDataService = inject(HelloDataService);

  private readonly resultSignal: WritableSignal<HelloResponse | null> = signal(null);
  private readonly loadingSignal: WritableSignal<boolean> = signal(false);
  private readonly errorSignal: WritableSignal<string | null> = signal(null);

  readonly result: Signal<HelloResponse | null> = this.resultSignal.asReadonly();
  readonly isLoading: Signal<boolean> = this.loadingSignal.asReadonly();
  readonly error: Signal<string | null> = this.errorSignal.asReadonly();

  greet(name: string): void {
    const trimmed: string = name.trim();
    if (!trimmed) return;

    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    this.dataService.hello({ name: trimmed }).subscribe({
      next: (response: HelloResponse) => {
        this.resultSignal.set(response);
        this.loadingSignal.set(false);
      },
      error: (err: ApiError) => {
        this.errorSignal.set(err.message);
        this.loadingSignal.set(false);
      },
    });
  }
}
