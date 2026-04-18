# Frontend Guidelines (Angular)

This is an **Angular** web application. Code examples below are **conceptual illustrations** of patterns—adapt to your specific use case.

## TypeScript & ESLint Rules

**Explicit types are required.** Do not rely on type inference.

| Context | Required | Example |
|---------|----------|---------|
| Function return types | Yes | `getData(): Observable<User>` |
| Member variables | Yes | `private readonly user: User \| null = null;` |
| Parameters | Yes | `load(id: string): void` |
| Variable declarations | Yes | `const users: User[] = await fetch();` |
| Array/Object destructuring | No | `const { name } = user;` |
| Arrow function params (inline) | No | `items.map(x => x.id)` |

Avoid `any`; use `unknown` when type is uncertain.

## Angular Best Practices

### Components
- **Standalone only** (do NOT set `standalone: true`—it's default in Angular 20+)
- Use `changeDetection: ChangeDetectionStrategy.OnPush`
- Use `input()` / `output()` functions, not decorators
- Use `host` object in decorator instead of `@HostBinding` / `@HostListener`
- Selectors: `app-kebab-case` for components, `[appCamelCase]` for directives
- Prefer inline templates for small components
- Prefer Reactive forms over Template-driven

### Templates
- Use native control flow: `@if`, `@for`, `@switch` (not `*ngIf`, `*ngFor`)
- Use `async` pipe for observables
- Use `class` / `style` bindings (not `ngClass` / `ngStyle`)
- No arrow functions in templates
- No global assumptions (`new Date()`, etc.)

### Images
- Use `NgOptimizedImage` for static images (not for base64)

## State Management (Signals)

- Use `signal()` for local state, `computed()` for derived state
- Use `update()` or `set()` (not `mutate`)

## Accessibility

- Must pass AXE checks and WCAG AA (focus, contrast, ARIA)
- Templates linted for: alt text, valid ARIA, form labels, keyboard nav

## SCSS Architecture

### Design Tokens
- All design tokens are CSS custom properties defined in `src/styles/_tokens.scss`
- Colors, spacing, typography, borders, shadows, transitions, z-index, layout constants
- Reference via `var(--color-bg-primary)`, `var(--space-md)`, etc.

### Mixins
- Reusable mixins in `src/styles/_mixins.scss`
- Import in component SCSS: `@use 'mixins' as m;` (short path via `stylePreprocessorOptions`)
- Key mixins: `card`, `scrollable`, `active-line-indicator`, `button-primary`, `button-ghost`, `toggle-group`, `toggle-option`, `input-field`, `flex-center`, `flex-between`, `badge`, `timestamp`, `breakpoint-*`

### Component Styling
- Use BEM-ish naming: `.block__element--modifier`
- Scope styles via component SCSS files (Angular encapsulation)
- Use `@include m.mixin-name` instead of duplicating patterns
- No global utility classes in templates — use mixins in component SCSS
- Responsive design via `@include m.breakpoint-md { ... }` mixins

## Service Architecture

```
Components → Logic Services → Data Services → BaseHttpClient → API
```

### Data Services (`src/app/services/data-services/`)
- Extend `BaseHttpClient`, define `resourcePath`
- Return raw `Observable<T>`—no state, no business logic

```typescript
@Injectable({ providedIn: 'root' })
export class HelloDataService extends BaseHttpClient {
  protected readonly resourcePath: string = '/api';

  hello(request: HelloRequest): Observable<HelloResponse> {
    return this.post<HelloResponse>('/hello', request);
  }
}
```

### Logic Services (`src/app/services/logic-services/`)
- Inject data services, manage state with signals
- Components consume logic services only

```typescript
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
    this.loadingSignal.set(true);
    this.errorSignal.set(null);
    this.dataService.hello({ name }).subscribe({
      next: (res: HelloResponse) => { this.resultSignal.set(res); this.loadingSignal.set(false); },
      error: (err: ApiError) => { this.errorSignal.set(err.message); this.loadingSignal.set(false); },
    });
  }
}
```

### Service Rules
- Use `inject()` (not constructor injection)
- Use `providedIn: 'root'` for singletons
- Components → Logic Services only (never Data Services directly)
- Handle errors in Logic Services via `ApiError` type
