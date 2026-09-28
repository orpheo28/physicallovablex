"""Scope gate (fishing-boat bug): out-of-scope prompts are refused at POST /projects; keyword features are word-bounded."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from api import scope
from api.cad.directions import preset_key
from api.cad.look import features_for
from api.main import app

client = TestClient(app)


def test_keyword_gate_refuses_vehicles_not_devices():
    for p in ("un bateau, pour aller pêcher", "a fishing boat", "une maison en bois", "a sofa for my living room"):
        assert not scope.check(p).in_scope, p
    for p in ("desk lamp", "a bike light", "détecteur de touche pour la pêche", "a BLE tracker card", "car phone mount"):
        assert scope.check(p).in_scope, p


def test_create_project_refuses_out_of_scope():
    r = client.post("/projects", json={"mode": "idea", "prompt": "un bateau, pour aller pêcher"})
    assert r.status_code == 422
    assert "small physical products" in r.json()["detail"]
    assert client.post("/projects", json={"mode": "idea", "prompt": "a warm desk lamp"}).status_code == 201


def test_features_are_word_bounded():
    brief = SimpleNamespace(category="other", product_name="Fishing float", one_liner="Floats on the water while fishing",
                            key_features=["category-leading"], prompt="")
    f = features_for(brief)
    assert "bowl" not in f and "feet" in f  # "water" is not a bowl, "fishing" is not a ring, "category" is not a cat
    assert preset_key(brief) == "default"
    assert "bowl" in features_for(SimpleNamespace(category="kitchen_appliance", product_name="Dog feeder", one_liner="", key_features=[]))
