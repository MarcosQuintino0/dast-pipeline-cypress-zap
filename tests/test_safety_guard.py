"""
Testes da guarda que impede o scan de mirar um host que nao e nosso.

Este e o teste mais importante do repositorio. Todo o resto do pipeline gera
relatorio; esta funcao e a unica que impede o projeto de virar um ataque contra
infraestrutura de terceiros. Um scan ativo dispara payloads de injecao,
traversal, XSS e comando de sistema — nao e leitura, e ataque, e apontar isso
para um dominio alheio e conduta ilegal em varias jurisdicoes.

Um erro de digitacao numa variavel de ambiente basta para cruzar essa linha,
por isso a protecao esta em codigo e nao num aviso no README.
"""

import pytest

from security_tests.config import ScanTargetNotAllowed, assert_target_is_allowed


class TestAlvosPermitidos:
    """Os alvos locais que o proprio repositorio sobe devem passar."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:3000",
            "http://localhost:3000/posts",
            "http://127.0.0.1:3000/posts/1",
            "http://api:3000",
            "http://api:3000/comments?postId=1",
        ],
    )
    def test_permite_alvo_local(self, url: str) -> None:
        assert_target_is_allowed(url)


class TestAlvosRecusados:
    """Qualquer host fora da allowlist interrompe a execucao."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://jsonplaceholder.typicode.com",
            "https://jsonplaceholder.typicode.com/posts",
            "http://example.com",
            "https://api.github.com/users",
            # Host parecido com um permitido, mas diferente: a verificacao e por
            # igualdade exata, e nao por "contem". "localhost.evil.com" resolve
            # para um servidor de terceiro e nao pode passar.
            "http://localhost.evil.com",
            "http://notlocalhost",
        ],
    )
    def test_recusa_alvo_externo(self, url: str) -> None:
        with pytest.raises(ScanTargetNotAllowed):
            assert_target_is_allowed(url)

    def test_mensagem_explica_o_risco(self) -> None:
        """A mensagem precisa dizer por que foi recusado, e nao apenas que foi.

        Quem esbarra nesta excecao normalmente esta configurando o pipeline pela
        primeira vez. Uma mensagem que so diz "nao permitido" leva a pessoa a
        adicionar o host na allowlist para seguir em frente, que e exatamente o
        contrario do que a guarda existe para evitar.
        """
        with pytest.raises(ScanTargetNotAllowed) as excecao:
            assert_target_is_allowed("https://jsonplaceholder.typicode.com")

        mensagem = str(excecao.value)
        assert "jsonplaceholder.typicode.com" in mensagem
        assert "ataque" in mensagem.lower()
        assert "controla" in mensagem.lower()

    def test_recusa_url_sem_host(self) -> None:
        """Uma URL malformada nao pode passar por omissao."""
        with pytest.raises(ScanTargetNotAllowed):
            assert_target_is_allowed("nao-e-uma-url")
