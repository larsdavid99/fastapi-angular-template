export interface ApiError {
  readonly status: number;
  readonly message: string;
  readonly timestamp: string;
}
