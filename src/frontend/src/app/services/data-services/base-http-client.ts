import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ApiError } from '../../models/api-error.model';

export abstract class BaseHttpClient {
  protected readonly http: HttpClient = inject(HttpClient);
  protected abstract readonly resourcePath: string;

  protected post<T>(endpoint: string, body: unknown): Observable<T> {
    return this.http
      .post<T>(`${this.resourcePath}${endpoint}`, body)
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  protected get<T>(endpoint: string): Observable<T> {
    return this.http
      .get<T>(`${this.resourcePath}${endpoint}`)
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    const apiError: ApiError = {
      status: error.status,
      message: (error.error as { detail?: string })?.detail ?? error.message ?? 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
    };
    return throwError(() => apiError);
  }
}
