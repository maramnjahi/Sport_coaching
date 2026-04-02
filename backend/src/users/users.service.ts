import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User, UserDocument } from '../database/schemas/user.schema';
import { UserRole } from '../database/entities/role.enum';
import { SportType } from '../database/entities/sport.enum';

type CreateUserInput = {
  email: string;
  passwordHash: string;
  role: UserRole;
  sport: SportType | null;
  level: string | null;
  profile: Record<string, unknown>;
};

@Injectable()
export class UsersService {
  constructor(
    @InjectModel(User.name)
    private readonly usersModel: Model<UserDocument>,
  ) {}

  async create(input: CreateUserInput): Promise<User> {
    const user = new this.usersModel(input);
    const savedUser = await user.save();
    return this.toUserDto(savedUser);
  }

  async findByEmail(email: string): Promise<User | null> {
    const user = await this.usersModel.findOne({ email }).exec();
    return user ? this.toUserDto(user) : null;
  }

  async findById(id: string): Promise<User | null> {
    const user = await this.usersModel.findById(id).exec();
    return user ? this.toUserDto(user) : null;
  }

  private toUserDto(doc: UserDocument): User {
    return {
      id: doc._id.toString(),
      email: doc.email,
      passwordHash: doc.passwordHash,
      role: doc.role,
      sport: doc.sport ?? null,
      level: doc.level ?? null,
      profile: doc.profile,
      createdAt: doc.createdAt,
      updatedAt: doc.updatedAt,
    };
  }
}