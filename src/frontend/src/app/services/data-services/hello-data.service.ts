import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { HelloRequest } from '../../models/hello-request.model';
import { HelloResponse } from '../../models/hello-response.model';
import { BaseHttpClient } from './base-http-client';

@Injectable({ providedIn: 'root' })
export class HelloDataService extends BaseHttpClient {
  protected readonly resourcePath: string = '/api';

  hello(request: HelloRequest): Observable<HelloResponse> {
    return this.post<HelloResponse>('/hello', request);
  }
}
