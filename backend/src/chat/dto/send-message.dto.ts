import { IsArray, IsNotEmpty, IsString } from 'class-validator';

export class SendMessageDto {
  @IsString()
  @IsNotEmpty()
  query!: string;
}

export class MessageSourceDto {
  documentId?: string;
  page?: number;
  text?: string;
  score?: number;
}

export class ChatResponseDto {
  response!: string;
  sources!: MessageSourceDto[];
  latencyMs!: number;
}
