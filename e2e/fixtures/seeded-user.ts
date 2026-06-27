import { APIRequestContext, request } from '@playwright/test';
import { randomUUID } from 'node:crypto';

export interface SeededUser {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
}

export interface CreatedUser extends SeededUser {
  /** API-base used for creation, e.g. http://localhost/api */
  apiBase: string;
}

/**
 * Build a unique seed user. Does NOT call the API.
 */
export function makeSeedUser(prefix = 'e2e'): SeededUser {
  const id = randomUUID();
  return {
    email: `${prefix}+${id}@example.test`,
    password: 'TestPass123!',
    firstName: 'E2E',
    lastName: 'User',
  };
}

/**
 * Resolve the API base from E2E_BASE_URL (default http://localhost).
 */
export function apiBase(): string {
  const root = (process.env.E2E_BASE_URL ?? 'http://localhost').replace(/\/$/, '');
  return `${root}/api`;
}

/**
 * Register a new user via the public auth endpoint. Returns the created user.
 * Throws if the backend rejects the registration.
 */
export async function registerSeedUser(
  apiContext: APIRequestContext,
  user: SeededUser = makeSeedUser(),
): Promise<CreatedUser> {
  const base = apiBase();
  const resp = await apiContext.post(`${base}/auth/register`, {
    data: {
      email: user.email,
      password: user.password,
      first_name: user.firstName,
      last_name: user.lastName,
    },
  });
  if (!resp.ok()) {
    const body = await resp.text();
    throw new Error(
      `Failed to register seed user (${resp.status()}): ${body.slice(0, 400)}`,
    );
  }
  return { ...user, apiBase: base };
}

/**
 * Convenience: create an APIRequestContext, register a user, return both.
 * Caller is responsible for disposing the context.
 */
export async function createSeedUser(): Promise<{
  user: CreatedUser;
  apiContext: APIRequestContext;
}> {
  const apiContext = await request.newContext();
  const user = await registerSeedUser(apiContext);
  return { user, apiContext };
}
