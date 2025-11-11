from app import models
from app.routes import tipos as tipos_routes


def test_tipos_functions_return_data(monkeypatch):
    class DummySession:
        def __init__(self):
            self._items = [models.TipoVehiculo(id_tipo_vehiculo=1, tipo="Camion")]

        def query(self, model):
            return self

        def all(self):
            return self._items

    dummy_db = DummySession()

    vehiculos = tipos_routes.get_tipos_vehiculo(db=dummy_db)
    assert vehiculos[0].tipo == "Camion"
