import { IsEmail, IsEnum, IsNotEmpty, IsOptional, IsString, MinLength } from 'class-validator';
import { SportType } from '../../database/entities/sport.enum';
import { UserRole } from '../../database/entities/role.enum';

export class RegisterDto {
  @IsEmail()
  email!: string;

  @IsString()
  @MinLength(8)
  password!: string;

  @IsEnum(UserRole)
  @IsOptional()
  role?: UserRole;

  @IsEnum(SportType)
  @IsOptional()
  sport?: SportType;

  @IsString()
  @IsOptional()
  @IsNotEmpty()
  level?: string;
}