# ---------------------------------------------------------------------------
# Alvo local do pipeline: uma API com a mesma forma do JSONPlaceholder.
#
# A versao 0.17 do json-server e escolhida de proposito. Ela expoe as rotas
# aninhadas que os testes usam — /posts/1/comments e /users/1/posts — resolvidas
# pelas chaves postId e userId. A linha 1.x reorganizou esse comportamento.
# ---------------------------------------------------------------------------
FROM node:22-alpine

RUN npm install --global --no-fund --no-audit json-server@0.17.4

WORKDIR /app
COPY db.json ./db.json

EXPOSE 3000

# --host 0.0.0.0 e necessario para o container aceitar conexoes de fora dele.
# O db.json e uma copia dentro da imagem: as escritas do scan ficam contidas no
# container e somem quando ele e recriado, entao cada execucao parte do mesmo
# estado.
CMD ["json-server", "--host", "0.0.0.0", "--port", "3000", "db.json"]
