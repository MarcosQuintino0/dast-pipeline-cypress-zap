"""
Configuracao central do pipeline, com validacao de tipos via Pydantic Settings.

Por que Pydantic Settings e nao um dicionario ou variaveis soltas:

- Valida tipo na carga. ZAP_PORT="abc" falha no inicio, e nao no meio do scan.
- Enum para valores restritos, o que elimina erro de digitacao silencioso:
  ZAP_ATTACK_STRENGTH="MEDIO" nao passa.
- Le de variavel de ambiente e de .env sem codigo extra.
- Um unico lugar com valor padrao, entao nenhum outro modulo precisa inventar.

Nenhum outro arquivo do projeto deve conter valor de configuracao fixo.
"""

from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class ZapMode(StrEnum):
    """Modos de operacao do ZAP.

    safe      observa, nunca ataca
    protect   ataca apenas URLs dentro do escopo definido
    standard  equilibrio padrao
    attack    agressivo, ataca tudo que descobre
    """

    SAFE = "safe"
    PROTECT = "protect"
    STANDARD = "standard"
    ATTACK = "attack"


class ZapAttackStrength(StrEnum):
    """Intensidade do scan ativo.

    LOW    poucas variacoes de payload, rapido
    INSANE todas as variacoes possiveis, muito lento
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    INSANE = "INSANE"


class ZapAlertThreshold(StrEnum):
    """Sensibilidade do alerta.

    LOW  reporta ate suspeita fraca, gera mais falso positivo
    HIGH reporta so com confianca alta, pode deixar passar achado real
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ScanTargetNotAllowed(Exception):
    """Alvo fora da allowlist. O scan e interrompido antes de qualquer requisicao."""


class Settings(BaseSettings):
    """Configuracao global do pipeline."""

    # === CAMINHOS ===
    BASE_DIR: Path = Path(__file__).resolve().parent
    ZAP_SCRIPTS_DIR: Path = Path(__file__).resolve().parent / "zap_scripts"
    TRAFFIC_DIR: Path = Path(__file__).resolve().parent / "traffic"
    REPORTS_DIR: Path = Path(__file__).resolve().parent / "reports"

    # === ALVO ===
    # API local com a forma do JSONPlaceholder, subida por docker compose.
    TARGET_URL: str = "http://localhost:3000"

    # Dentro da rede do compose o ZAP alcanca o alvo pelo nome do servico, e nao
    # por localhost: para o container do ZAP, localhost e ele mesmo.
    TARGET_URL_FROM_ZAP: str = "http://api:3000"

    # === GUARDA DE SEGURANCA ===
    # Scan ativo nao le, ataca: injecao, traversal, XSS, comando de sistema.
    # Contra um servico de terceiros isso e abuso e, em varias jurisdicoes,
    # teste nao autorizado. A lista e curta e explicita de proposito, e um alvo
    # fora dela interrompe a execucao antes da primeira requisicao.
    # Guardada como texto separado por virgula, e nao como lista.
    #
    # O Pydantic Settings decodifica campos de lista como JSON antes de
    # qualquer validador rodar, o que obrigaria a escrever
    # ["localhost","127.0.0.1","api"] no .env. Como esta e a lista que separa
    # um teste de seguranca de um ataque a terceiros, ela precisa ser trivial
    # de ler e editar: quanto mais estranha a sintaxe, maior a chance de
    # alguem errar sem perceber. A leitura tipada fica em allowed_hosts.
    ALLOWED_SCAN_HOSTS: str = "localhost,127.0.0.1,api"

    @property
    def allowed_hosts(self) -> list[str]:
        """Hosts autorizados, ja normalizados."""
        return [item.strip() for item in self.ALLOWED_SCAN_HOSTS.split(",") if item.strip()]

    # === ZAP ===
    # Nome do contexto, definido num unico lugar.
    #
    # Ele era repetido em dois modulos: um criava o contexto, o outro o
    # procurava pelo nome. Ao renomear so um dos dois, a busca passou a devolver
    # uma string de erro onde o codigo esperava um dicionario, e o scan quebrou
    # na fase 6 depois de cinco fases bem-sucedidas. Valor repetido e defeito
    # esperando o dia em que alguem alterar so uma das copias.
    ZAP_CONTEXT_NAME: str = "DAST_LOCAL_API"

    # Onde o diretorio de trafego aparece dentro do container do ZAP.
    #
    # A API de importacao de HAR recebe um caminho de arquivo e o abre no
    # sistema de arquivos de quem executa o ZAP. Como o ZAP roda em container e
    # o HAR e gravado no host, o caminho precisa ser traduzido. O volume que faz
    # essa ponte esta no docker-compose.yml.
    ZAP_TRAFFIC_DIR_IN_CONTAINER: str = "/zap/traffic"

    ZAP_HOST: str = "127.0.0.1"
    ZAP_PORT: int = 8080
    ZAP_API_KEY: str = "dast-pipeline-local"
    ZAP_MODE: ZapMode = ZapMode.STANDARD

    # === POLITICA DE SCAN ===
    ZAP_ATTACK_STRENGTH: ZapAttackStrength = ZapAttackStrength.MEDIUM
    ZAP_ALERT_THRESHOLD: ZapAlertThreshold = ZapAlertThreshold.LOW
    ZAP_THREAD_PER_HOST: int = 2
    ZAP_DELAY_IN_MS: int = 0
    ZAP_PSCAN_TIMEOUT_SECONDS: int = 300

    # === REGRAS DE NEGOCIO ===
    # Define quais metodos HTTP podem ser atacados em cada caminho. O que nao
    # esta aqui e descartado no pre-processamento e nunca chega ao ZAP.
    #
    # Serve a dois propositos. Corta ruido, porque o Cypress gera trafego de
    # CSS, JS, fonte e favicon que nao interessa a um scan de API. E delimita o
    # ataque, mantendo o scan restrito ao que se pretende avaliar.
    ENDPOINT_RULES: dict[str, list[str]] = {
        "/posts": ["GET", "POST"],
        "/posts/": ["GET", "PUT", "DELETE"],
        "/comments": ["GET", "POST"],
        "/todos": ["GET", "POST"],
        "/users": ["GET"],
        "/users/": ["GET"],
        "/albums": ["GET"],
        "/albums/": ["GET"],
        "/photos": ["GET"],
    }

    # Campos cujos valores numericos viram {{AUTO_INT}} no HAR, para o script
    # HttpSender do ZAP gerar um valor diferente a cada requisicao do scan.
    FIELDS_TO_TOKENIZE: list[str] = ["userId", "id", "postId"]

    # === ALLOWLIST DE TECNOLOGIA ===
    # O ZAP traz centenas de regras, muitas para tecnologias que o alvo nao usa.
    # Restringir corta tempo de scan e falso positivo: nao faz sentido procurar
    # injecao de Oracle ou falha de IIS numa API Node.
    ZAP_TECH_ALLOWLIST: str = "Language.JavaScript,WS.Node,WS.Express,OS.Linux,SCM.Git"

    def model_post_init(self, __context: Any) -> None:
        """Cria os diretorios de saida se ainda nao existirem."""
        self.TRAFFIC_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Um unico .env serve ao docker compose e a este modulo. Variaveis como
    # API_PORT so interessam ao compose, entao o Python ignora o que nao e dele
    # em vez de exigir que cada lado tenha seu proprio arquivo: dois arquivos de
    # configuracao divergem em silencio, e um so nao.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instancia unica, importada pelos demais modulos.
settings = Settings()


def assert_target_is_allowed(url: str) -> None:
    """Recusa qualquer alvo fora da allowlist antes de o scan comecar.

    Nao e formalidade. Um erro de digitacao numa variavel de ambiente basta para
    transformar este projeto num ataque contra um host que nao e seu, e a
    diferenca entre um pipeline de seguranca e um incidente e exatamente esta
    verificacao.

    Raises:
        ScanTargetNotAllowed: quando o host do alvo nao esta na allowlist.
    """
    host = urlparse(url).hostname

    if host is None:
        raise ScanTargetNotAllowed(f"URL de alvo invalida: {url!r}")

    if host not in settings.allowed_hosts:
        permitidos = ", ".join(settings.allowed_hosts)
        raise ScanTargetNotAllowed(
            f"Host {host!r} nao esta na allowlist ({permitidos}).\n"
            "Scan ativo dispara payloads de ataque reais. Aponte o pipeline "
            "apenas para um alvo que voce controla, como a API local que este "
            "repositorio sobe com docker compose."
        )
