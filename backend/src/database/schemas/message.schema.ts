import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Types } from 'mongoose';
import { MessageRole } from '../entities/message-role.enum';

export type MessageDocument = HydratedDocument<Message>;

@Schema({ timestamps: { createdAt: true, updatedAt: false } })
export class Message {
  id!: string;

  @Prop({ type: Types.ObjectId, ref: 'ChatSession', required: true, index: true })
  sessionId!: string;

  @Prop({ type: String, enum: MessageRole, required: true })
  role!: MessageRole;

  @Prop({ required: true })
  content!: string;

  @Prop({ type: Array, default: [] })
  sourcesJson?: unknown[];

  @Prop({ type: Number, required: false, default: null })
  latencyMs?: number | null;

  @Prop()
  createdAt?: Date;
}

export const MessageSchema = SchemaFactory.createForClass(Message);
MessageSchema.virtual('id').get(function () {
  return this._id.toString();
});
MessageSchema.set('toJSON', { virtuals: true });
