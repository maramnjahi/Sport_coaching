import { Logger, ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import helmet from 'helmet';

import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const logger = new Logger('Bootstrap');
  const app = await NestFactory.create(AppModule);

  // ─── Security ────────────────────────────────────────────────────────────────
  app.use(helmet());
  app.enableCors({ origin: true, credentials: true });

  // ─── Global prefix ───────────────────────────────────────────────────────────
  // app.setGlobalPrefix('api'); // removed for simpler routing

  // ─── Validation ──────────────────────────────────────────────────────────────
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: { enableImplicitConversion: false },
    }),
  );

  // ─── Graceful shutdown ───────────────────────────────────────────────────────
  app.enableShutdownHooks();

  const port = Number(process.env.PORT ?? 3001);
  await app.listen(port);
  logger.log(`🚀 CoachMind API is running on http://localhost:${port}`);
}

void bootstrap();