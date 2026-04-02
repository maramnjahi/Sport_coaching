import { UserRole } from '../../database/entities/role.enum';

export class AuthResponseDto {
  accessToken!: string;
  user?: {
    id: string;
    email: string;
    role: UserRole;
  };
}
