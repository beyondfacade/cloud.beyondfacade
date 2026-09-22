# 로컬 개발용 이미지 — 배포는 Vercel이 담당하므로 이 파일은 배포에 사용되지 않음.
# 프론트엔드 스택 확정(package.json 생성) 후 동작합니다.
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3200
CMD ["npm", "run", "dev"]
