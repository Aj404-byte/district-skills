"""Offline tests: no network, no real home directory."""
import argparse
import json

import pytest

from district_skills import cli, installer


def test_location_is_required():
    ns = argparse.Namespace(city=None, lat=None, lng=None)
    with pytest.raises(cli.Err, match="ask the user"):
        cli.resolve(ns)


def test_lat_lng_passthrough():
    assert cli.resolve(argparse.Namespace(city=None, lat=1.5, lng=2.5)) == (1.5, 2.5, None)


def test_known_city_needs_no_network(capsys):
    lat, lng, name = cli.resolve(argparse.Namespace(city="Mumbai", lat=None, lng=None))
    assert name == "mumbai" and 18 < lat < 20
    assert "# location:" in capsys.readouterr().err


def test_ld_json_flattens_graph():
    html = '<script type="application/ld+json">{"@graph":[{"@type":"Event"},{"@type":"Restaurant"}]}</script>'
    assert [i["@type"] for i in cli.ld_json(html)] == ["Event", "Restaurant"]


def test_login_validation_does_not_hit_network():
    with pytest.raises(cli.Err):
        cli.cmd_login(argparse.Namespace(action="start", phone="abc", country_code="91"))


def test_installer_copies_all_skills(tmp_path):
    out = installer.install(str(tmp_path))
    names = {p.name for p in tmp_path.iterdir()}
    assert names == {"district", "district-discover", "district-login", "district-logout", "district-bookings"}
    assert len(out["installed"]) == 5
    for n in names:
        text = (tmp_path / n / "SKILL.md").read_text()
        assert text.startswith("---\nname: " + n + "\n")
        assert "scripts/district.py" not in text


def test_installer_only_and_unknown(tmp_path):
    assert len(installer.install(str(tmp_path), ["district-login"])["installed"]) == 1
    with pytest.raises(SystemExit):
        installer.install(str(tmp_path), ["nope"])


def test_every_skill_documents_location_rule():
    for n in ("district", "district-discover"):
        text = (installer.resources.files("district_skills") / "skills" / n / "SKILL.md").read_text()
        assert "Ask the user where they are" in text or "**Ask the user where they are**" in text
