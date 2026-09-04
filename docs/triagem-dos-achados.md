# Triagem dos achados

Um scanner DAST não entrega vulnerabilidades. Entrega **candidatos**. A parte
que exige engenheiro é separar o que é risco real do que é ruído da ferramenta,
e conseguir provar a diferença.

Esta é a triagem dos dois achados de severidade **alta** da execução contra o
alvo local deste repositório.

---

## SQL Injection — falso positivo

**O que o ZAP reportou**

| Campo     | Valor                   |
| --------- | ----------------------- |
| Alerta    | SQL Injection           |
| Risco     | Alto                    |
| Confiança | Média                   |
| CWE       | 89                      |
| URL       | `http://api:3000/posts` |
| Parâmetro | `Accept`                |
| Ataque    | `*/*' AND '1'='1' -- `  |
| Evidência | _(vazia)_               |

**Por que desconfiei**

Três sinais, antes de qualquer teste:

1. O parâmetro injetado é o cabeçalho **`Accept`**, não um parâmetro de consulta
   ou de corpo. Um cabeçalho de negociação de conteúdo não costuma alimentar
   consulta a banco.
2. O campo **evidência veio vazio**. O ZAP não extraiu mensagem de erro de banco
   nem dado indevido: a detecção foi por heurística de diferença entre respostas.
3. O alvo **não tem banco SQL**. É `json-server`, que persiste num arquivo JSON.

**Como confirmei**

Reproduzi o payload e comparei as respostas por hash:

```bash
curl -s -H "Accept: */*' AND '1'='1' -- " http://localhost:3000/posts | md5sum
curl -s -H "Accept: */*' AND '1'='2' -- " http://localhost:3000/posts | md5sum
curl -s                                   http://localhost:3000/posts | md5sum
```

As três saídas foram idênticas:

```
c6f914455134791aead74569b7636d36
c6f914455134791aead74569b7636d36
c6f914455134791aead74569b7636d36
```

A detecção de injeção cega booleana funciona comparando a resposta de
`AND '1'='1'` com a de `AND '1'='2'`. Quando a aplicação **ignora** o parâmetro
injetado, as duas respostas são iguais — e essa igualdade é justamente o que a
heurística interpreta como condição sempre verdadeira.

**Veredito:** falso positivo. O cabeçalho não influencia consulta alguma, e não
existe consulta SQL para influenciar.

**O que isso ensina sobre o pipeline:** a allowlist de tecnologias em
`security_tests/config.py` existe exatamente para reduzir esse tipo de ruído.
Ela declara Node, Express e JavaScript — se declarasse também um banco SQL, o
ZAP aplicaria ainda mais regras de injeção e o ruído aumentaria sem nenhum ganho.

---

## External Redirect — achado real

**O que o ZAP reportou**

| Campo     | Valor                           |
| --------- | ------------------------------- |
| Alerta    | External Redirect               |
| Risco     | Alto                            |
| Confiança | Média                           |
| CWE       | 601                             |
| URL       | `http://api:3000/comments`      |
| Parâmetro | `Host`                          |
| Ataque    | `7409559654336579101.owasp.org` |

**Como confirmei**

Requisição com o cabeçalho `Host` manipulado:

```bash
curl -s -D - -o /dev/null \
  -H "Host: 7409559654336579101.owasp.org" \
  "http://localhost:3000/comments?_page=1&_limit=2"
```

Resposta:

```
Link: <http://7409559654336579101.owasp.org/comments?_page=2&_limit=2>; rel="next"
```

Contra a mesma requisição sem manipulação:

```
Link: <http://localhost:3000/comments?_page=2&_limit=2>; rel="next"
```

**Veredito:** reproduzível. O valor do cabeçalho `Host` é refletido, sem
validação, nas URLs de paginação que a aplicação devolve.

**Por que importa**

Um cliente que siga a paginação — e seguir o cabeçalho `Link` é o comportamento
correto segundo a RFC 8288 — é conduzido a um host escolhido por quem enviou a
requisição. É a base de duas classes de ataque conhecidas:

- **Envenenamento de cache web**, quando um proxy ou CDN armazena a resposta
  com a URL envenenada e a serve a outros usuários.
- **Envenenamento de link de recuperação de senha**, quando o mesmo padrão
  aparece na geração de e-mails.

**Ressalva honesta sobre o impacto:** aqui o alvo é uma API local sem cache
intermediário e sem envio de e-mail, então o risco concreto **nesta instância**
é baixo. O que o achado demonstra é a classe de defeito e a capacidade do
pipeline de encontrá-la. Num serviço real atrás de CDN, o mesmo comportamento
seria explorável.

**Correção esperada:** validar o cabeçalho `Host` contra uma lista de domínios
conhecidos, ou construir URLs absolutas a partir de configuração do servidor em
vez de a partir da requisição.

---

## Os demais achados

| Alerta                                      | Risco       | Comentário                                                                                                                                                 |
| ------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Servidor vaza informação via `X-Powered-By` | Baixo       | Real. O Express anuncia a si mesmo em todas as respostas, o que facilita a fase de reconhecimento de um atacante. Correção: `app.disable('x-powered-by')`. |
| ZAP está desatualizado                      | Baixo       | **Não é achado sobre o alvo.** É o ZAP relatando a própria versão. Ruído de inventário, não de segurança da aplicação.                                     |
| User Agent Fuzzer                           | Informativo | Verifica se a aplicação responde diferente conforme o cliente. Sem diferença relevante aqui.                                                               |

---

## O critério

A regra que sigo neste projeto, e que sustenta as decisões acima:

**Um achado só é reportado como real quando pode ser reproduzido fora da
ferramenta.** Se depende do scanner para existir, é candidato — não conclusão.

O inverso também vale, e é o erro mais caro: descartar achado por conveniência.
O `External Redirect` era fácil de ignorar como "coisa de cabeçalho". Foi
reproduzido, entendido e reportado como real, com a ressalva explícita de que o
impacto nesta instância é limitado.
