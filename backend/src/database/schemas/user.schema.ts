import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';
import { UserRole } from '../entities/role.enum';
import { SportType } from '../entities/sport.enum';

export type UserDocument = HydratedDocument<User>;

@Schema({ timestamps: true })
export class User {
  id!: string;

  @Prop({ required: true, unique: true, index: true })
  email!: string;

  @Prop({ required: true })
  passwordHash!: string;

  @Prop({ type: String, enum: UserRole, default: UserRole.ATHLETE })
  role!: UserRole;

  @Prop({ type: String, enum: SportType, required: false, default: null })
  sport?: SportType | null;

  @Prop({ type: String, required: false, default: null })
  level?: string | null;

  @Prop({ type: Object, default: {} })
  profile!: Record<string, unknown>;

  @Prop()
  createdAt?: Date;

  @Prop()
  updatedAt?: Date;
}

export const UserSchema = SchemaFactory.createForClass(User);
UserSchema.virtual('id').get(function () {
  return this._id.toString();
});
UserSchema.set('toJSON', { virtuals: true });
