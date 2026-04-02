import { Controller, Get, Req, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { UsersService } from './users.service';

type JwtRequest = {
  user: {
    sub: string;
    email: string;
    role: string;
  };
};

@UseGuards(JwtAuthGuard)
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get('me')
  async getMe(@Req() req: JwtRequest): Promise<{ id: string; email: string; role: string }> {
    const user = await this.usersService.findById(req.user.sub);
    if (!user) {
      return {
        id: req.user.sub,
        email: req.user.email,
        role: req.user.role,
      };
    }

    return {
      id: user.id,
      email: user.email,
      role: user.role,
    };
  }
}