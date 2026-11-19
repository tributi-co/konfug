"""Pruebas mínimas del contrato público de Konfug, sin servicios externos."""

from unittest import mock

import pytest

import konfug
from konfug import Konfug, KonfugMetaConfigError, KonfugMissingError


@pytest.fixture
def config():
    """Konfug sin Datastore ni Secret Manager: solo variables de entorno."""
    return Konfug(
        project_id="proyecto",
        settings_kind="Settings",
        namespace="ns",
        skip_datastore=True,
        skip_secret_manager=True,
        skip_firebase=True,
    )


def test_tipos_desde_entorno(config, monkeypatch):
    monkeypatch.setenv("K_STR", "hola")
    monkeypatch.setenv("K_INT", "7")
    monkeypatch.setenv("K_FLOAT", "1.5")
    monkeypatch.setenv("K_FLAG_ON", "1")
    monkeypatch.setenv("K_FLAG_OFF", "false")
    monkeypatch.setenv("K_LIST", "a, b ,,c")
    monkeypatch.setenv("K_DICT", '{"x": 1}')

    assert config.string("K_STR") == "hola"
    assert config.integer("K_INT") == 7
    assert config.floatnum("K_FLOAT") == 1.5
    assert config.flag("K_FLAG_ON") is True
    assert config.flag("K_FLAG_OFF") is False
    assert config.stringlist("K_LIST") == ["a", "b", "c"]
    assert config.dictionary("K_DICT") == {"x": 1}


def test_default_y_ausente(config):
    assert config.string("K_NO_EXISTE", default_val="d") == "d"
    with pytest.raises(KonfugMissingError):
        config.string("K_NO_EXISTE")


def test_raw_setting_nullable(config):
    assert config.raw_setting("K_NO_EXISTE", nullable=True) is None


def test_dictionary_invalido(config, monkeypatch):
    monkeypatch.setenv("K_DICT", "[1, 2]")
    with pytest.raises(ValueError):
        config.dictionary("K_DICT")


def test_secret_desde_entorno_y_transform(config, monkeypatch):
    monkeypatch.setenv("S_KEY", "abc")
    assert config.secret("S_KEY", transform=str.upper) == "ABC"


def test_secret_ausente(config):
    with pytest.raises(KonfugMissingError) as err:
        config.secret("S_NO_EXISTE")
    assert 'secret "S_NO_EXISTE"' in err.value.message
    assert config.secret("S_NO_EXISTE", default_val="x") == "x"


def test_metaconfig_requerida(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(KonfugMetaConfigError):
        Konfug(settings_kind="S", namespace="n", skip_datastore=True)


def test_metaconfig_desde_entorno(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p")
    monkeypatch.setenv("KONFUG_DATASTORE_SETTINGS_KIND", "S")
    monkeypatch.setenv("KONFUG_DATASTORE_NAMESPACE", "n")
    cfg = Konfug(skip_datastore=True, skip_secret_manager=True)
    assert cfg.string("X", default_val="ok") == "ok"


def test_datastore_namespace_comun_y_prioridad(monkeypatch):
    """El namespace propio gana sobre el común; el entorno gana sobre ambos."""
    por_namespace = {"ns": {"A": "propio", "B": "propio"},
                     "comun": {"A": "comun", "C": "comun"}}

    def query(kind, namespace):
        resultado = mock.Mock()
        resultado.fetch.return_value = iter([por_namespace[namespace]])
        return resultado

    cliente = mock.Mock()
    cliente.query.side_effect = query
    monkeypatch.setenv("B", "entorno")
    with mock.patch.object(konfug.datastore, "Client", return_value=cliente):
        cfg = Konfug(
            project_id="p", settings_kind="S", namespace="ns",
            common_namespace="comun", skip_secret_manager=True,
        )

    assert cfg.string("A") == "propio"
    assert cfg.string("B") == "entorno"
    assert cfg.string("C") == "comun"


def test_secret_desde_secret_manager(monkeypatch):
    respuesta = mock.Mock()
    respuesta.payload.data = "valor-secreto".encode("utf-8")
    cliente = mock.Mock()
    cliente.access_secret_version.return_value = respuesta
    with mock.patch.object(
        konfug.secretmanager, "SecretManagerServiceClient",
        return_value=cliente,
    ):
        cfg = Konfug(
            project_id="p", settings_kind="S", namespace="n",
            skip_datastore=True,
        )
    assert cfg.secret("S_REMOTO") == "valor-secreto"
    cliente.access_secret_version.assert_called_once_with(
        request={"name": "projects/p/secrets/S_REMOTO/versions/latest"}
    )


def test_hot_settings_usa_firestore(config):
    config._skip_firebase = False
    documento = mock.Mock(exists=True)
    documento.to_dict.return_value = {"value": "5"}
    coleccion = mock.Mock()
    coleccion.document.return_value.get.return_value = documento
    hot_cls = konfug.HotFug.hotfug_cls({}, "coleccion")
    hot_cls._FIREBASE = coleccion
    config._hot_cls = hot_cls

    valor = config.integer("HOT_KEY", hot=True)
    assert valor.retrieve() == 5
    coleccion.document.assert_called_once_with("HOT_KEY")


def test_firebase_submodulos_importados():
    """Sin depender de que otro módulo importe los submódulos de firebase."""
    import subprocess
    import sys

    codigo = (
        "import konfug, firebase_admin;"
        "assert konfug.credentials.Certificate;"
        "assert konfug.firestore.client;"
        "assert konfug.exceptions.FirebaseError"
    )
    subprocess.run([sys.executable, "-c", codigo], check=True)
