"""
Testes do pre-processamento do HAR.

Este modulo decide o que o ZAP vai atacar. Um erro aqui nao aparece como
falha: aparece como um relatorio de seguranca que parece limpo porque o
trafego certo nunca chegou ao scanner. E o tipo de defeito que passa
despercebido justamente por produzir o resultado que todo mundo quer ver.

Os testes cobrem as quatro decisoes do pipeline — filtrar, deduplicar,
tokenizar e reescrever o host — com o formato real de HAR.
"""

import json
from typing import Any

import pytest

from security_tests.config import settings
from security_tests.har.preprocessing import (
    generate_unique_key,
    rewrite_target_host,
    should_keep_entry,
    tokenize_entry,
    validate_entry,
)


def entrada(
    url: str = "http://localhost:3000/posts",
    method: str = "GET",
    status: int = 200,
    body: str | None = None,
) -> dict[str, Any]:
    """Monta uma entrada de HAR com a estrutura minima que o pipeline espera."""
    request: dict[str, Any] = {"url": url, "method": method}
    if body is not None:
        request["postData"] = {"text": body}
    return {"request": request, "response": {"status": status}}


class TestValidacaoDeEstrutura:
    def test_aceita_entrada_bem_formada(self) -> None:
        assert validate_entry(entrada()) is True

    @pytest.mark.parametrize(
        "quebrada",
        [
            {"request": {"url": "http://localhost:3000/posts"}},  # sem method
            {"response": {"status": 200}},  # sem request
            {"request": {"method": "GET"}, "response": {"status": 200}},  # sem url
        ],
    )
    def test_recusa_entrada_incompleta(self, quebrada: dict[str, Any]) -> None:
        assert validate_entry(quebrada) is False


class TestFiltroDeEntradas:
    """O filtro define o escopo do ataque. O que passa aqui sera atacado."""

    def test_mantem_resposta_de_sucesso_em_endpoint_conhecido(self) -> None:
        assert should_keep_entry(entrada(status=200)) is True

    @pytest.mark.parametrize("status", [301, 400, 401, 404, 500])
    def test_descarta_resposta_que_nao_seja_2xx(self, status: int) -> None:
        """Erro e redirecionamento nao representam o comportamento a avaliar.

        Atacar um endpoint que ja respondeu 404 gasta tempo de scan e produz
        alerta sobre uma resposta de erro, que e falso positivo classico.
        """
        assert should_keep_entry(entrada(status=status)) is False

    def test_descarta_endpoint_fora_das_regras(self) -> None:
        """Trafego de asset estatico e ruido: o Cypress gera CSS, JS e favicon."""
        assert should_keep_entry(entrada(url="http://localhost:3000/favicon.ico")) is False

    def test_descarta_metodo_nao_permitido_no_endpoint(self) -> None:
        """A regra e por metodo, e nao so por caminho.

        /posts aceita GET e POST. Um DELETE em /posts nao esta previsto e nao
        deve ser exercitado pelo scanner.
        """
        assert should_keep_entry(entrada(method="DELETE")) is False

    def test_permite_metodo_declarado_para_o_caminho(self) -> None:
        assert should_keep_entry(entrada(method="POST")) is True

    @pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
    def test_regra_mais_especifica_vence(self, method: str) -> None:
        """/posts/1 deve ser julgado por "/posts/", e nao por "/posts".

        As regras casam por substring, entao "/posts/1" corresponde tanto a
        "/posts" quanto a "/posts/". A versao anterior aceitava a primeira
        regra declarada, o que tornava a mais especifica inalcancavel: "/posts"
        permite apenas GET e POST, entao PUT e DELETE em "/posts/1" eram
        descartados mesmo com "/posts/" autorizando os dois.

        O defeito nao aparecia como erro. O pipeline rodava, o relatorio saia
        limpo, e as operacoes de escrita simplesmente nunca tinham sido
        escaneadas — que e onde injecao mais importa.
        """
        assert should_keep_entry(entrada(url="http://localhost:3000/posts/1", method=method)) is True

    def test_regra_especifica_ainda_recusa_metodo_nao_previsto(self) -> None:
        """Vencer por especificidade nao pode virar permissao ampla."""
        assert (
            should_keep_entry(entrada(url="http://localhost:3000/posts/1", method="PATCH")) is False
        )


class TestDeduplicacao:
    def test_ignora_query_string_na_chave(self) -> None:
        """Duas chamadas ao mesmo endpoint com filtros diferentes sao uma so.

        Escanear /posts?userId=1 e /posts?userId=2 exercita exatamente o mesmo
        codigo do servidor. Deduplicar corta tempo de scan sem perder cobertura.
        """
        a = generate_unique_key(entrada(url="http://localhost:3000/posts?userId=1"))
        b = generate_unique_key(entrada(url="http://localhost:3000/posts?userId=2"))
        assert a == b == "GET|/posts"

    def test_separa_por_metodo(self) -> None:
        """Mesmo caminho com metodos diferentes sao alvos diferentes."""
        get = generate_unique_key(entrada(method="GET"))
        post = generate_unique_key(entrada(method="POST"))
        assert get != post


class TestTokenizacao:
    """Troca de identificadores numericos por {{AUTO_INT}}.

    O script HttpSender do ZAP substitui esse token por um valor novo a cada
    requisicao do scan, evitando que centenas de ataques disputem o mesmo
    registro e produzam conflito em vez de resultado.
    """

    def test_substitui_campo_numerico_configurado(self) -> None:
        resultado = tokenize_entry(entrada(method="POST", body=json.dumps({"userId": 1})))
        corpo = json.loads(resultado["request"]["postData"]["text"])
        assert corpo["userId"] == "{{AUTO_INT}}"

    def test_substitui_numero_em_texto(self) -> None:
        resultado = tokenize_entry(entrada(method="POST", body=json.dumps({"id": "42"})))
        corpo = json.loads(resultado["request"]["postData"]["text"])
        assert corpo["id"] == "{{AUTO_INT}}"

    def test_preserva_campo_nao_numerico(self) -> None:
        """Tokenizar um titulo destruiria o payload que se quer testar."""
        resultado = tokenize_entry(
            entrada(method="POST", body=json.dumps({"id": "abc", "title": "texto"}))
        )
        corpo = json.loads(resultado["request"]["postData"]["text"])
        assert corpo["id"] == "abc"
        assert corpo["title"] == "texto"

    def test_preserva_campo_fora_da_lista(self) -> None:
        resultado = tokenize_entry(entrada(method="POST", body=json.dumps({"preco": 99})))
        corpo = json.loads(resultado["request"]["postData"]["text"])
        assert corpo["preco"] == 99

    def test_nao_quebra_com_corpo_invalido(self) -> None:
        """Corpo que nao e JSON passa intacto em vez de derrubar o pipeline."""
        original = entrada(method="POST", body="isto nao e json")
        resultado = tokenize_entry(original)
        assert resultado["request"]["postData"]["text"] == "isto nao e json"

    def test_nao_quebra_sem_corpo(self) -> None:
        assert tokenize_entry(entrada()) is not None


class TestReescritaDeHost:
    """O HAR e gravado pelo navegador; o scan roda dentro do container do ZAP.

    Sem esta reescrita o ZAP tentaria alcancar localhost, que la dentro e ele
    mesmo. O scan terminaria sem atingir endpoint algum e produziria um
    relatorio vazio — que parece um resultado limpo e nao e.
    """

    def test_troca_o_host_do_navegador_pelo_do_container(self) -> None:
        resultado = rewrite_target_host(entrada(url=f"{settings.TARGET_URL}/posts/1"))
        assert resultado["request"]["url"] == f"{settings.TARGET_URL_FROM_ZAP}/posts/1"

    def test_preserva_caminho_e_query(self) -> None:
        resultado = rewrite_target_host(entrada(url=f"{settings.TARGET_URL}/posts?userId=1"))
        assert resultado["request"]["url"].endswith("/posts?userId=1")

    def test_ignora_url_de_outro_host(self) -> None:
        """Reescrever cegamente poderia redirecionar trafego que nao e do alvo."""
        outra = "http://outro-servidor:9999/posts"
        resultado = rewrite_target_host(entrada(url=outra))
        assert resultado["request"]["url"] == outra
