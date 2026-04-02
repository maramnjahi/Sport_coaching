import { Body, Controller, Get, Param, Post, Req, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { ChatService } from './chat.service';
import { CreateSessionDto } from './dto/create-session.dto';
import { SendMessageDto } from './dto/send-message.dto';

type JwtRequest = {
  user: {
    sub: string;
    email: string;
    role: string;
  };
};

@UseGuards(JwtAuthGuard)
@Controller('chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post('sessions')
  async createSession(
    @Req() req: JwtRequest,
    @Body() dto: CreateSessionDto,
  ): Promise<Record<string, unknown>> {
    const session = await this.chatService.createSession(req.user.sub, dto);
    return {
      id: session.id,
      userId: session.userId,
      sport: session.sport,
      title: session.title,
      createdAt: session.createdAt,
      updatedAt: session.updatedAt,
    };
  }

  @Get('sessions')
  async getSessions(@Req() req: JwtRequest): Promise<Record<string, unknown>[]> {
    const sessions = await this.chatService.getUserSessions(req.user.sub);
    return sessions.map((s) => ({
      id: s.id,
      sport: s.sport,
      title: s.title,
      createdAt: s.createdAt,
      updatedAt: s.updatedAt,
    }));
  }

  @Get('sessions/:id/messages')
  async getMessages(@Param('id') sessionId: string): Promise<Record<string, unknown>[]> {
    const messages = await this.chatService.getSessionMessages(sessionId);
    return messages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: m.sourcesJson,
      latencyMs: m.latencyMs,
      createdAt: m.createdAt,
    }));
  }

  @Post('sessions/:id/ask')
  async askQuestion(
    @Param('id') sessionId: string,
    @Body() dto: SendMessageDto,
  ): Promise<Record<string, unknown>> {
    const { userMessage, assistantMessage } = await this.chatService.sendMessage(sessionId, dto);
    return {
      userMessage: {
        id: userMessage.id,
        role: userMessage.role,
        content: userMessage.content,
        createdAt: userMessage.createdAt,
      },
      assistantMessage: {
        id: assistantMessage.id,
        role: assistantMessage.role,
        content: assistantMessage.content,
        sources: assistantMessage.sourcesJson,
        latencyMs: assistantMessage.latencyMs,
        createdAt: assistantMessage.createdAt,
      },
    };
  }
}
