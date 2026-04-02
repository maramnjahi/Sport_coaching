import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Types } from 'mongoose';
import { SportType } from '../entities/sport.enum';

export type ChatSessionDocument = HydratedDocument<ChatSession>;

@Schema({ timestamps: true })
export class ChatSession {
  id!: string;

  @Prop({ type: Types.ObjectId, ref: 'User', required: true, index: true })
  userId!: string;

  @Prop({ type: String, enum: SportType, required: true })
  sport!: SportType;

  @Prop({ required: true })
  title!: string;

  @Prop()
  createdAt?: Date;

  @Prop()
  updatedAt?: Date;
}

export const ChatSessionSchema = SchemaFactory.createForClass(ChatSession);
ChatSessionSchema.virtual('id').get(function () {
  return this._id.toString();
});
ChatSessionSchema.set('toJSON', { virtuals: true });
