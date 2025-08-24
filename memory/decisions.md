
# Decisions

- **[2025-08-22]** Decided to create dedicated services (`authService`, `accountService`) on the frontend to mirror the backend API structure. This keeps concerns separated and follows the existing pattern of `transactionService`.
- **[2025-08-22]** The `apiClient`'s built-in silent token refresh is sufficient. No additional logic is needed in the UI components to handle token expiration.
- **[2025-08-22]** Will use `sessionStorage` via the `secureStorage` service for JWTs, as it's a reasonable default for security without the complexity of httpOnly cookies for this stage of development.
- **[2025-08-22]** The API base URL will be managed by the `VITE_API_URL` environment variable in the frontend, which is the standard for Vite projects.
