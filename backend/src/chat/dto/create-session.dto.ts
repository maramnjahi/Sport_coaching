import { IsEnum, IsNotEmpty, IsString } from 'class-validator';
import { SportType } from '../../database/entities/sport.enum';

export class CreateSessionDto {
  @IsEnum(SportType)
  sport!: SportType;

  @IsString()
  @IsNotEmpty()
  title!: string;
}
