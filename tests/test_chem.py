"""Pure-python SMILES parser and descriptor correctness."""

from shennong.chem import describe_smiles, parse_smiles


def test_benzene_formula_and_mass():
    d = describe_smiles("c1ccccc1")
    assert d.valid
    assert d.formula == "C6H6"
    assert abs(d.mw - 78.11) < 0.05
    assert d.rings == 1
    assert d.aromatic_atoms == 6


def test_aspirin_descriptors():
    d = describe_smiles("CC(=O)Oc1ccccc1C(=O)O")
    assert d.valid
    assert d.formula == "C9H8O4"
    assert abs(d.mw - 180.16) < 0.05
    assert d.hbd == 1
    assert d.hba == 4
    assert d.rings == 1
    assert d.rotatable_bonds == 3
    assert d.lipinski_pass


def test_caffeine_formula():
    d = describe_smiles("Cn1cnc2c1c(=O)n(C)c(=O)n2C")
    assert d.valid
    assert d.formula == "C8H10N4O2"
    assert abs(d.mw - 194.19) < 0.05


def test_invalid_smiles_is_explicit_not_guessed():
    d = describe_smiles("not-a-smiles")
    assert not d.valid
    assert d.mw == 0.0
    assert "could not be parsed" in d.note


def test_fused_ring_count():
    assert describe_smiles("c1ccc2ccccc2c1").rings == 2


def test_functional_alerts():
    assert describe_smiles("O=C1C=CC(=O)C=C1").flags["quinone"]
    assert describe_smiles("COc1cc(/C=C/C(=O)CC(=O)/C=C/c2ccc(O)c(OC)c2)ccc1O").flags["michael_acceptor"]
    assert not describe_smiles("c1ccccc1").flags["quinone"]


def test_charged_bracket_atom_parses():
    mol = parse_smiles("Cn1cnc2c1c(=O)[n+](C)c(=O)n2C")
    assert any(atom.charge == 1 for atom in mol.atoms)
