FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# 빌드 산출물 검사(자산 경로, 절대 API 주소 없음)를 이미지 빌드 단계에서 함께 실행
RUN npm run build && npm run check -- f6

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
