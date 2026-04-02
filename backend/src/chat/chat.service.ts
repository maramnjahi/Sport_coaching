import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { ChatSession, ChatSessionDocument } from '../database/schemas/chat-session.schema';
import { Message, MessageDocument } from '../database/schemas/message.schema';
import { MessageRole } from '../database/entities/message-role.enum';
import { CreateSessionDto } from './dto/create-session.dto';
import { SendMessageDto, ChatResponseDto, MessageSourceDto } from './dto/send-message.dto';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class ChatService {
  constructor(
    @InjectModel(ChatSession.name)
    private readonly sessionModel: Model<ChatSessionDocument>,
    @InjectModel(Message.name)
    private readonly messageModel: Model<MessageDocument>,
    private readonly configService: ConfigService,
  ) {}

  async createSession(userId: string, dto: CreateSessionDto): Promise<ChatSession> {
    const session = new this.sessionModel({
      userId,
      sport: dto.sport,
      title: dto.title,
    });
    const savedSession = await session.save();
    return this.toChatSessionDto(savedSession);
  }

  async getSessionById(sessionId: string): Promise<ChatSession> {
    const session = await this.sessionModel.findById(sessionId).exec();
    if (!session) {
      throw new NotFoundException(`Session ${sessionId} not found`);
    }
    return this.toChatSessionDto(session);
  }

  async getUserSessions(userId: string): Promise<ChatSession[]> {
    const sessions = await this.sessionModel
      .find({ userId })
      .sort({ createdAt: -1 })
      .exec();
    return sessions.map((s) => this.toChatSessionDto(s));
  }

  async sendMessage(
    sessionId: string,
    dto: SendMessageDto,
  ): Promise<{ userMessage: Message; assistantMessage: Message }> {
    const session = await this.getSessionById(sessionId);

    const userMessage = new this.messageModel({
      sessionId,
      role: MessageRole.USER,
      content: dto.query,
      sourcesJson: [],
      latencyMs: null,
    });
    const savedUserMessage = await userMessage.save();

    const startTime = Date.now();

    let aiResponse: ChatResponseDto;
    try {
      aiResponse = await this.callAiService(dto.query, session.sport, sessionId);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      aiResponse = {
        response: `Sorry, I encountered an error processing your question: ${errorMessage}`,
        sources: [],
        latencyMs: Date.now() - startTime,
      };
    }

    const assistantMessage = new this.messageModel({
      sessionId,
      role: MessageRole.ASSISTANT,
      content: aiResponse.response,
      sourcesJson: aiResponse.sources as any,
      latencyMs: aiResponse.latencyMs,
    });
    const savedAssistantMessage = await assistantMessage.save();

    return {
      userMessage: this.toMessageDto(savedUserMessage),
      assistantMessage: this.toMessageDto(savedAssistantMessage),
    };
  }

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const messages = await this.messageModel
      .find({ sessionId })
      .sort({ createdAt: 1 })
      .exec();
    return messages.map((m) => this.toMessageDto(m));
  }

  private async callAiService(
    query: string,
    sport: string,
    sessionId: string,
  ): Promise<ChatResponseDto> {
    const aiServiceUrl = this.configService.get<string>('AI_SERVICE_URL');
    if (!aiServiceUrl) {
      return {
        response: 'AI service not configured',
        sources: [],
        latencyMs: 0,
      };
    }

    try {
      const requestStarted = Date.now();
      const response = await fetch(`${aiServiceUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          sport,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`AI service returned ${response.status}`);
      }

      const data = (await response.json()) as {
        response: string;
        sources: ChatResponseDto['sources'];
        latencyMs: number;
      };
      return {
        response: data.response,
        sources: data.sources ?? [],
        latencyMs: data.latencyMs ?? Date.now() - requestStarted,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to call AI service: ${errorMessage}`);
    }
  }

  private toChatSessionDto(doc: ChatSessionDocument): ChatSession {
    return {
      id: doc._id.toString(),
      userId: doc.userId.toString(),
      sport: doc.sport,
      title: doc.title,
      createdAt: doc.createdAt,
      updatedAt: doc.updatedAt,
    };
  }

  private toMessageDto(doc: MessageDocument): Message {
    return {
      id: doc._id.toString(),
      sessionId: doc.sessionId.toString(),
      role: doc.role,
      content: doc.content,
      sourcesJson: doc.sourcesJson ?? [],
      latencyMs: doc.latencyMs ?? null,
      createdAt: doc.createdAt,
    };
  }
}
