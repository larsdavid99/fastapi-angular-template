import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/hello/hello').then(
        (m: typeof import('./pages/hello/hello')) => m.HelloPageComponent,
      ),
  },
  {
    path: '**',
    redirectTo: '',
  },
];
