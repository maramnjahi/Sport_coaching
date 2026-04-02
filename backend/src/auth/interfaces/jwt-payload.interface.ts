import { UserRole } from '../../database/entities/role.enum';

export interface JwtPayload {
  sub: string;
  email: string;
  role: UserRole;
}